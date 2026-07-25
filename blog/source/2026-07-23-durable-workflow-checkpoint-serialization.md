# "maximum recursion depth exceeded": A Durable-Workflow Checkpointing War Story
*Passing an SDK client through a checkpointed agent workflow crashed on circular references. The fix reshaped how I cross @step boundaries.*

I was building a governed multi-agent workflow in Python on Microsoft Agent Framework. The orchestration used the framework's native `@workflow` and `@step` decorators to get durable execution for free: a pipeline that moves a case through triage, enrich, diagnose, approval, and close, where the approval stage suspends the whole workflow until a human responds — maybe seconds later, maybe the next morning.

Durable execution is the whole point. The framework serializes the entire workflow message dict *and* every `@step`'s arguments and results, writes that to a checkpoint store, and can rehydrate the run later. That is how a workflow survives a process restart and how human-in-the-loop approval works at all. It is also, as I learned the hard way, a serialization boundary I had been treating like an ordinary function call.

## The first crash: a live client in the message

My triage stage needed a classifier, and the classifier needed a live Azure `AIProjectClient` built from a `DefaultAzureCredential`. The obvious thing — the thing you'd do in any non-durable pipeline — is to construct the client at startup and thread it through the workflow message so each stage can reach it.

That crashed immediately with `maximum recursion depth exceeded`. No line number in my code, just a wall of stack frames deep inside the checkpoint serializer.

The reason is structural, not incidental. When the checkpoint layer serializes the workflow message, it walks the entire object graph reachable from that message. An `AIProjectClient` and a `DefaultAzureCredential` are not leaf values — they hold transport pools, config objects, cached token providers, and back-references between them. The serializer follows a reference, which points back to an object it is already inside, and recurses until Python's stack gives out. The "recursion depth" error is really "you handed me a cyclic graph and asked me to turn it into flat bytes."

The rule that fell out of this: **never put a live SDK client in serialized workflow state.** Not in the message, not in a `@step` argument, not in a `@step` result.

## The injection sidestep

So how does the classifier get its client if the client can't ride through the message? Out-of-band, at the composition root, via a module-level setter — and the triage step deliberately opts out of serialization.

```python
# classifier.py — module-level injection point
_classifier = None

def set_classifier(client):
    """Called ONCE from the composition root, before the workflow runs."""
    global _classifier
    _classifier = client

def triage(case: dict) -> dict:   # NOT decorated with @step
    # Reads the live client from module state, never from the message.
    label = _classifier.classify(case["summary"])
    return {**case, "label": label}
```

```python
# main.py — composition root
client = AIProjectClient(credential=DefaultAzureCredential(), ...)
set_classifier(client)          # inject once, out-of-band
run_workflow(case)              # the message carries only JSON-shaped data
```

Two decisions are doing the work here. First, `set_classifier()` injects the live client through a module-level global that lives entirely outside the serialized message graph — the checkpoint serializer never sees it. Second, `triage` is intentionally *not* decorated with `@step`, so its arguments and return value are never captured into a checkpoint. The non-serializable dependency and the serialization boundary never touch.

Contrast that with the tempting version:

```python
# DON'T: client rides through the message, gets walked by the serializer
def run_workflow(case, client):
    case["_client"] = client     # boom on the next checkpoint
```

Here is the boundary, drawn out:

```
   COMPOSITION ROOT                        CHECKPOINT STORE
   (process memory)                        (durable, JSON-only)
   ┌────────────────────┐                  ┌────────────────────────┐
   │ AIProjectClient    │                  │ workflow message dict  │
   │ DefaultAzure       │                  │   { "case_id": "...",  │
   │   Credential       │                  │     "label": "...",    │
   │ classifier         │                  │     "stage": "triage"} │  <- JSON OK
   └─────────┬──────────┘                  │                        │
             │                             │ @step args / results   │
   set_classifier(client)                  │   ["workload:tool"]     │  <- string key OK
             │ (module-level, out-of-band) └────────────────────────┘
             ▼
   ┌────────────────────┐        @workflow / @step boundary
   │ module global      │   ─────────────╪══════════════════─────────►
   │ _classifier        │                ║  serializer walks graph
   └────────────────────┘                ║
                                         ║  live client  ->  recursion depth EXCEEDED
                                         ║  (workload,tool) tuple key -> cannot encode
                                         ║  plain to_dict() (live events) -> won't round-trip
```

Everything on the right of the double line has to be flat data. Anything that can't be flat data goes in on the left, through the composition root, and is reached by reference at runtime.

## The second crash: tuple dict keys

With clients out of the message, the workflow ran — until a later stage checkpointed a policy map. My policies were keyed by `(workload, tool)` tuples, which is idiomatic, fast Python. The durable backend rejected it.

JSON object keys must be strings. Python's own `json.dumps` will happily stringify an `int` key, but a `tuple` key has no JSON representation at all, and the durable checkpoint backend won't invent one. The fix was to flatten the composite key into a string:

```python
policy[f"{workload}:{tool}"] = rule    # "batch:scanner", not (workload, tool)
```

This is the part that surprised me most, so it is worth stating plainly: the serialization boundary applies to dict **keys**, not just values. "JSON-serializable" has to hold all the way down — every value *and* every key that crosses a `@workflow` or `@step` boundary.

## The third trap: encode with the framework's codec

The last issue wasn't a crash so much as a checkpoint that looked fine and didn't round-trip. When I wired up a custom durable store, I reached for the workflow object's `to_dict()` to persist it. It serialized, it saved, and on resume it was subtly wrong — because a raw `to_dict()` still holds live `WorkflowEvent` objects that don't survive a store-and-reload cycle.

The framework ships a codec for exactly this: `encode_checkpoint_value` and `decode_checkpoint_value`. Those functions know how to turn framework internals into something a durable store can hold and reconstruct them faithfully on the way back. A durable store must go through the codec on both ends. Hand-rolling `to_dict()` skips the part of the encoding that makes the checkpoint actually durable.

## Lessons

The single idea that would have saved me three debugging sessions: **the checkpoint boundary is a serialization boundary, and you should treat it exactly like a network wire.** Everything crossing a `@workflow`/`@step` boundary is going over that wire as JSON — values and keys alike — so live SDK clients, credentials, tuple keys, and objects holding cyclic references simply cannot cross it. The move is not to serialize harder; it's to keep non-serializable things off the wire entirely. Inject live clients out-of-band at the composition root through a module-level setter, keep the dependency-heavy stage undecorated so its args never get captured, flatten composite keys to strings, and always encode and decode through the framework's own codec. Once you internalize that the message and every `@step` signature are data-only channels, the whole class of "maximum recursion depth exceeded" checkpoint failures disappears — and you get durable, human-in-the-loop workflows that suspend and resume without surprises.
