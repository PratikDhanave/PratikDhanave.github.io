# LLM Agents in Google ADK: The Four Knobs You Actually Tune

*description, instruction, generation params, and structured output — the dials on almost every agent you'll build*

---

The smallest agent in Google's [Agent Development Kit](https://google.github.io/adk-docs/) is a name, a model, and one line of instruction. That gets you talking. But the moment you have more than one agent, or you need the output to be *machine-readable* instead of chatty prose, you start reaching for four fields that appear on nearly every `LlmAgent` you write: `description`, `instruction`, the generation parameters, and an output schema. This post walks each one, side by side in Python and Go, and lands on the sharpest contrast between the two SDKs: how they force typed JSON out of a model.

## Knob 1 — `description`: how a parent decides to delegate

`description` is not the system prompt. It's a one-liner written for *other agents* to read. When you build a multi-agent tree (a later concept), a parent looks at each child's `description` to decide whether to route a request there. So write it as a routing hint, not as behavior:

```python
description="Provides structured facts (capital, currency, population, languages) about a country."
```

If a top-level agent is the only one a human talks to, the `description` does nothing — but the habit of writing a crisp, capability-focused line pays off the instant you add a coordinator above it.

## Knob 2 — `instruction`: the system prompt, with `{state}` templating

The `instruction` is the actual behavioral prompt. The feature worth internalizing early is that ADK treats it as a **template**: any `{placeholder}` is substituted from session state at run time.

```python
instruction="You are helping {user_name}. Their preferred units are {units?}."
```

`{user_name}` is pulled from session state; `{units?}` — note the `?` — is *optional*, so the substitution silently no-ops if the key is absent. This is how you personalize a static prompt without doing string concatenation in your own code. Both SDKs share the `{key}` / `{key?}` convention. Go adds one extra escape hatch: an `InstructionProvider` — a function that builds the prompt in code when `{}` templating isn't expressive enough. Python's equivalent is passing a callable as the instruction.

## Knob 3 — generation params: temperature, tokens, top-p

Generation config controls the sampling behavior of the underlying model. For extraction and structured tasks you almost always want temperature **low** (0–0.2) so the output is consistent run to run.

```python
from google.genai import types

generate_content_config=types.GenerateContentConfig(
    temperature=0.1,
    max_output_tokens=512,
    top_p=0.9,
)
```

Go carries the same fields, with one idiom difference that trips people up: **temperature is a pointer** (`*float32`), not a plain value. The API needs to distinguish "unset" from "explicitly zero", and Go has no `None`, so ADK uses a pointer and gives you the `genai.Ptr` helper:

```go
GenerateContentConfig: &genai.GenerateContentConfig{
    Temperature:     genai.Ptr(float32(0.1)),
    MaxOutputTokens: 512,
    TopP:            genai.Ptr(float32(0.9)),
},
```

Python takes the bare `temperature=0.1` because `None` already carries the "unset" meaning. `max_output_tokens` is a plain `int` in both.

## Knob 4 — structured output: force typed JSON

This is the reason most people reach past the smallest agent. Instead of parsing prose with regex, you declare the exact shape you want and the model is constrained to emit conforming JSON. This is where the two SDKs diverge the most.

**Python** — declare a Pydantic model and hand it over. ADK converts it to a schema for you, and you get a validating class for free:

```python
from pydantic import BaseModel, Field

class CountryInfo(BaseModel):
    capital: str = Field(description="The capital city.")
    currency: str = Field(description="The official currency name.")
    population_millions: float = Field(description="Approximate population in millions.")
    languages: list[str] = Field(description="Official language(s).")

root_agent = LlmAgent(
    name="country_info_agent",
    model="gemini-flash-latest",
    description="Provides structured facts about a country.",
    instruction="You are a geography expert. Return the capital, currency, "
                "approximate population in millions, and official language(s).",
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=CountryInfo,
    output_key="country_info",   # writes the result into session.state["country_info"]
)
```

**Go** — there's no Pydantic, so you build the `genai.Schema` explicitly. More verbose, but dependency-free and the shape is right there in front of you:

```go
func countrySchema() *genai.Schema {
    return &genai.Schema{
        Type: genai.TypeObject,
        Properties: map[string]*genai.Schema{
            "capital":            {Type: genai.TypeString},
            "currency":           {Type: genai.TypeString},
            "populationMillions": {Type: genai.TypeNumber},
            "languages":          {Type: genai.TypeArray, Items: &genai.Schema{Type: genai.TypeString}},
        },
        Required: []string{"capital", "currency", "populationMillions", "languages"},
    }
}

// llmagent.New(llmagent.Config{ ... OutputSchema: countrySchema(), OutputKey: "country_info" })
```

Watch the naming: Python's `population_millions` (snake_case) vs. the JSON `populationMillions` (camelCase). Pick a convention and make your instruction tell the model the same one.

The `output_key` in both examples is the quiet workhorse: it stashes the final structured result into `session.state["country_info"]`, which is how one agent hands data to the next in a pipeline.

### Mental model: the schema is a contract on the *final* output

Setting an output schema guarantees the response parses into your type. But the two SDKs disagree on what an output-schema agent may *also* do — and this is not a universal rule, so don't assume:

- **Python `google-adk` (2.x):** an output-schema agent **may still call tools and transfer**. Tools run during the reasoning loop; the schema is enforced only on the *final* output.
- **Go `adk/v2`:** stricter — an agent with an `OutputSchema` is **reply-only**. No tools, no agent transfer.

When you need both structure *and* tools on Go, the pattern is to split the work: one agent does the tool-calling, a second formats its result against the schema — the subject of the next concept.

## Two bonus knobs worth knowing

Two more fields shape *how the agent is fed*, and they pair naturally with the four above:

- **`input_schema`** — the symmetric counterpart to the output schema. It declares the structured *input* the agent expects, and it matters mainly when a parent invokes this agent as a tool: the parent must pass arguments matching it. On a top-level chat agent it's effectively a no-op. Python passes a Pydantic model; Go spells out a `genai.Schema`.
- **`include_contents`** — set it to `'none'` (Go: `llmagent.IncludeContentsNone`) to make a **stateless worker** that sees only its current turn, not the prior conversation. Reach for it when you want lower cost, more determinism, and privacy from the upstream conversation — ideal for a sub-agent invoked as a tool or run inside a loop.

## The takeaway

Four knobs cover most of what you'll tune: `description` for delegation, `instruction` for behavior (templated from state), generation params for sampling, and an output schema for typed results. The one place to slow down is structured output — Python's Pydantic-to-schema convenience and Go's explicit `genai.Schema` produce the same guarantee, but Go additionally forbids tools on a schema'd agent. Know that difference and you'll design your agent boundaries correctly from the start.

*Next in the series: composing these agents into Sequential, Parallel, and Loop workflows.*
