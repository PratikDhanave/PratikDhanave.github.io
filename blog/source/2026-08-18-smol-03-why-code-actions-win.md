# Why Code Actions Win

*The claim that agents should write code isn't just aesthetic — Hugging Face backs it with measured results: code agents take fewer steps, make fewer LLM calls, and score better on hard benchmarks. This post examines the evidence and the mechanism, so you understand not just that code actions win but why.*

The last post explained *what* code actions are. This one examines *why they win* — the concrete efficiency and accuracy advantages Hugging Face reports, and the mechanism behind them. The claim is that code agents are meaningfully better than JSON tool-calling agents on substantive tasks, and it's worth understanding the reasoning, because it tells you *when* the advantage is real. (Figures are Hugging Face's reported results on their benchmarks — directional, verify on your workload.)

## The efficiency advantage

The headline result: code agents are reported to reduce the number of **steps and LLM calls by around 30%** compared to standard tool-calling, on the tasks measured. That's a substantial efficiency gain, and it follows directly from the code-action mechanism (the last post):

- **Fewer round-trips** — because one code action can call multiple tools, loop over results, and compose them, work that takes *many* JSON tool-call round-trips (each a separate LLM turn) collapses into *one* code action with *one* LLM turn. Fewer turns means fewer LLM calls.
- **Fewer steps to a solution** — the agent reaches the answer in fewer overall actions, because each action accomplishes more.

The efficiency gain matters on two fronts covered elsewhere in this blog:

- **Cost** — fewer LLM calls means fewer tokens and lower cost (the cost playbook's concern) — a ~30% reduction in calls is a direct cost lever, on top of everything else.
- **Latency** — fewer round-trips means less back-and-forth with the model, so the agent finishes faster — each JSON round-trip is a model call with its own latency, and collapsing many into one code action cuts total latency.

So the code agent's expressiveness (from the last post) isn't just elegant — it translates into measurably fewer, more-productive steps, which is fewer calls, lower cost, and lower latency. That's a concrete, multi-dimensional win, not just a nicer programming model.

## The accuracy advantage

Beyond efficiency, code agents are reported to achieve **superior performance on complex benchmarks** — better *accuracy*, not just fewer steps. This is the more surprising claim (you might expect a tradeoff — faster but worse), and the mechanism explains why there isn't one:

- **Code matches the task's structure** — complex tasks involve logic, composition, and computation (the last post), which code expresses naturally and JSON tool-calling expresses awkwardly through many turns. Expressing the action in the right language leads to *better* actions, hence better results.
- **Fewer turns means fewer places to go wrong** — each JSON round-trip is a chance for the model to lose track, misread an intermediate result, or drift; collapsing work into a coherent code action reduces those failure points.
- **Code plays to the model's strengths** — models reason well in code (the last post), so letting them act in code produces more capable actions than forcing a constrained JSON format.

So code agents are reported to be *both* more efficient *and* more accurate on complex tasks — an unusual combination that comes from aligning the action format with both the task's structure and the model's strengths. The absence of a speed-vs-accuracy tradeoff is the strongest part of the case: you're not trading quality for efficiency; the same mechanism delivers both.

## The mechanism, restated

It's worth restating *why* one mechanism delivers both efficiency and accuracy, because that's the deep point:

Complex agentic work is fundamentally about *composing* operations — call this, use its result to do that, loop, combine, compute. A programming language is *built* to express composition; a list of isolated JSON function calls is not. So when you let the agent act in code, you let it express the composed action *directly and correctly in one step*, whereas JSON tool-calling forces the agent to decompose that composition into many single-call turns, threading intermediate results back through the model as text each time. The single code action is both *fewer steps* (efficiency) and *less error-prone* (accuracy), because the composition stays intact in code rather than being fragmented across turns. One mechanism — actions as composable code — produces both wins, because both problems (too many steps, too many error points) come from the same root: fragmenting composed work into isolated calls.

## When the advantage is real (and when it isn't)

The evidence is compelling, but the advantage is strongest for a specific kind of task, and honesty requires the boundary:

- **Code actions win most** on tasks that genuinely involve composition, logic, loops, and computation — where the "one code action does the work of many calls" effect is large. Data manipulation, multi-tool workflows, computational tasks, and complex reasoning-plus-action are the sweet spot.
- **The advantage shrinks** for *simple* tasks that really are just one isolated tool call — where there's nothing to compose, a code action and a JSON tool call do the same thing, and the simpler tool-calling agent is fine (the last post's guidance). Not every task has composition to exploit.
- **The advantage is real but directional** — the ~30% and accuracy figures are Hugging Face's on their benchmarks; the *shape* of the advantage (fewer steps, better composition) is sound, but the magnitude on *your* workload depends on how much composition your tasks involve. Measure it (the cost playbook's discipline).

So code actions win because they align the action format with composed work and with the model's code fluency — delivering fewer steps *and* better accuracy where tasks involve real composition, which is most substantive agentic work. The advantage is genuine and mechanistically sound, largest where composition is heaviest, and directional in magnitude. But executing model-written code introduces a serious cost — security — which the next post addresses, because it's the price of this power.

## Key takeaways

- Code agents are reported to reduce steps and LLM calls by ~30% versus JSON tool-calling, because one code action collapses work that would take many round-trips (call, loop, call, compose) into a single LLM turn — a direct cost and latency win.
- They're also reported to achieve better accuracy on complex benchmarks — not a speed-vs-quality tradeoff — because code matches the task's structure, fewer turns mean fewer places to drift, and code plays to models' code-training strengths.
- One mechanism delivers both wins: complex work is about composing operations, which code expresses directly in one intact step while JSON tool-calling fragments it into many error-prone turns — so fewer steps (efficiency) and less fragmentation (accuracy) share the same root.
- The advantage is largest for tasks with real composition (logic, loops, multi-tool workflows, computation) and shrinks for simple single-tool-call tasks (where a tool-calling agent is fine) — it's genuine and mechanistically sound but its magnitude on your workload depends on how much composition your tasks involve.
- The figures are Hugging Face's directional benchmark results — verify on your workload — and the power of executing code comes with a serious security cost (sandboxing), the subject of the next post.

## Further reading

- [Code agents: actions as code (previous post)](/blog/posts/smol-02-code-agents.html)
- [smolagents documentation](https://huggingface.co/docs/smolagents/index)
- [The AI Cost Optimization Playbook — fewer LLM calls as a cost lever](/blog/series/the-ai-cost-optimization-playbook/)
