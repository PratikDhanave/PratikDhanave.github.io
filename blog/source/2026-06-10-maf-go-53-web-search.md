# step21 · Foundry Web Search (hosted tool + citations)

*This lesson teaches how to attach the hosted web-search tool and read the citation annotations the service returns with its answer.*

---

## What this lesson demonstrates

A function tool is code *you* run when the model asks. A **hosted tool** is different: it's a marker you attach to the agent that tells the Foundry service "you're allowed to do this yourself." `&hostedtool.WebSearch{}` carries no logic — the *service* performs the search, grounds its answer on the results, and returns the answer alongside `CitationAnnotation`s pointing at the sources it used. This lesson attaches the tool and adds a pure function to pull those citations out of the response.

## Reading citations off the response

The citation reader is a pure function of the response — no network, no globals — which is exactly what makes it directly unit-testable:

```go
func collectCitations(resp *agent.Response) []citation {
	var out []citation
	if resp == nil {
		return out
	}
	for content := range resp.Contents() {
		for _, annotation := range content.Header().Annotations {
			c, ok := annotation.(*message.CitationAnnotation)
			if !ok || c.URL == "" {
				continue
			}
			out = append(out, citation{Title: c.Title, URL: c.URL, Snippet: c.Snippet})
		}
	}
	return out
}
```

## What to notice / the gotcha

- **A hosted tool is a zero-value marker.** `&hostedtool.WebSearch{}` implements `tool.Tool` but has an empty `Description()` and no `Run`. Attaching it just *declares the capability*; the search happens server-side, not in your process.
- **Citations ride along on content, not on the top-level response.** Each `message.Content` has a `Header()` whose `Annotations` may hold `*message.CitationAnnotation` values. `resp.Contents()` is a Go 1.23+ iterator over every content, so extracting citations is one nested loop — and you must type-assert each annotation and skip the ones with an empty `URL`.
- **Not every deployment supports it.** The live run needs a model deployment that supports hosted web search; without it the tool declaration has nothing to act on.

## How it maps to the Agent Framework

`hostedtool.WebSearch` mirrors `hostedtool.CodeInterpreter` (step14): both are server-side capabilities the agent merely declares. What's new here is the *return* path — the Go SDK surfaces grounding sources as `CitationAnnotation`s on content headers, giving you attributable, auditable answers rather than an opaque blob of text.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step21_web_search
```

The live run needs `az login`, `FOUNDRY_PROJECT_ENDPOINT`, and a web-search-capable deployment. Offline tests feed a hand-built response (one annotation with a URL, one without) to `collectCitations` and assert it keeps the URL'd one; the live call is gated behind `AF_LIVE=1`.

---

Next: [step23 · Local MCP (wrapping remote tools)](/blog/posts/maf-go-54-local-mcp.html)
