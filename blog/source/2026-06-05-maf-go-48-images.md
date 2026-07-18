# step10 · Images (multimodal input)

*This lesson teaches how to send a question and an image together in one message to a vision-capable Foundry agent.*

---

## What this lesson demonstrates

So far every message has been plain text. But `message.Message` holds a *list* of content parts, and different part types carry different media. This lesson puts a `TextContent` (the question) and a `DataContent` (an embedded JPEG) in the **same** message and hands it to a vision-capable `VisionAgent`. The image rides along as inline base64 bytes — no upload step, no URL — and the model reasons over both parts as a single turn.

## Building the multimodal message

The whole "multimodal" idea is just co-locating two content parts in one `message.New(...)` call:

```go
func imageMessage(prompt string, img []byte) *message.Message {
	return message.New(
		&message.TextContent{Text: prompt},
		&message.DataContent{
			Name:      "walkway.jpg",
			Data:      base64.StdEncoding.EncodeToString(img),
			MediaType: "image/jpeg",
		},
	)
}
```

## What to notice / the gotcha

- **`DataContent.Data` must be base64-encoded**, and `MediaType` (`"image/jpeg"`) tells the service how to decode it. `Name` is an optional filename hint. Forget the base64 encode and the service can't read the bytes. For a *remote* image you'd use `message.URIContent` instead of embedding.
- **`RunMessage` vs `RunText`.** `RunText(ctx, "…")` is sugar for a single text part; when you need more than text you assemble the `*message.Message` yourself and call `a.RunMessage(ctx, msg)`.
- **The image is embedded at compile time** with `//go:embed assets/walkway.jpg`, so there's no run-time file I/O and the demo is self-contained.

## How it maps to the Agent Framework

In the Go SDK, a turn is a `*message.Message` — a bag of `message.Content` parts — not a string. The Foundry provider serializes `DataContent` inline into the `POST /responses` request, so a vision-capable deployment (e.g. `gpt-4o`) sees the picture and the prompt together. The same content-part model is how you'd later attach audio or documents.

## Run it

```bash
go run ./tutorial/02-agents/providers/foundry/step10_images
```

The live run needs `az login`, `FOUNDRY_PROJECT_ENDPOINT`, and a vision-capable model deployment. The offline tests assert the message structure (one `TextContent` + one `DataContent`, `Data` round-tripping back to the original bytes) with no network; the live call is gated behind `AF_LIVE=1`.

---

Next: [step11 · An Agent as a Function Tool](/blog/posts/maf-go-49-as-function-tool.html)
