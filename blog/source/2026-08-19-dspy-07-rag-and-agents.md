# Building RAG and Agents in DSPy

*The two systems everyone builds — retrieval-augmented generation and tool-using agents — are where DSPy's declarative approach pays off most, because they are exactly the multi-step pipelines whose prompts are hardest to tune by hand.*

With all five primitives in hand, this post assembles them into the two workhorses of production AI: a RAG pipeline and an agent. Both are multi-step programs with several promptable components, which is precisely where hand-tuning breaks down and DSPy's compile-the-prompts approach shines. This seventh post in the DSPy series builds each and optimizes it.

## RAG, end to end

A RAG program in DSPy is a `dspy.Module` that retrieves and then generates, with the generation step declared rather than prompted:

```python
import dspy

class RAG(dspy.Module):
    def __init__(self, retriever):
        self.retriever = retriever
        self.respond = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retriever(question, k=5)
        return self.respond(context=context, question=question)
```

Untuned, this already works — DSPy builds a reasonable prompt for `respond` from the signature. The value comes from optimization. Assemble a small set of `dspy.Example` question/answer pairs, write a metric that captures a good grounded answer (correctness plus, ideally, a groundedness check so the optimizer is rewarded for using the retrieved context rather than guessing), and compile:

```python
def rag_metric(example, pred, trace=None):
    return example.answer.lower() in pred.answer.lower()   # start simple; add grounding

optimizer = dspy.MIPROv2(metric=rag_metric)
compiled_rag = optimizer.compile(RAG(my_retriever), trainset=trainset)
```

Compilation tunes how the model uses the retrieved context — the instruction and the demonstrations for the `respond` step — to maximize the metric. You never wrote the RAG prompt; you declared the pipeline and defined good, and DSPy found the wording. Add a query-rewriting step (`question -> search_query`) or a reranking step as further modules and the optimizer tunes those too, turning the advanced-RAG techniques into declared, optimizable components rather than hand-crafted prompts.

## Adding multi-hop retrieval

Questions that need several retrieval steps become a program with a loop in `forward` — retrieve, reason about what's missing, retrieve again — with each reasoning step a declared module the optimizer can tune:

```python
class MultiHopRAG(dspy.Module):
    def __init__(self, retriever, hops=2):
        self.retriever = retriever
        self.hops = hops
        self.next_query = dspy.ChainOfThought("context, question -> search_query")
        self.respond = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = []
        query = question
        for _ in range(self.hops):
            context += self.retriever(query, k=3)
            query = self.next_query(context=context, question=question).search_query
        return self.respond(context=context, question=question)
```

This is the agentic-RAG pattern expressed declaratively: the `next_query` module learns, through optimization, how to formulate the follow-up search from what has been retrieved so far. The control flow is plain Python; the promptable steps are tunable modules.

## Agents with ReAct

For tasks that need tools and open-ended iteration, DSPy's `ReAct` module is the agent. You give it a signature and a set of Python functions as tools, and it runs the reason-act-observe loop:

```python
def search_docs(query: str) -> str:
    """Search internal documentation."""
    ...

def get_order(order_id: str) -> str:
    """Look up an order's status by ID."""
    ...

agent = dspy.ReAct("question -> answer", tools=[search_docs, get_order])
agent(question="Where is order 4021, and what's our return policy?").answer
```

The tools are ordinary functions with docstrings and typed signatures — DSPy uses those to tell the model what each tool does and how to call it, the same discipline good tool design demands everywhere. And because `ReAct` is a module, it optimizes like any other: compiling an agent tunes the instruction and demonstrations that guide its tool selection and reasoning, so the agent gets better at *choosing and using* its tools against your metric — including a metric that inspects the trajectory (via the `trace` parameter) to reward efficient, correct tool use rather than only the final answer.

## Optimizing the whole pipeline

The unifying point is that RAG pipelines and agents are just programs, so the entire workflow you have learned applies: declare the steps, define a metric that captures end-to-end quality, and compile. The optimizer improves every declared module in the pipeline against one objective — the query rewriter, the multi-hop reasoner, the answerer, the agent's tool-use reasoning — even though you tuned nothing by hand. This is DSPy's strongest case: on exactly the multi-step systems where hand-written prompts are most brittle and most numerous, it replaces prompt archaeology with a metric and a compile.

## Keep it grounded and measured

Two cautions carry over from the rest of the series. First, optimization is only as good as the metric: for RAG, reward groundedness and not just surface answer-match, or the optimizer may learn to produce confident answers that ignore the context. Second, agents multiply cost and failure surface — more steps, more tool calls, more tokens — so apply DSPy's discipline of measuring: compile the simplest program that meets the metric, and only add hops, tools, or reflection when the evaluation shows they earn their cost. DSPy makes it easy to *build* these systems; the metric and the evaluation are what keep them honest.

## Key takeaways

- RAG in DSPy is a `dspy.Module` that retrieves (ordinary code) and generates (a declared module); compiling it tunes how the model uses retrieved context, with no hand-written RAG prompt.
- Multi-hop retrieval is a program with a loop in `forward` and a declared `next_query` module the optimizer teaches to formulate follow-up searches — agentic RAG, expressed declaratively.
- Agents are the `dspy.ReAct` module: Python functions as tools (docstrings + typed signatures describe them), and compiling the agent tunes its tool-selection and reasoning against your metric.
- RAG pipelines and agents are just programs, so declare steps → define an end-to-end metric → compile; the optimizer improves every module at once against one objective.
- Reward groundedness (not just answer-match) for RAG, and use trajectory-aware metrics for agents; build the simplest program that meets the metric and add complexity only when evaluation shows it pays.

## Further reading

- [DSPy tutorials (RAG, agents) — official docs](https://dspy.ai)
- [Agentic RAG series](/blog/series/agentic-rag/)
- [DSPy paper — Khattab et al., 2023](https://arxiv.org/abs/2310.03714)
