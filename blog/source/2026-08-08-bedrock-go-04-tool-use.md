# Tool Use with the Converse API

*How to give an Amazon Bedrock model real Go functions — declaring tools, catching the tool-use stop reason, executing your code, and returning results — using the full round-trip loop in aws-sdk-go-v2.*

---

A Bedrock model can reason about your problem, but on its own it cannot read a database, hit an internal API, or do arithmetic you can trust. **Tool use** — the industry's name for function calling — closes that gap. You describe the functions you have, the model decides *when* to call one and *with what arguments*, you run the real Go code, and you hand the answer back so the model can finish its reply.

The Converse API makes this uniform across every tool-capable model on Bedrock — Anthropic's Claude, Amazon Nova, Mistral, and others — behind one request shape. This post walks the whole loop in Go with `github.com/aws/aws-sdk-go-v2/service/bedrockruntime`: how a tool is declared, how the model signals it wants one, how you execute it, and how the result travels back. The theme to hold onto: **tool use is a conversation, not a single call.** You will loop.

---

## The shape of the loop

Before any code, fix the five steps in your head. Everything below is an implementation of this:

1. You send the conversation plus a **tool configuration** describing what the model may call.
2. The model replies with stop reason `ToolUse` and one or more **tool-use blocks** — each naming a tool and carrying JSON input it chose.
3. You **execute the real function** for each requested call.
4. You append the model's message, then send a **new user message** containing one **tool-result block** per call, each echoing the request's id.
5. You call Converse again. The model reads the results and either answers (`EndTurn`) or asks for more tools — in which case you go back to step 2.

Steps 2 through 5 repeat until the model stops asking for tools. That repetition is the part people forget, and it is why this is a `for` loop rather than two sequential calls.

---

## Declaring a tool

A tool is a name, a human-readable description, and a JSON Schema for its inputs. In aws-sdk-go-v2 that maps onto a small tower of union types. Working outward from the schema:

- The schema itself is a **document** — a dynamic JSON value from `github.com/aws/aws-sdk-go-v2/aws/protocol/document`. You build one from a Go map with `document.NewLazyDocument(...)`. (If you are unsure of the exact constructor for a given SDK version, check the `aws/protocol/document` package on pkg.go.dev — the lazy document is the workhorse here.)
- That document goes inside the `types.ToolInputSchema` union, specifically the `*types.ToolInputSchemaMemberJson` variant.
- The schema, name, and description live in a `types.ToolSpecification`.
- The spec is wrapped in the `types.Tool` union via `*types.ToolMemberToolSpec`.
- One or more `types.Tool` values fill `types.ToolConfiguration.Tools`.

Here is a single `get_weather` tool declared end to end:

```go
import (
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/aws/protocol/document"
	"github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types"
)

func weatherToolConfig() *types.ToolConfiguration {
	schema := document.NewLazyDocument(map[string]any{
		"type": "object",
		"properties": map[string]any{
			"city": map[string]any{
				"type":        "string",
				"description": "City name, e.g. 'Pune' or 'Berlin'.",
			},
			"unit": map[string]any{
				"type":        "string",
				"enum":        []string{"celsius", "fahrenheit"},
				"description": "Temperature unit to report.",
			},
		},
		"required": []string{"city"},
	})

	return &types.ToolConfiguration{
		Tools: []types.Tool{
			&types.ToolMemberToolSpec{
				Value: types.ToolSpecification{
					Name:        aws.String("get_weather"),
					Description: aws.String("Get the current weather for a city."),
					InputSchema: &types.ToolInputSchemaMemberJson{Value: schema},
				},
			},
		},
	}
}
```

The JSON Schema is the model's entire view of your function. Names, the `description` on each property, `enum` constraints, and the `required` list are what steer the model toward correct calls — treat them as prompt engineering, not boilerplate.

**The gotcha:** `InputSchema` is a *document union*, not a Go map you can hand over directly. You must wrap your map in `document.NewLazyDocument(...)` and then in `*types.ToolInputSchemaMemberJson`. Skipping either layer is a compile error at best and, if you improvise with `any`, a runtime marshalling failure that surfaces as an opaque validation error from Bedrock.

---

## The real Go function

The tool declaration is a promise; this is the code that keeps it. Nothing about it is special to Bedrock — it is an ordinary function. In production `get_weather` would call a weather API; here it returns a canned value so the example stays self-contained and deterministic.

```go
type WeatherArgs struct {
	City string `json:"city"`
	Unit string `json:"unit"`
}

func getWeather(args WeatherArgs) string {
	unit := args.Unit
	if unit == "" {
		unit = "celsius"
	}
	// A real implementation would call a weather service here.
	temp := "24"
	if unit == "fahrenheit" {
		temp = "75"
	}
	return fmt.Sprintf("The weather in %s is sunny, %s degrees %s.", args.City, temp, unit)
}
```

The model will call `get_weather` with arguments *it* chose. Those arrive as a document, so before you can call `getWeather` you have to decode that document into `WeatherArgs`.

---

## Decoding the model's arguments

When the model requests a tool, the input lands in `types.ToolUseBlock.Input`, typed as `document.Interface` — the same document abstraction as the schema, only now flowing the other direction. It is **not** a `map[string]any` you can index. Decode it deliberately into your struct with `UnmarshalSmithyDocument`:

```go
func decodeArgs(input document.Interface, out any) error {
	if err := input.UnmarshalSmithyDocument(out); err != nil {
		return fmt.Errorf("decode tool input: %w", err)
	}
	return nil
}
```

`UnmarshalSmithyDocument` honours the `json` struct tags, so the same `WeatherArgs` you would use for a plain JSON payload works here. If you prefer to route everything through `encoding/json`, marshal the document to bytes and `json.Unmarshal` into your struct — both are valid; pick one and be consistent.

**The gotcha:** the input is a document union, not a Go map. Reaching for a type assertion like `input.(map[string]any)` will not compile against the document interface. Decode it into a typed struct (or a `map[string]any` via unmarshalling) on purpose — and validate the fields, because the model can omit an optional argument or, occasionally, hallucinate one that is not in your schema.

---

## Reading the response

A Converse call returns a `*bedrockruntime.ConverseOutput`. Two fields drive the loop:

- `output.StopReason` — a `types.StopReason`. `types.StopReasonToolUse` means "run tools and come back"; `types.StopReasonEndTurn` means the model is done.
- `output.Output` — a `types.ConverseOutput` union whose `*types.ConverseOutputMemberMessage` variant holds the assistant's `types.Message`.

That message's `Content` is a slice of `types.ContentBlock`. Iterate it and type-switch each block. A turn that uses tools contains one `*types.ContentBlockMemberToolUse` per requested call (and often a `*types.ContentBlockMemberText` block where the model narrates what it is about to do):

```go
func assistantMessage(out *bedrockruntime.ConverseOutput) (types.Message, error) {
	msg, ok := out.Output.(*types.ConverseOutputMemberMessage)
	if !ok {
		return types.Message{}, fmt.Errorf("unexpected output type %T", out.Output)
	}
	return msg.Value, nil
}
```

Each tool-use block carries a `types.ToolUseBlock` with three fields you need: `ToolUseId` (a unique id for *this* call), `Name` (which tool), and `Input` (the document of arguments).

---

## Handling the calls and building results

For every `*types.ContentBlockMemberToolUse` in the assistant message, dispatch on `Name`, decode the input, run the function, and wrap the return value in a `*types.ContentBlockMemberToolResult`. The result block is a `types.ToolResultBlock`, and its `ToolUseId` **must** be the exact id from the request:

```go
func runToolCalls(assistant types.Message) ([]types.ContentBlock, error) {
	var results []types.ContentBlock

	for _, block := range assistant.Content {
		use, ok := block.(*types.ContentBlockMemberToolUse)
		if !ok {
			continue // text or other blocks — nothing to execute
		}
		tu := use.Value

		var (
			output string
			status = types.ToolResultStatusSuccess
		)

		switch aws.ToString(tu.Name) {
		case "get_weather":
			var args WeatherArgs
			if err := decodeArgs(tu.Input, &args); err != nil {
				output, status = err.Error(), types.ToolResultStatusError
			} else {
				output = getWeather(args)
			}
		default:
			output = fmt.Sprintf("unknown tool %q", aws.ToString(tu.Name))
			status = types.ToolResultStatusError
		}

		results = append(results, &types.ContentBlockMemberToolResult{
			Value: types.ToolResultBlock{
				ToolUseId: tu.ToolUseId, // echo the SAME id
				Status:    status,
				Content: []types.ToolResultContentBlock{
					&types.ToolResultContentBlockMemberText{Value: output},
				},
			},
		})
	}

	return results, nil
}
```

Note the nested unions again: a tool result's `Content` is a slice of `types.ToolResultContentBlock`, and text goes in via `*types.ToolResultContentBlockMemberText`. There is also a JSON variant (`*types.ToolResultContentBlockMemberJson`) if you would rather return structured data than a sentence — the model reads either.

**The gotcha:** every tool result **must** echo the exact `ToolUseId` from its request. Bedrock pairs results to calls by id, not by order; a mismatched or missing id makes the whole Converse call fail with a validation error. When a tool errors, do not drop the result — return it with `Status: types.ToolResultStatusError` and a message in the text block. The model can read the failure and recover (retry with different arguments, or apologise gracefully); a silently missing result just breaks the turn.

---

## The driving loop

Now assemble the pieces. Seed the conversation with a user turn, then loop: call Converse, and if the stop reason is `ToolUse`, append the assistant message, run the tools, append a **user** message carrying the results, and go around again. Stop when the model returns any other stop reason.

```go
func converseWithTools(ctx context.Context, client *bedrockruntime.Client, modelID, question string) (string, error) {
	toolCfg := weatherToolConfig()

	messages := []types.Message{
		{
			Role:    types.ConversationRoleUser,
			Content: []types.ContentBlock{&types.ContentBlockMemberText{Value: question}},
		},
	}

	const maxTurns = 8 // a hard ceiling so a misbehaving model can't loop forever
	for turn := 0; turn < maxTurns; turn++ {
		out, err := client.Converse(ctx, &bedrockruntime.ConverseInput{
			ModelId:    aws.String(modelID),
			Messages:   messages,
			ToolConfig: toolCfg,
		})
		if err != nil {
			return "", fmt.Errorf("converse: %w", err)
		}

		assistant, err := assistantMessage(out)
		if err != nil {
			return "", err
		}

		if out.StopReason != types.StopReasonToolUse {
			return firstText(assistant), nil // EndTurn, MaxTokens, etc.
		}

		// Record the model's tool request, then answer it.
		messages = append(messages, assistant)

		results, err := runToolCalls(assistant)
		if err != nil {
			return "", err
		}
		messages = append(messages, types.Message{
			Role:    types.ConversationRoleUser, // results go back as USER role
			Content: results,
		})
	}

	return "", fmt.Errorf("tool loop exceeded %d turns", maxTurns)
}

func firstText(msg types.Message) string {
	for _, block := range msg.Content {
		if t, ok := block.(*types.ContentBlockMemberText); ok {
			return t.Value
		}
	}
	return ""
}
```

Ask *"What's the weather in Pune in fahrenheit?"* and the trace is: Converse returns `ToolUse` with a `get_weather` call for `{"city":"Pune","unit":"fahrenheit"}`; you run `getWeather`, append the assistant turn and a user turn holding the result; the second Converse call returns `EndTurn` with prose like *"It's sunny in Pune, about 75 degrees fahrenheit."*

**The gotcha:** one Converse call is almost never enough — you must loop. The first call only *requests* tools; the answer comes on a later iteration. Two subtleties bite here. First, tool results are sent back as a message with **`ConversationRoleUser`**, not assistant — the assistant role is reserved for what the model produced, and you appended that verbatim one step earlier. Second, always keep a turn ceiling (`maxTurns` above): a model that keeps requesting tools, or a buggy tool that always errors, would otherwise loop indefinitely and burn tokens.

---

## Parallel tool calls

The loop above already handles the important subtlety: a single assistant turn can contain **several** tool-use blocks. If you ask *"Compare the weather in Pune and Berlin,"* the model may emit two `get_weather` calls in one turn rather than taking two round-trips. That is why `runToolCalls` ranges over *all* content blocks and returns a slice of results.

The rules for the parallel case:

- Execute each requested call — sequentially, or concurrently with a `sync.WaitGroup` / `errgroup` if the functions are slow and independent.
- Return **one** tool-result block per tool-use block, each carrying its own matching `ToolUseId`.
- Put all of those result blocks in a **single** user message. You do not send one message per result; you send one message whose `Content` holds every result.

| Scenario | Assistant turn | Your reply |
|---|---|---|
| One tool | 1 tool-use block | 1 user message, 1 result block |
| Parallel tools | N tool-use blocks in one turn | 1 user message, N result blocks (ids matched) |
| Sequential tools | 1 tool-use block, then `ToolUse` again next turn | 1 result, loop, repeat |

If you execute the calls concurrently, guard shared state and preserve the id-to-result pairing — order within the message does not matter to Bedrock, but every id must be present and correct.

**The gotcha:** in the parallel case it is easy to build results whose ids drift — for example, if you collect outputs in a map keyed by tool name instead of by `ToolUseId`, two calls to the same tool collide. Key everything by `ToolUseId`, the value Bedrock assigned, so each result lands against the exact call that produced it.

---

## Nudging the model toward (or away from) tools

`types.ToolConfiguration` has an optional `ToolChoice` union that governs *whether* the model may or must call a tool on the next turn:

- `*types.ToolChoiceMemberAuto` — the model decides (the default behaviour).
- `*types.ToolChoiceMemberAny` — the model must call *some* tool.
- `*types.ToolChoiceMemberTool` — the model must call one specific named tool.

Support for `Any` and a forced tool varies by model family, so consult the model's documentation before relying on them; `Auto` is universal. Forcing a tool is useful when your application always needs structured output on the first turn — for example, always extracting fields into a known schema.

---

## Key takeaways

- **Tool use is a loop, not a call.** Send the tool config, catch `StopReason == ToolUse`, run the function, return the result, and Converse again — repeating until the model stops asking. Always cap the iterations.
- **Declarations are nested unions.** A tool is `*types.ToolMemberToolSpec` → `types.ToolSpecification` → `*types.ToolInputSchemaMemberJson` → a `document.NewLazyDocument(...)` JSON Schema. The schema is the model's whole view of your function.
- **Inputs arrive as a document, not a map.** Decode `ToolUseBlock.Input` with `UnmarshalSmithyDocument` (or a JSON round-trip) into a typed struct, and validate.
- **Every result must echo its `ToolUseId`,** carry a `Status`, and travel back in a **user-role** message. Bedrock pairs results to calls by id, so mismatches fail the turn.
- **Handle parallel calls.** One turn can hold several tool-use blocks; return one id-matched result each, all in a single user message.

Give a model good tools with clear schemas and a correct loop, and it stops guessing at facts it cannot know and starts orchestrating the real capabilities you already built.

---

## Further reading

- [Use a tool to complete an Amazon Bedrock model response](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-inference-call.html) — the official Converse tool-use (function calling) guide.
- [Call a tool with the Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-examples.html) — request/response walkthroughs and the tool-result contract.
- [`bedrockruntime` package](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime) and its [`types`](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types) — `ConverseInput`, `ToolConfiguration`, `Tool`, `ToolUseBlock`, `ToolResultBlock`, and the content-block unions.
- [aws-sdk-go-v2 `bedrockruntime/types`](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockruntime/types) — the ToolConfiguration / ContentBlock union types; the document helpers for tool input schemas live in the SDK's Smithy `document` package (confirm the exact import path on pkg.go.dev for your SDK version).
