# Elementary Cellular Automata — The Simplest Possible Rules

*To understand cellular automata, start with the simplest possible version: a single line of cells, each either black or white, each updating based only on itself and its two immediate neighbors. These elementary cellular automata are about as minimal as a system can be — and yet, astonishingly, some of them produce patterns of unlimited complexity. This post is about the simplest CAs, how their 256 rules are numbered, and the shocking discovery that minimal rules can be maximally complex.*

Post 1 introduced cellular automata in general; this post examines the *simplest* case, which is where the field's most surprising results were found. Elementary CAs are minimal enough to enumerate completely (there are exactly 256) yet rich enough to contain genuine complexity — making them the perfect laboratory for the series' core theme of complexity from simplicity.

## The simplest cellular automaton

An **elementary cellular automaton** is the most minimal CA possible:

- **One dimension** — cells form a single *line* (not a 2D grid).
- **Two states** — each cell is black or white (1 or 0).
- **Nearest-neighbor** — each cell's next state depends only on *three* cells: itself and its immediate left and right neighbors.

That's it — a row of cells, each looking at itself and its two neighbors, updating by a fixed rule, step after step. To visualize the evolution, we draw each successive step as a new row below the previous one, so the 1D line evolving over time becomes a 2D picture (time running downward) — which is how elementary CAs are famously displayed. This minimal setup is deliberately as simple as a cellular automaton can be, which makes what it can do all the more remarkable.

The beauty of this minimality is that you can *enumerate every possible rule*. Since a cell's next state depends on three cells, each on/off, there are 2³ = 8 possible neighborhood configurations (000, 001, 010, …, 111). A *rule* specifies the next state (0 or 1) for each of those 8 configurations — so a rule is 8 bits, and there are exactly 2⁸ = **256 possible elementary CA rules**. The entire space of the simplest cellular automata is just 256 rules, each completely specifiable and studiable. This completeness is why elementary CAs are such a clean laboratory: you can examine *all* of them.

## Wolfram numbering: naming the 256 rules

Because each rule is 8 bits (the output for each of the 8 neighborhood configurations), each rule corresponds to a number from 0 to 255 — its **Wolfram code**. You list the 8 configurations in a fixed order and read off the 8 output bits as a binary number; that number names the rule. "Rule 30," "Rule 90," "Rule 110" — these famous names are just the decimal values of the 8-bit output patterns. This numbering (introduced by Stephen Wolfram, who extensively studied these systems) gives every elementary CA a simple name, making it easy to refer to and compare specific rules. It's a neat encoding: the entire behavior of an elementary CA is captured in a single number 0–255.

What makes this more than bookkeeping is that *different rule numbers produce wildly different behavior*, and studying all 256 reveals the full range of what even the simplest CAs can do. Some rules are boring; some are astonishing — and which is which is not at all obvious from the rule number. You largely have to *run* the rule to see what it does (a hint of the deep unpredictability in post 4).

## The shock: simple rules, unlimited complexity

Here is the discovery that made elementary CAs famous and reshaped how people think about complexity. Among the 256 trivial rules, the behaviors fall into strikingly different categories:

- **Some rules are simple/boring** — they die out to all-white, settle into a uniform or simple repeating pattern, or produce regular, predictable structures (like nested triangles). Unsurprising: simple rule, simple result.
- **Some rules are chaotic** — they produce patterns that look essentially random, with no discernible structure, despite the completely deterministic rule. **Rule 30** is the famous example: from a single black cell, it generates a pattern so random-looking that it has been used as a *random number generator* — genuine-seeming randomness from a trivial deterministic rule and a single starting cell. This is already shocking: pure determinism producing apparent randomness.
- **Some rules are complex** — and this is the profound category — producing patterns that are *neither* simple/repetitive *nor* fully random, but a rich mix: localized structures, some moving, interacting against a patterned background, with intricate, unpredictable, organized-yet-irregular behavior. **Rule 110** is the celebrated example, and (post 5) it turns out to be capable of *universal computation* — the simplest known Turing-complete system.

The shock is the sheer *disproportion*: these rules are about as simple as a rule can possibly be — 8 bits, three-cell neighborhoods — and yet some of them produce behavior of unlimited complexity, apparent randomness, and even universal computation. This was a genuinely surprising empirical discovery (central to Wolfram's *A New Kind of Science*): **complexity is not rare or requiring of complex rules — it appears even among the very simplest possible rules.** You don't have to build something complicated to get complexity; it's already there, lurking in rules a child could specify. Elementary CAs made this concrete and undeniable by exhibiting it in the simplest systems imaginable, which is why they're foundational to how we now understand the relationship between simplicity and complexity.

The through-line: an **elementary cellular automaton** is the simplest CA — a **1D line**, **two states**, **nearest-neighbor** (each cell depends on itself + 2 neighbors) — minimal enough that there are exactly **256 possible rules** (3 cells → 8 neighborhood configs → 8 output bits → 2⁸ rules), each nameable by its **Wolfram number** (0–255, the decimal of its 8 output bits: Rule 30, Rule 90, Rule 110). The shock, found by enumerating all 256: behaviors range from **simple/repetitive** to **chaotic** (Rule 30 — apparent randomness from a deterministic rule, used as an RNG) to **complex** (Rule 110 — organized-yet-irregular structures, later shown universal, post 5) — and crucially, **complexity appears even among the very simplest possible rules**, the surprising empirical discovery (central to Wolfram's work) that *complexity needs no complex cause and is lurking in trivial rules*. Elementary CAs are the clean, enumerable laboratory that made this undeniable.

## Key takeaways

- An **elementary cellular automaton** is the simplest CA: **1D** (a single line of cells), **two states** (black/white), **nearest-neighbor** (next state depends only on the cell + its immediate left and right — three cells); evolution is drawn as successive rows (time downward) making a 2D picture.
- Its minimality means you can **enumerate every rule**: 3 cells → **8 neighborhood configurations** → a rule assigns an output bit to each → **2⁸ = 256 possible rules** total — the entire space of the simplest CAs is completely studiable.
- Each rule is named by its **Wolfram code** (0–255) — the decimal value of its 8 output bits — giving famous names like **Rule 30, Rule 90, Rule 110**; different rule numbers produce wildly different behavior, and you largely have to *run* a rule to see what it does.
- Enumerating all 256 reveals strikingly different behavior classes: **simple/boring** (die out, uniform, or regular nested patterns), **chaotic** (**Rule 30** — apparent randomness from a deterministic rule and one starting cell, used as a random-number generator), and **complex** (**Rule 110** — organized-yet-irregular interacting structures, later shown **universal**/Turing-complete, post 5).
- The profound shock is the **disproportion**: these are about as simple as rules can be (8 bits, 3-cell neighborhoods), yet some produce unlimited complexity, apparent randomness, and universal computation — the surprising empirical discovery (central to Wolfram's *A New Kind of Science*) that **complexity appears even among the very simplest rules** and is *lurking in trivial rules*, not requiring complex causes.

## Further reading

- [Elementary cellular automaton — the 1D, 2-state, nearest-neighbor CAs](https://en.wikipedia.org/wiki/Elementary_cellular_automaton)
- [Rule 30 — apparent randomness from a trivial deterministic rule](https://en.wikipedia.org/wiki/Rule_30)
