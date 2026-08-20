# Composing Programs

*Real tasks are pipelines, not single calls, and in DSPy you build them the way you build a neural network — subclass a base module, declare sub-modules, and wire them together in a forward method.*

Single modules handle single transformations. Real systems chain several — rewrite a query, retrieve, reason, generate, verify. DSPy composes these into a **program**: a `dspy.Module` subclass that holds sub-modules and connects them in a `forward` method. If you have used PyTorch, the shape is deliberately familiar. This fourth post in the DSPy series covers composing programs, why the structure matters for optimization, and a worked RAG example.

## A program is a module made of modules

DSPy programs are built exactly like the modules they contain — by subclassing `dspy.Module`, declaring sub-modules in `__init__`, and defining the data flow in `forward`:

```python
import dspy

class MultiHop(dspy.Module):
    def __init__(self):
        self.generate_query = dspy.ChainOfThought("question -> search_query")
        self.generate_answer = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        query = self.generate_query(question=question).search_query
        context = search(query)                     # your retriever
        return self.generate_answer(context=context, question=question)
```

Two sub-modules, each with its own signature and strategy, wired together by ordinary Python in `forward`. The control flow is just code — loops, conditionals, function calls — so a program can be as simple or as elaborate as the task needs. This is the same compositional pattern as the ReAct module you saw earlier; an agent is one kind of program, and you can write your own.

## Why the structure matters: optimization sees inside

The reason to build programs this way — rather than concatenating everything into one giant prompt — is that DSPy's optimizer can see and tune *each sub-module independently*. Because `generate_query` and `generate_answer` are declared as distinct parameterized modules, the optimizer can find the best instruction and demonstrations for the query-rewriting step *and*, separately, for the answering step. A monolithic prompt offers one blob to tune; a structured program offers several tunable components, each optimized for its own role. The structure you write is the structure the optimizer improves.

This is the payoff of the "programming, not prompting" stance at pipeline scale. You decompose the task into declared steps; DSPy compiles each step's prompt; and the whole pipeline improves against a single end-to-end metric even though its parts are tuned individually.

## A RAG program

Retrieval-augmented generation is the canonical multi-step program, and DSPy expresses it cleanly. A minimal RAG module retrieves context for the question and generates a grounded answer:

```python
class RAG(dspy.Module):
    def __init__(self, retriever):
        self.retriever = retriever
        self.respond = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retriever(question)          # returns passages
        return self.respond(context=context, question=question)

rag = RAG(my_retriever)
rag(question="What is our refund window?").answer
```

The retriever is ordinary code — any vector search, hybrid search, or API you like — and the generation step is a declared module. Because `respond` is parameterized, optimizing this program will tune how the model uses the retrieved context, improving faithfulness and answer quality against your metric without you hand-writing the RAG prompt. If you add a query-rewriting step or a reranking step, they become additional sub-modules the optimizer also tunes — the pipeline grows in structure, not in prompt-string complexity.

## Composition patterns

The `dspy.Module` + `forward` pattern accommodates the common pipeline shapes:

- **Sequential** — step feeds step, as in the RAG and multi-hop examples.
- **Conditional** — branch on an intermediate output (for example, route to different sub-modules based on a classification step, itself a module).
- **Iterative** — loop a step until a condition holds, with `forward` containing the loop (this is essentially what agent modules do internally).
- **Nested** — a program can contain other programs, since a program *is* a module; large systems compose from smaller compiled pieces.

Because it is all Python, you are not constrained by a diagram language — you express the flow directly. And because every LLM step is a declared module, every one of them remains tunable no matter how deep the composition.

## Keep programs decomposed for a reason

There is a temptation, once you know how, to collapse a pipeline back into one clever module with a huge signature. Resist it for the same reason you decompose functions in ordinary code, plus one DSPy-specific reason: a step that is folded into another cannot be optimized on its own. Keeping distinct transformations as distinct modules gives the optimizer more, smaller, better-defined targets — and each is easier to test and reason about. The right granularity is one module per genuine transformation: query rewriting, retrieval reasoning, answering, verification each earn their own module; trivial glue stays as plain code in `forward`.

## Key takeaways

- A DSPy program is a `dspy.Module` subclass that declares sub-modules in `__init__` and wires them in `forward` — the PyTorch-style compositional pattern.
- Control flow in `forward` is ordinary Python (sequential, conditional, iterative, nested), so programs are as simple or elaborate as the task needs; an agent is just one kind of program.
- Structuring the pipeline as distinct modules lets the optimizer tune each step independently while the whole improves against one end-to-end metric — a monolithic prompt offers only one blob to tune.
- RAG is the canonical program: an ordinary retriever plus a declared generation module, which optimization tunes to use context well without hand-written prompts.
- Keep genuine transformations as separate modules (more, better-defined optimization targets and easier testing); leave only trivial glue as plain code.

## Further reading

- [DSPy — official documentation](https://dspy.ai)
- [DSPy tutorials (RAG, agents) — docs](https://dspy.ai)
- [Agentic RAG series](/blog/series/agentic-rag/)
