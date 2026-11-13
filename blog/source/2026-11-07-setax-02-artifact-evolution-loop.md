# Artifact Evolution: The Generate–Evaluate–Refine Loop

*The least philosophical form of self-evolving AI is also the one with the hardest results to argue with: hold the model fixed, hold the harness fixed, and evolve the artifact — the program, the schedule, the mathematical construction — through thousands of generate-evaluate-refine rounds. This post dissects that loop: why it's evolutionary computation with the mutation operator replaced by a language model, why the evaluator is the entire ballgame, and what changes when the LLM is both the operator and, increasingly, the optimizer.*

[Post 1](/blog/posts/setax-01-what-evolves.html) placed artifact evolution as the first locus on the map: the system improves its *products*, not itself. That modesty is exactly why it works — every hard problem of self-modification (drift, regression, inspectability) is sidestepped, because the thing changing is an external object you can test.

## The loop, piece by piece

Strip any artifact-evolution system to its skeleton and four parts remain:

- **A population of candidates** — programs, kernels, heuristics, constructions. Not one draft being polished but *many* candidates held simultaneously, because search needs diversity to escape local optima.
- **A generator** — the mutation and crossover operator. Classically this was random perturbation of a genome ([genetic programming](https://en.wikipedia.org/wiki/Genetic_programming) evolved program trees with blind syntactic edits); the modern move is to make the generator an LLM prompted with one or more parent candidates, their scores, and sometimes their failure traces. The mutations stop being random and become *semantically plausible edits* — a change to the loop bound, a different data structure, an algebraic simplification — which collapses the search space by orders of magnitude.
- **An evaluator** — a function that scores a candidate automatically, cheaply, and *honestly*: does the program compile and pass the tests, how fast does the kernel run, how good is the bound the construction achieves. The evaluator is what makes the whole loop possible; post 3 is about what happens at its edges.
- **A selector** — which candidates survive to parent the next round. Plain greedy selection converges fast and stalls fast; practical systems keep diverse niches (by approach, by size, by score profile) so the population explores several basins at once — the classic exploration/exploitation tension, inherited intact from evolutionary computation.

The loop runs: sample parents → prompt the generator for children → evaluate → select → repeat, for hundreds or thousands of rounds. No gradient anywhere; the only requirement on the objective is that it can be *measured*, which is why this family reaches places gradient methods can't — discrete structures, program spaces, objectives with no useful derivative.

## What the LLM changes, exactly

Calling this "evolution with an LLM inside" undersells two shifts. First, **the operator is knowledge-laden**: a blind mutation of source code almost always produces garbage, so classic genetic programming spent nearly all its budget on non-compiling or trivially-broken children; an LLM operator produces children that are mostly *valid and interesting*, so the same compute explores far more of the meaningful space. Second — the deeper shift — **the operator can read the evidence**: feed it the parent's profiler output, the failing test, the score history of the lineage, and the "mutation" becomes a reasoned *diagnosis-and-edit*. At that point the line between evolutionary search and iterative refinement blurs: the system is doing both, population-level search for diversity and per-candidate reasoning for depth. The practical recipe that falls out: use cheap, fast models for bulk mutation (volume matters more than brilliance per child) and reserve strong models for the rare "stuck lineage" interventions — an economics question as much as an algorithms question.

What does *not* change: the loop's honesty still rests entirely on the evaluator, and the compute bill is dominated by evaluation when candidates are expensive to test (a kernel benchmark run, a full simulation). Generator cleverness buys better children per round; it buys nothing if the evaluator rewards the wrong thing — the [Goodhart](https://en.wikipedia.org/wiki/Goodhart%27s_law) failure that post 7 treats as the universal axis.

## Where this sits on the map

Against the taxonomy's three questions: *what evolves* — the artifact only; model and harness are frozen, which is why results transfer (a faster sorting routine or matrix-multiply schedule is just… yours now, no AI attached). *What feedback* — a mechanical evaluator, the strongest feedback type there is. *Where the loop closes* — entirely offline, inside the search job; nothing persists except the winning artifact. That profile — strongest feedback, narrowest blast radius — is why artifact evolution produced the field's most defensible wins first, and it's the standard to hold the other loci to: when someone claims a system "improved itself," ask whether the improvement is as checkable as a benchmark run. Post 3 walks the domains where this profile holds, frays, and breaks.

The takeaway: artifact evolution is **evolutionary search with an LLM as the mutation operator** — population, generator, evaluator, selector — where the LLM's contribution is semantically plausible, evidence-driven edits that make the search affordable, and the evaluator's contribution is everything else. The artifact evolves; the system doesn't; the results are externally checkable and transfer freely. It's the cleanest corner of the self-evolution map, and the benchmark for honesty in every other corner.

## Key takeaways

- The skeleton is classic evolutionary computation: **population → LLM generator → automatic evaluator → diversity-preserving selector**, run for thousands of rounds, gradient-free.
- The LLM upgrades mutation from blind syntactic edits to **semantically valid, evidence-informed edits** — and can act as a per-lineage *optimizer* when fed scores and traces, blurring search into refinement.
- **The evaluator is the system**: automatic, cheap, honest scoring is the enabling condition, the compute bottleneck, and the Goodhart risk all at once.
- Taxonomy profile: artifact-only change + mechanical feedback + offline loop = **maximum checkability, minimum blast radius** — the honesty standard for the rest of the map.

## Further reading

- [Genetic programming — the ancestral discipline of evolving programs](https://en.wikipedia.org/wiki/Genetic_programming)
- [Evolutionary computation — population search beyond gradients](https://en.wikipedia.org/wiki/Evolutionary_computation)
