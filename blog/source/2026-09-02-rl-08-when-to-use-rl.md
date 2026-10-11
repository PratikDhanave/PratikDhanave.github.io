# When to Use Reinforcement Learning — Power, Cost, and Honest Judgment

*Reinforcement learning is the most seductive paradigm in machine learning: define a goal, let an agent figure out the rest. It's also the hardest to get working and the easiest to misapply. This closing post is the practical judgment the series was building toward — where RL genuinely shines, where a simpler method is the honest choice, and how to recognize which situation you're in. It's the difference between RL as a tool and RL as a trap.*

Posts 1–7 built RL from the agent-environment loop to RLHF. This post steps back to the engineering decision: *should you use RL at all?* The answer is "less often than its excitement suggests, but when it fits, nothing else will do" — and knowing which is which is what separates practitioners from enthusiasts.

## What makes RL hard to apply

RL's difficulties aren't incidental; they're structural, and they explain why RL is far less deployed than supervised learning despite its fame:

- **Sample inefficiency** (post 5). RL often needs millions of trials to learn, which is fine in a simulator but ruinous when each trial costs real time, money, or safety. This single fact rules RL out for most real-world problems where you can't cheaply generate experience.
- **Reward design is hard** (post 2). Specifying a reward that captures what you actually want — without inviting reward hacking — is genuinely difficult, and a misspecified reward produces an agent that confidently does the wrong thing. Many RL failures are reward failures.
- **Instability and finickiness** (post 5). Deep RL is sensitive to hyperparameters, seeds, and implementation details; results are hard to reproduce and tuning is an art. It demands more engineering effort and expertise than most ML.
- **The exploration problem** (post 1). Exploration can be unsafe (a robot trying random actions) or simply inefficient, and in many real environments you can't let an agent explore freely at all.

The honest summary: RL trades the *need for labels* (its great advantage) for a *need for enormous, often unsafe, trial-and-error interaction and delicate tuning* (its great cost). That trade is worth it sometimes, and badly not worth it often.

## When RL is the right tool — and when it isn't

A practical decision rule emerges from the series. **Reach for RL when all of these hold:**
- The problem is genuinely **sequential decision-making** — a series of decisions where earlier actions affect later options, and you care about *long-term* cumulative outcome, not a single prediction. (If it's one input → one prediction, it's supervised learning, not RL.)
- You can specify a **reward** (what success looks like) but *not* the correct actions (how to achieve it). This is RL's sweet spot and the thing that rules out supervised learning.
- You have a **cheap way to generate experience** — a simulator, a game, or a setting where trial-and-error is safe and fast — *or* you can learn from a bounded feedback set (like RLHF's human preferences) rather than open exploration.

**Lean away from RL when:**
- The problem is really a **prediction** (classification/regression) — use supervised learning; it's simpler, more reliable, and more sample-efficient.
- A **simpler method or heuristic** solves it well enough — a rule, an optimizer, or a bandit algorithm often beats full RL at far less cost. (Not every sequential problem needs RL; many yield to classical optimization or control theory.)
- You **can't simulate** and real trials are expensive or unsafe, and you have no bounded-feedback substitute — RL's sample appetite makes it impractical.
- You can't specify a **trustworthy reward** — if you can't say what you want without inviting reward hacking, RL will optimize the wrong thing.

The most common mistake is reaching for RL because it's exciting when the problem is actually a supervised or optimization problem in disguise. The second most common is underestimating the engineering cost. RL's power is real, but it's a specialized tool, not a default.

## Where RL genuinely shines — and the frontier

Despite the caveats, RL is irreplaceable in a specific and important set of domains, and it's worth closing the series by naming where the investment pays:

- **Games and simulation** — the natural home: cheap, fast, safe experience and clear reward. RL's landmark results (post 5) all live here, and games remain where RL is most reliably successful.
- **Control and robotics** — continuous control (post 6) where you can simulate: locomotion, manipulation, autonomous systems, datacenter and energy optimization. The pattern is train-in-sim, transfer-to-real.
- **Aligning AI systems** — RLHF (post 7) and its descendants, the most consequential current use, where RL optimizes toward human-judged goals that can't be specified directly. This is where RL touches nearly everyone, through the assistants it helped create.
- **Sequential optimization under uncertainty** — recommendation as a long-term engagement problem, resource allocation, trading, operations — wherever decisions compound over time and you can model or simulate the dynamics.

The frontier is largely about attacking RL's weaknesses: **sample efficiency** (model-based RL that learns a world model to practice in, reducing real trials), **offline RL** (learning from logged data without live exploration, opening real-world domains where exploration is impossible), and the broad move — exemplified by RLHF — toward *learning rewards and dynamics* rather than hand-specifying them. These directions aim to keep RL's unique strength (optimizing long-term goals you can judge but not specify) while taming its costs.

The series' final lesson: reinforcement learning is the right frame for *sequential decision-making to maximize long-term reward when you can judge success but not dictate the actions* — a genuinely distinct and powerful capability no other ML paradigm offers. But it comes at the price of sample-hunger, reward-design difficulty, and instability, so the mark of judgment is reaching for it only when the problem truly fits and a simpler method won't do — and recognizing, as RLHF so vividly shows, that RL's deepest value is optimizing toward the goals we can recognize but never quite write down.

The throughline: RL is powerful but **hard to apply** — **sample-inefficient** (millions of trials), **reward-design-sensitive** (misspecification → confident wrong behavior), **unstable/finicky**, and **exploration-limited** (often unsafe) — trading supervised learning's need for labels for a need for massive, often unsafe trial-and-error. **Use RL when** the problem is genuinely **sequential decision-making** for long-term reward, you can specify a **reward but not the actions**, and you have **cheap/safe experience** (a simulator) or a **bounded feedback set** (RLHF). **Avoid it when** it's really prediction (use supervised), a simpler method/heuristic suffices, you can't simulate and real trials are costly/unsafe, or you can't specify a trustworthy reward. It genuinely shines in **games/simulation, control/robotics, AI alignment (RLHF), and sequential optimization**, with the frontier (model-based, offline RL, learned rewards) attacking its costs — and its deepest value is optimizing toward goals we can *judge but not specify*.

## Key takeaways

- RL is **structurally hard to apply**: **sample-inefficient** (millions of trials — ruinous outside simulators), **reward-design is hard** (misspecification → confident wrong behavior/reward hacking), **unstable and finicky** (hyperparameter/seed sensitive), and **exploration can be unsafe** — it trades the need for labels for a need for massive, often unsafe interaction.
- **Use RL when all hold**: genuinely **sequential decision-making** optimizing *long-term* cumulative reward (not one-shot prediction), you can specify a **reward but not the correct actions**, and you have **cheap/safe experience** (a simulator) *or* a bounded feedback set (RLHF's human preferences).
- **Avoid RL when**: it's really **prediction** (use supervised learning — simpler, more reliable, more sample-efficient), a **simpler method/heuristic/bandit** suffices, you **can't simulate** and real trials are costly/unsafe, or you **can't specify a trustworthy reward**.
- The two common mistakes: reaching for RL because it's exciting when the problem is a supervised/optimization problem in disguise, and underestimating its engineering cost — RL is a **specialized tool, not a default**.
- RL genuinely shines in **games/simulation**, **control/robotics** (train-in-sim, transfer-to-real), **AI alignment (RLHF)** — its most consequential current use — and **sequential optimization under uncertainty**; the frontier (model-based RL, **offline RL**, learned rewards) targets its sample/safety costs. Its deepest value: optimizing toward goals you can **judge but not specify**.

## Further reading

- [Reinforcement learning — applications, strengths, and limits](https://en.wikipedia.org/wiki/Reinforcement_learning)
- [Reinforcement learning from human feedback — RL's most consequential modern use](https://en.wikipedia.org/wiki/Reinforcement_learning_from_human_feedback)
