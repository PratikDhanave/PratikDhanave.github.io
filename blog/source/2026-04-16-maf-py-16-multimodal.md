# Multimodal

*Building a Message of mixed content parts so an agent can reason about an image.*

---

## What it demonstrates

Every prompt so far has been a plain string. But a user turn is really a `Message` made of one or more `Content` parts. To ask an agent about an image you build a `Message` whose `contents=[...]` mixes a text part and an image part, then pass that `Message` to `agent.run(...)`. There are two ways to attach an image:

- `Content.from_uri(uri=..., media_type=...)` — point at a public URL
- `Content.from_data(data=<bytes>, media_type=...)` — embed local bytes

## The code

```python
url_message = Message(
    role="user",
    contents=[
        Content.from_text(text="What do you see in this image?"),
        Content.from_uri(uri=IMAGE_URL, media_type="image/jpeg"),
    ],
)
result = await agent.run(url_message)
```

The same shape works for local files: read the bytes with `"rb"` and pass `Content.from_data(data=image_bytes, media_type="image/jpeg")`. The vision-capable model reads all parts of the turn together.

## The gotcha

A multimodal turn is a `Message`, not a `str` — and text is *also* a content part, built with `Content.from_text(text=...)`, not passed as a bare string. `media_type` is a MIME type; `from_data` requires it and takes raw `data=<bytes>` (not a path), while `from_uri` strongly recommends it. And the deployed model must be vision-capable (e.g. gpt-4o) or the image part is ignored or rejected.

## Azure / MAF mapping

The vision agent runs on `FoundryChatClient` (Azure AI Foundry) with `AzureCliCredential`. Using the client-agnostic `Message`/`Content` API means the same multimodal turn works across providers — only the deployed `FOUNDRY_MODEL` needs vision support.

## Run it

`uv run tutorial/02-agents/08_multimodal.py` — needs Foundry creds and a vision-capable model. It worked if you get a description of the image at the URL (and optionally a local one).

---

Next: [Structured Outputs](/blog/posts/maf-py-17-structured-outputs.html)
