# Gemma on Flutter

*This is where the concepts become code. With a quantized Gemma model and the flutter_gemma plugin, running a real LLM entirely on the user's phone is a handful of Dart calls — load the model, open a chat session, stream tokens into your UI. The plugin hides the runtime; you write an app.*

The previous posts assembled the pieces: a case for on-device AI, the edge constraints, a quantized model, and the runtime that executes it. Now we wire them together in Flutter with the **`flutter_gemma`** plugin, which wraps the on-device runtime (MediaPipe on mobile/web, LiteRT on desktop) behind a Dart API. This post walks the shape of a real integration — model loading, sessions, streaming, and the patterns that keep it within the constraints. (The plugin's exact API surface evolves across versions, so treat the code as the *shape* of the integration and check the current package docs for precise signatures.)

## The integration at a glance

Running Gemma in a Flutter app has four conceptual steps, each mapping to something from earlier posts:

```text
1. Get the model onto the device   (a quantized .task file — the shipping problem, post 8)
2. Initialize the model            (load into memory via the runtime — the memory constraint)
3. Create a chat / session         (holds conversation state + KV cache)
4. Send a prompt, stream tokens    (the generation loop, streamed to the UI)
```

The plugin turns each into a few Dart calls. The art is less in the API and more in respecting the constraints around it — model size, memory, streaming UX — which the earlier posts prepared you for.

## Adding the plugin and choosing an engine

You add `flutter_gemma` to your `pubspec.yaml`, and — because the runtime is platform-specific — the engine for your target platform. For a mobile app that's the MediaPipe engine package; the plugin architecture lets you provide the engine appropriate to where the app runs (MediaPipe for mobile/web with `.task`/`.bin` models, LiteRT-LM for desktop with `.litertlm` models, as covered in the runtime post). The key setup decisions:

- **Pick your model and format** — a quantized Gemma `.task` model for mobile (from the quantization post), sized to your lowest-end device's memory budget.
- **Pick your engine** — the MediaPipe engine for mobile/web; add the LiteRT path only if you ship desktop.
- **Configure platform bits** — on-device ML needs platform configuration (minimum OS versions, sometimes native settings); the package docs list the specifics per platform.

## Loading the model

Getting the model into memory is the first real interaction, and it reflects the memory constraint directly — loading is a spike, and the file is large. Conceptually:

```dart
// Illustrative shape — check flutter_gemma docs for the current API.
final gemma = FlutterGemmaPlugin.instance;

// Point the plugin at the model file already on the device (bundled or downloaded).
await gemma.modelManager.setModelPath(localModelPath);

// Initialize the model with your inference settings.
final model = await gemma.createModel(
  modelType: ModelType.gemmaIt,   // an instruction-tuned Gemma variant
  maxTokens: 1024,                 // bound context to control KV-cache memory
  // preferredBackend: gpu,        // hint the accelerator; runtime falls back
);
```

Two things to notice, both straight from earlier posts. First, `setModelPath` assumes the model file is *already on the device* — how it got there (bundled in the app vs. downloaded on first run) is the shipping problem, deferred to the final post. Second, `maxTokens` bounds the context, which directly bounds the **KV cache memory** — a concrete place where the memory constraint becomes a line of code. Set it as low as your feature tolerates.

## Chat sessions and streaming

With a model loaded, you create a **chat session** that holds conversation history (and thus the KV cache), then send messages and stream the response:

```dart
// Illustrative shape.
final chat = await model.createChat(
  temperature: 0.7,
  // tokenBuffer / topK etc. as supported
);

await chat.addQueryChunk(Message.text(text: userInput, isUser: true));

// Stream tokens as they generate — do NOT block on the whole response.
final buffer = StringBuffer();
await for (final token in chat.generateChatResponseAsync()) {
  buffer.write(token);
  setState(() => _reply = buffer.toString());  // update UI incrementally
}
```

**Streaming is not optional on-device** — it's essential UX. From the edge-constraints post, on-device generation runs at tens of tokens per second, so waiting for a complete response would leave the user staring at a spinner. Streaming tokens into the UI as they arrive makes a modest generation speed *feel* responsive, because text appears immediately and continuously. Always consume the async token stream and render incrementally; never `await` the full string for anything user-facing.

Note also that the chat session *accumulates* history, which grows the KV cache with every turn (the memory constraint again). For long conversations you manage this exactly as the LLM serving series described — bound the history, or summarize older turns — so memory stays within budget.

## Keeping it responsive and safe

A few patterns make an on-device Gemma feature production-quality rather than a demo:

- **Run inference off the UI thread.** Generation is heavy; the plugin runs native inference, but coordinate so the UI stays smooth (stream updates, avoid synchronous heavy work on the main isolate). A janky UI during generation is a common first-attempt mistake.
- **Handle load failure and low memory gracefully.** On a weak device the model may fail to load or the OS may reclaim memory. Detect it, show a clear message, and (if you have one) fall back to a smaller model or a cloud path rather than crashing.
- **Show model state to the user.** Loading a model takes time; surface "preparing…" so the first interaction isn't a mysterious pause. Free/close the model when appropriate to release memory.
- **Bound generation.** Cap output length and context so a runaway generation doesn't drain battery or overheat the device (thermal/battery constraints) — and give the user a way to stop generation.

## From demo to feature

The gap between "it generated text on my phone" and "shippable feature" is exactly the constraints this series has been building around, now expressed in code:

- **Model choice → memory:** a right-sized, 4-bit Gemma model that fits your lowest-end device.
- **`maxTokens` / history management → KV cache:** bounded context so memory stays in budget across a conversation.
- **Streaming → the modest speed:** incremental rendering that makes tens-of-tokens-per-second feel instant.
- **Graceful fallback → heterogeneity:** clear handling when a device can't cope.

With this, you have a functioning on-device Gemma feature in Flutter. But an LLM alone only knows what's in its weights. To make it useful over the *user's own data* — privately, on-device — you add retrieval, which is the next post: on-device RAG and memory, done entirely without a server.

## Key takeaways

- The `flutter_gemma` plugin wraps the platform runtime behind a Dart API, turning on-device Gemma into four steps: get the model on the device, initialize it, create a chat session, and stream tokens — you write an app, not inference code. (API surface evolves; verify signatures in the package docs.)
- Add the plugin plus the platform engine (MediaPipe for mobile/web with `.task` models, LiteRT for desktop), and choose a right-sized quantized Gemma model for your lowest-end device.
- Model loading points the plugin at a file already on the device (bundling/download is the shipping problem), and `maxTokens` bounds context — a concrete line of code that bounds KV-cache memory.
- Streaming is essential, not optional: because on-device generation runs at tens of tokens/sec, consume the async token stream and render incrementally so modest speed *feels* responsive — never await the full response for user-facing text.
- Production quality comes from respecting the constraints in code: run inference off the UI thread, handle load failure/low memory gracefully with fallback, show model state, and bound generation to protect battery/thermal — plus manage growing chat history to keep the KV cache in budget.

## Further reading

- [flutter_gemma — on-device LLMs for Flutter](https://pub.dev/packages/flutter_gemma)
- [The on-device runtime (previous post)](/blog/posts/edgeai-04-the-on-device-runtime.html)
- [Google AI — Gemma models](https://ai.google.dev/gemma)
