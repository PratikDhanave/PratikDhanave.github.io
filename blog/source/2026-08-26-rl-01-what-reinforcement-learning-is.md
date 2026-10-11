# What Reinforcement Learning Is — Learning from Consequences

*Supervised learning needs a teacher who knows every right answer; reinforcement learning needs only a goal and the freedom to try. It's how a system learns to play a game, control a robot, or — increasingly — align a language model, not by being shown correct outputs but by acting, seeing what happens, and learning from the consequences. This series builds RL from first principles, and it starts with why "learning from reward" is a fundamentally different and more general kind of learning.*

This series is the dedicated treatment of the third ML paradigm from the [Machine Learning from First Principles](/blog/series/machine-learning-from-first-principles/) series. RL is the backbone of game-playing AI, robotics, and — the reason it matters to everyone now — RLHF, the technique that turns a raw language model into a helpful assistant. Post 1 sets up the whole framework: the agent, the environment, the reward, and the hard problems that make RL its own discipline.

## Learning by interaction, not by examples

In supervised learning (the ML series), every training example comes with the correct answer, and the model learns to reproduce it. That's unavailable for a huge class of problems: nobody can give the "correct" move for every chess position, or the correct motor command for every instant of a robot's walk. What you *can* specify is a **goal** — win the game, stay upright, maximize the score — and let the system figure out how to achieve it.

**Reinforcement learning** is learning to act by **interacting with an environment to maximize cumulative reward**. There's no answer key; there's only feedback — a reward signal that says how well things are going — and the learner must discover, through trial and error, which actions lead to good outcomes. This is closer to how animals and humans actually learn: a child learns to walk not by being shown the correct joint angles but by trying, falling, and adjusting. RL formalizes learning from *consequences* rather than from *instruction*.

The practical upshot: RL applies where you can define *what success looks like* (the reward) but not *how to achieve it* (the policy). That's an enormous and important class — games, control, resource allocation, and the alignment of AI systems — and it's exactly where supervised learning can't reach.

## The core loop: agent, environment, reward

RL's framework is a loop between two entities, and nearly all its vocabulary comes from naming the parts:

- **The agent** — the learner and decision-maker (the game player, the robot controller, the trading system).
- **The environment** — everything the agent interacts with and can't directly control (the game, the physical world, the market).
- The loop: at each step the agent observes the environment's **state**, chooses an **action**, and the environment responds with a new state and a **reward** — a scalar number signaling how good that transition was. The agent's goal is to choose actions that maximize **cumulative** reward over time.
- **The policy** — the agent's strategy: a mapping from states to actions. Learning, in RL, *means improving the policy* until it reliably earns high reward. The policy is the thing RL produces, the analog of the "trained model" in supervised learning.

The subtle, defining feature is that reward is often **delayed**. The action that wins a chess game might have been made thirty moves earlier; the reward (winning) arrives long after the decisive move. So the agent can't just maximize immediate reward — it must learn which actions lead to good outcomes *eventually*, assigning credit backward through time. This **credit assignment problem** — figuring out which of many past actions deserves the reward — is the heart of what makes RL hard and interesting, and the next posts (value functions, Bellman equations) are largely about solving it.

## The two hard problems that define RL

Two challenges, absent from supervised learning, give RL its distinctive character and drive almost all of its algorithms:

- **The exploration–exploitation trade-off.** The agent faces a constant dilemma: **exploit** what it already knows works (take the action that's paid off before) or **explore** something new that *might* be better but might be worse? Pure exploitation gets stuck in mediocre habits; pure exploration never cashes in what it learned. Every RL algorithm must balance the two — try enough new things to discover good strategies, while increasingly favoring what works. This dilemma, in its purest form, is the **multi-armed bandit** problem, and it has no equivalent in supervised learning, where the data is simply given.
- **Delayed reward and credit assignment** (above) — learning which actions, among a long sequence, were actually responsible for an outcome that arrived much later. This is why RL needs the machinery of *value* (estimating the long-term worth of states and actions) rather than just reacting to immediate reward.

These two problems are why RL is a separate discipline rather than a flavor of supervised learning. The agent is learning from a sparse, delayed, self-generated signal while simultaneously deciding how much to gamble on the unknown — a genuinely harder learning problem, and the reason RL is both powerful and notoriously finicky.

The throughline: **reinforcement learning** is learning to act by **interacting with an environment to maximize cumulative reward** — no answer key, only a goal and trial-and-error feedback — so it reaches the vast class of problems where you can define *success* (the reward) but not *how* to achieve it (games, control, AI alignment). Its framework is the loop of **agent**, **environment**, **state → action → reward**, producing a **policy** (state→action strategy, the thing RL learns). What makes it hard and distinct: reward is often **delayed**, creating the **credit assignment** problem, and the agent must constantly balance **exploration vs exploitation** (the multi-armed bandit dilemma) — two challenges with no analog in supervised learning, and the source of everything that follows.

## Key takeaways

- **Reinforcement learning** learns to act by **interacting with an environment to maximize cumulative reward** — no labeled right answers, only a goal and trial-and-error feedback — modeling learning from *consequences* (how animals learn) rather than *instruction*.
- It applies wherever you can specify **what success looks like** (the reward) but not **how to achieve it** (the policy): games, robotics/control, resource allocation, and AI alignment — a class supervised learning can't reach.
- Core framework: the **agent** (learner) interacts with the **environment** via a loop of **state → action → reward**, aiming to maximize *cumulative* reward; the learned output is a **policy** (states → actions), the analog of a trained model.
- Reward is often **delayed**, creating the **credit-assignment problem** — figuring out which of many past actions earned a much-later reward — which is why RL needs the notion of *value* (long-term worth), developed in later posts.
- Two defining challenges with no supervised-learning analog: the **exploration–exploitation trade-off** (exploit known-good actions vs explore possibly-better ones — the **multi-armed bandit** in pure form) and **delayed reward/credit assignment** — together making RL its own, harder discipline.

## Further reading

- [Reinforcement learning — learning to act from reward](https://en.wikipedia.org/wiki/Reinforcement_learning)
- [Multi-armed bandit — the exploration–exploitation dilemma](https://en.wikipedia.org/wiki/Multi-armed_bandit)
