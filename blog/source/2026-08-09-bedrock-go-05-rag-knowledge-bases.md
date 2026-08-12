# Retrieval-Augmented Generation with Knowledge Bases

*How to query a Knowledge Base for Amazon Bedrock from Go — the managed retrieve-then-read layer — using both the low-level Retrieve call and the one-shot RetrieveAndGenerate, with citations wired through.*

---

A model trained months ago cannot answer questions about your internal wiki, last quarter's contracts, or a product manual it never saw. Retrieval-Augmented Generation (RAG) fixes that without retraining: fetch the passages that matter, put them in front of the model, and let it answer from them. The hard part of RAG is the retrieval plumbing — chunking documents, embedding them, running a vector store, keeping it in sync. **Knowledge Bases for Amazon Bedrock** is AWS's managed version of that plumbing. You point it at data in S3, it chunks and embeds the content into a vector store (OpenSearch Serverless, Aurora PostgreSQL with pgvector, and others), and it exposes a retrieval endpoint you call at query time.

This post is about the *query time* from Go. Two runtime calls live in `github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime`:

- **`Retrieve`** — hand it a query, get back ranked chunks. You decide what to do with them (usually stuff them into a Converse prompt yourself). This is the *retrieve-then-read* pattern with you holding the pen.
- **`RetrieveAndGenerate`** — hand it a query, get back a finished answer plus citations. Retrieval, prompt assembly, and generation happen server-side in one call.

Both talk to a knowledge base you have already created. Creating one is a *control-plane* job and out of scope here — I will cover the setup boundary briefly, then spend the rest of the post on the two runtime calls, with complete Go examples and the traps that bite people.

---

## Where the knowledge base comes from (the setup boundary)

You do not create a knowledge base from the runtime client. Creation lives in a separate control-plane package, `github.com/aws/aws-sdk-go-v2/service/bedrockagent` (note: no `runtime` suffix), or more commonly in the console, CloudFormation, Terraform, or the CDK. The setup wires three things together: a data source (typically an S3 bucket), an embedding model, and a vector store to hold the embeddings. Once configured, you trigger an *ingestion job* that reads the source, chunks each document, embeds the chunks, and writes vectors into the store.

I am deliberately not showing the create API in detail — it has many knobs (chunking strategy, embedding model ARN, vector index mapping) and inventing field names would be worse than useless. Treat it as infrastructure: provision it once with IaC, note the resulting **knowledge base ID** (a short string like `ABCD1234XY`), and move on to querying. Everything below assumes you have that ID and that at least one ingestion job has finished.

**The gotcha:** a knowledge base returns nothing useful until ingestion has completed at least once. If you provision the KB and immediately query it, `Retrieve` happily returns an empty result set — no error, just no chunks — because the vector store is still empty or mid-sync. Same after you add new documents to S3: they are invisible to queries until the next ingestion job finishes indexing them. Check the data source sync status in the console (or via the control-plane API) before you conclude your retrieval code is broken.

---

## Building the runtime client

Both calls use the same client, constructed from a standard AWS config. Nothing Bedrock-specific here beyond the package name.

```go
package main

import (
	"context"
	"log"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime"
)

func newClient(ctx context.Context) (*bedrockagentruntime.Client, error) {
	cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion("us-east-1"))
	if err != nil {
		return nil, err
	}
	return bedrockagentruntime.NewFromConfig(cfg), nil
}
```

The region matters: a knowledge base is regional, so the client's region must match where the KB lives, or you will get a "resource not found" error for an ID that plainly exists elsewhere. Credentials resolve through the usual chain (environment, shared config, IAM role). The IAM principal needs `bedrock:Retrieve` and `bedrock:RetrieveAndGenerate` permissions, and — for `RetrieveAndGenerate` — permission to invoke the generation model as well.

---

## Pattern A: Retrieve, then read

`Retrieve` is the honest primitive. You give it a knowledge base ID and a query string; it returns ranked chunks and gets out of your way. The input carries the query inside a `types.KnowledgeBaseQuery`:

```go
import (
	"github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime"
	"github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime/types"
)

func retrieveChunks(ctx context.Context, c *bedrockagentruntime.Client, kbID, question string) ([]types.KnowledgeBaseRetrievalResult, error) {
	out, err := c.Retrieve(ctx, &bedrockagentruntime.RetrieveInput{
		KnowledgeBaseId: aws.String(kbID),
		RetrievalQuery: &types.KnowledgeBaseQuery{
			Text: aws.String(question),
		},
	})
	if err != nil {
		return nil, err
	}
	return out.RetrievalResults, nil
}
```

`out.RetrievalResults` is a `[]types.KnowledgeBaseRetrievalResult`. Each result carries three things worth reading: `Content` (a `*types.RetrievalResultContent` whose `Text` field holds the chunk text), `Location` (where the chunk came from — for an S3 source, an S3 URI), and `Score` (a `*float64` relevance score the vector store assigned). Because these are all pointers, guard against `nil` before dereferencing:

```go
func summarize(results []types.KnowledgeBaseRetrievalResult) {
	for i, r := range results {
		text := ""
		if r.Content != nil && r.Content.Text != nil {
			text = aws.ToString(r.Content.Text)
		}
		score := 0.0
		if r.Score != nil {
			score = *r.Score
		}
		log.Printf("chunk %d (score %.3f): %.80s...", i, score, text)
	}
}
```

The `Location` field is a `*types.RetrievalResultLocation` — a tagged union whose shape depends on the source type. For S3-backed data it exposes an `S3Location` with a URI; other source types populate their own sub-struct. Rather than hard-coding one variant, switch on `Location.Type` and read the matching field. When in doubt about the exact sub-field names, open the `bedrockagentruntime/types` package on pkg.go.dev and read the `RetrievalResultLocation` definition — union shapes evolve as AWS adds source types, and guessing is how you ship a nil dereference.

### Feeding chunks to Converse

`Retrieve` gives you passages, not an answer. To produce an answer you assemble a prompt yourself and send it to a chat model — for Bedrock that is the `Converse` call in `github.com/aws/aws-sdk-go-v2/service/bedrockruntime` (covered earlier in this series). The join looks like this:

```go
func buildPrompt(question string, results []types.KnowledgeBaseRetrievalResult) string {
	var sb strings.Builder
	sb.WriteString("Answer the question using only the context below. ")
	sb.WriteString("If the context does not contain the answer, say so.\n\n")
	sb.WriteString("Context:\n")
	for i, r := range results {
		if r.Content == nil || r.Content.Text == nil {
			continue
		}
		fmt.Fprintf(&sb, "[%d] %s\n\n", i+1, aws.ToString(r.Content.Text))
	}
	fmt.Fprintf(&sb, "Question: %s", question)
	return sb.String()
}
```

You then pass that string to `Converse` as the user message. The numbered `[1]`, `[2]` markers let you ask the model to cite by index, giving you a poor man's citation system that maps back to the `Location` of each result. This is more work than the one-shot call, but the payoff is total control — see the comparison below.

**The gotcha:** by default `Retrieve` returns a modest number of chunks, and the count is tunable through the optional `RetrievalConfiguration` field on `RetrieveInput` (which nests a vector-search configuration with a `NumberOfResults` knob). Retrieve too few and the answer is missing context; retrieve too many and you blow the model's context window and pay for tokens that add noise. There is no universal right number — tune it against real queries. The results also arrive already ranked by score, so if you truncate, truncate from the bottom.

---

## Pattern B: RetrieveAndGenerate, the one-shot path

When you do not need to touch the prompt, `RetrieveAndGenerate` collapses the whole pipeline into a single call. It retrieves, builds a grounded prompt with a managed template, calls a generation model, and hands back the finished text plus citations that map answer spans to source chunks.

The input nests the query in a `types.RetrieveAndGenerateInput` (note: this is a *types* struct, distinct from the operation's own `RetrieveAndGenerateInput` — the SDK reuses the name across packages, which is confusing until you see it). The configuration selects the knowledge-base flavor and names both the KB and the model:

```go
func retrieveAndGenerate(ctx context.Context, c *bedrockagentruntime.Client, kbID, modelArn, question string) (*bedrockagentruntime.RetrieveAndGenerateOutput, error) {
	return c.RetrieveAndGenerate(ctx, &bedrockagentruntime.RetrieveAndGenerateInput{
		Input: &types.RetrieveAndGenerateInput{
			Text: aws.String(question),
		},
		RetrieveAndGenerateConfiguration: &types.RetrieveAndGenerateConfiguration{
			Type: types.RetrieveAndGenerateTypeKnowledgeBase,
			KnowledgeBaseConfiguration: &types.KnowledgeBaseRetrieveAndGenerateConfiguration{
				KnowledgeBaseId: aws.String(kbID),
				ModelArn:        aws.String(modelArn),
			},
		},
	})
}
```

Three fields carry the weight. `Type` is a required enum — `types.RetrieveAndGenerateTypeKnowledgeBase` says "use a knowledge base" (the other value, `RetrieveAndGenerateTypeExternalSources`, feeds documents inline instead). `KnowledgeBaseId` is the same short ID from setup. `ModelArn` names the generation model.

**The gotcha:** `ModelArn` wants a *full ARN*, not a bare model ID. A value like `anthropic.claude-3-sonnet-20240229-v1:0` — perfectly valid for `Converse` — is rejected here. You need the full `arn:aws:bedrock:<region>::foundation-model/<model-id>` form (or an inference-profile ARN). The failure surfaces as a validation error, not a helpful hint, so the first time you wire this up, double-check you handed it an ARN and not an ID.

### Reading the answer and its citations

The response has two parts you care about. `out.Output` is a `*types.RetrieveAndGenerateOutput` whose `Text` field holds the generated answer. `out.Citations` is a `[]types.Citation` — this is the whole reason to prefer this call over a raw chat request, and skipping it throws away RAG's main benefit.

Each `Citation` links a *span of the answer* to the *sources that grounded it*. The `GeneratedResponsePart` field tells you which piece of the answer the citation covers; `RetrievedReferences` is a `[]types.RetrievedReference`, each carrying the same `Content` / `Location` / `Score` fields you saw from `Retrieve`. Walking them looks like this:

```go
func printGrounded(out *bedrockagentruntime.RetrieveAndGenerateOutput) {
	answer := ""
	if out.Output != nil && out.Output.Text != nil {
		answer = aws.ToString(out.Output.Text)
	}
	fmt.Println("Answer:", answer)

	for i, cite := range out.Citations {
		fmt.Printf("\nCitation %d covers:\n", i+1)
		if cite.GeneratedResponsePart != nil &&
			cite.GeneratedResponsePart.TextResponsePart != nil &&
			cite.GeneratedResponsePart.TextResponsePart.Text != nil {
			fmt.Printf("  %q\n", aws.ToString(cite.GeneratedResponsePart.TextResponsePart.Text))
		}
		for _, ref := range cite.RetrievedReferences {
			if ref.Content != nil && ref.Content.Text != nil {
				fmt.Printf("  source: %.80s...\n", aws.ToString(ref.Content.Text))
			}
		}
	}
}
```

**The gotcha:** citations are optional to *use* but essential to *trust*. If your UI shows only `out.Output.Text` and ignores `out.Citations`, you have built a chatbot that sounds authoritative with no way for a reader to verify it — which is precisely the failure mode RAG exists to prevent. Surface the citations: render the source URI from each reference's `Location`, or at minimum footnote the covered spans. The trust benefit of RAG lives entirely in that mapping.

### Multi-turn sessions

`RetrieveAndGenerate` can carry conversational state. The response includes a `SessionId`; pass it back on the next call (via the input's session field) and Bedrock keeps context across turns so follow-up questions like "and what about the second one?" resolve against the earlier answer. For a stateless single question, ignore it. The exact session field names are stable but easy to fat-finger — confirm them on pkg.go.dev before relying on them.

---

## Choosing between the two

They are not competitors so much as different altitudes. The rule of thumb:

| Question | Retrieve + your own Converse | RetrieveAndGenerate |
|---|---|---|
| Who writes the prompt? | You | Bedrock (managed template) |
| Effort to first answer | Higher (assemble + call Converse) | Lowest (one call) |
| Citations | You build them from `Location` | Returned in `out.Citations` |
| Rerank / filter chunks | Yes, before prompting | No, it is a black box |
| Mix KB chunks with other sources | Yes, you control the context | No (one KB per call) |
| Custom system prompt / persona | Full control | Limited to config knobs |

Reach for **`RetrieveAndGenerate`** when you want a grounded answer fast and the default prompt template is good enough — internal Q&A, doc search, a support assistant. Reach for **`Retrieve` + `Converse`** when you need to rerank results with your own model, blend knowledge-base chunks with data from another system, enforce a specific persona or output format, or apply business rules to which chunks are even allowed into the prompt. Many production systems start with `RetrieveAndGenerate` to ship, then graduate to `Retrieve` once they need control the managed path does not give.

---

## Key takeaways

- **The knowledge base is infrastructure; this post is the runtime.** Create it via the control plane (`bedrockagent`, console, or IaC), note the KB ID, and query it with `bedrockagentruntime`.
- **`Retrieve` returns ranked chunks, not answers.** Read `RetrievalResults[i].Content.Text`, `.Location`, and `.Score` (all pointers — nil-check them), then assemble your own prompt for `Converse`.
- **`RetrieveAndGenerate` is the one-call path.** Set `Type: types.RetrieveAndGenerateTypeKnowledgeBase`, give it a `KnowledgeBaseId` and a full-ARN `ModelArn`, and read `out.Output.Text` plus `out.Citations`.
- **`ModelArn` is an ARN, not a model ID** — the single most common first-run failure.
- **Ingestion must finish before queries return anything** — an empty result set is often a sync-timing bug, not a code bug.
- **Surface citations or lose the point.** The span-to-source mapping in `out.Citations` is the trust layer; hiding it turns grounded RAG back into an unverifiable chatbot.
- **When unsure of an exact field name** — especially the union `RetrievalResultLocation` and the session fields — read the `bedrockagentruntime` and its `types` package on pkg.go.dev rather than guessing.

---

## Further reading

- [Knowledge Bases for Amazon Bedrock — official documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Retrieve data and generate responses (Retrieve / RetrieveAndGenerate)](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html)
- [`bedrockagentruntime` package — pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime)
- [`bedrockagentruntime/types` package — pkg.go.dev](https://pkg.go.dev/github.com/aws/aws-sdk-go-v2/service/bedrockagentruntime/types)
