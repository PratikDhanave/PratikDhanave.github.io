# step11 · Using Images (multi-modality)

*How one message can bundle a text prompt and an image, and why that forces RunMessage instead of the RunText shortcut.*

---

## What this lesson demonstrates

Every prompt so far has been a plain string via `RunText`. Real agents also take images, audio, and files. This lesson sends a vision-capable model a photo of a walkway together with the question *"What do you see?"* — assembled as a single multi-part `message.Message` and run with `RunMessage`.

The image `assets/walkway.jpg` is baked into the binary with `//go:embed`, so nothing is read from disk at runtime and the program is fully self-contained.

## The core: a message is a list of Content parts

```go
func imageMessage(prompt, imageName, mediaType string, imageBytes []byte) *message.Message {
    return message.New(
        &message.TextContent{Text: prompt},
        &message.DataContent{
            Name:      imageName,
            Data:      base64.StdEncoding.EncodeToString(imageBytes),
            MediaType: mediaType,
        },
    )
}
```

`message.New(...)` takes any number of Content parts and returns one user `Message`. A `*TextContent` carries the question; a `*DataContent` carries the image — its raw JPEG bytes base64-encoded into `Data`, with `MediaType` (`"image/jpeg"`) telling the model how to decode them.

## What to notice

- **`RunMessage`, not `RunText`.** `RunText` only accepts a plain string, so it cannot carry the image. `a.RunMessage(ctx, msg)` takes a fully built `*message.Message`, which is how you pass any multi-part input.
- **`DataContent` vs `URIContent`.** `DataContent` embeds the bytes in the request. For an image already hosted at a URL you would use `message.URIContent` instead — no bytes, just a link the model fetches itself.
- **The logger prints text only.** The middleware calls `msg.String()`, which returns just the text parts, so the base64 image bytes never get dumped to your console.
- **`go:embed` bakes the asset in.** `//go:embed assets/walkway.jpg` compiles the image into the binary as `[]byte`, so the offline test can verify the real image loaded (it starts with the JPEG magic bytes `0xFF 0xD8`).

## How it maps to the SDK

The multi-modal `message.Message` is provider-agnostic: `foundryprovider` translates the `DataContent` into an image data URI on the Foundry Responses API request. The gotcha at the Azure AI Foundry level is that this only works against a **vision-capable deployment** (e.g. `gpt-4o`) — the SDK will happily assemble the message, but a text-only model will ignore the image.

## Run it

```bash
go run ./tutorial/02-agents/agents/step11_using_images
```

The offline tests (wiring, message assembly, embedded asset) run anywhere; the live vision call needs `az login` + a vision model and is gated behind `AF_LIVE=1`.

---

Next: [12 · Agent as a Function Tool](/blog/posts/maf-go-22-as-function-tool.html)
