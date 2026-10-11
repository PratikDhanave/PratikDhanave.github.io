# Markov Decision Processes — The Math That Frames Every RL Problem

*Behind every reinforcement learning algorithm is one formal structure: the Markov decision process. It's the precise way of writing down "an agent making a sequence of decisions under uncertainty," and once a problem is framed as an MDP, the whole toolkit of RL applies to it. This post builds the MDP from its parts and explains the one assumption — the Markov property — that makes the entire theory work.*

Post 1 described RL informally as an agent-environment loop. This post gives it the mathematical frame that the rest of the series stands on. You don't need heavy math to get the MDP — you need to understand its five components and why framing a problem *as* an MDP is the first real step in applying RL to anything.

## The five components of an MDP

A **Markov decision process (MDP)** is the formal model of sequential decision-making under uncertainty. It has five parts, each naming something from post 1's loop:

- **States (S)** — the set of situations the agent can be in (a chess position, a robot's sensor readings, a game screen). The state is what the agent observes to decide.
- **Actions (A)** — the choices available to the agent in each state (a legal move, a motor command).
- **Transition function (P)** — the dynamics: given a state and an action, the probability of landing in each possible next state. This is where *uncertainty* lives — the same action may lead to different outcomes (a robot's wheel slips; an opponent responds unpredictably). In many real problems the agent doesn't know P and must learn from experience.
- **Reward function (R)** — the immediate reward for a transition, the scalar signal defining the goal. *Designing the reward is designing what the agent will try to do* — and getting it wrong is a major source of RL failure (next section).
- **Discount factor (γ)** — a number between 0 and 1 that weighs future rewards against immediate ones. γ near 0 makes the agent myopic (only immediate reward matters); γ near 1 makes it far-sighted (future rewards count almost fully). Discounting both expresses "sooner is better" and keeps the math well-behaved over long horizons.

An MDP ties these together: the agent is in a state, picks an action, transitions (stochastically) to a new state and gets a reward, repeatedly. The goal, made precise: find a **policy** (post 1) that maximizes the *expected cumulative discounted reward* — the **return**. Every RL problem, from Atari to RLHF, is ultimately "solve this MDP."

## The Markov property: why the present is enough

The "Markov" in MDP is a specific, load-bearing assumption: the **Markov property** states that the future depends only on the *current* state, not on the history of how you got there. The present state captures everything relevant for deciding what to do next.

This matters enormously because it makes the problem *tractable*. If the agent had to consider its entire history at every step, the problem would be impossibly complex. The Markov property says: *forget the past; the current state is a sufficient summary.* A chess position is Markov — you don't need the move history to decide the best move, just the board. This assumption is what lets RL use the clean recursive machinery (value functions, the Bellman equation, post 3) that the whole field depends on.

The practical consequence is that **state design is everything**: the state must contain enough information to be Markov. If a robot's state is just its current camera frame, it isn't Markov — the frame doesn't capture velocity, which matters — so practitioners include velocity (or stack several frames) to *make* the state Markov. Much of the engineering of an RL problem is defining a state representation rich enough that "the present is enough" actually holds. When people say RL is hard to apply, a large part of what they mean is that framing the real problem as a clean MDP — especially designing a Markov state and a good reward — is hard.

## Reward design: the subtle, decisive part

Of the five components, the **reward function** deserves special attention because it's where RL most often goes wrong. The reward *defines the goal*, and the agent will maximize it *literally* — including in ways you didn't intend:

- **Reward hacking / specification gaming** — the agent finds a way to score high reward without achieving what you actually wanted. A classic example: an agent rewarded for *game score* in a boat race learns to loop forever hitting score-granting targets instead of finishing the race. The reward said "score," so it maximized score — exactly as asked, not as intended.
- **Sparse vs dense reward** — a reward that only arrives at the very end (win/lose) gives little signal to learn from (the credit-assignment problem, post 1, at its worst), while a denser reward (points along the way) learns faster but risks encoding the *wrong* incremental behavior. Shaping reward well is a genuine craft.
- **Alignment of reward with intent** — the deep lesson is that specifying a reward that truly captures what you want is *hard*, and the gap between "what I rewarded" and "what I meant" is where many RL failures (and AI-safety concerns) live. This is not a minor engineering detail; it's arguably the central practical difficulty of RL, and it's exactly why RLHF (post 7) *learns* a reward from human preferences rather than hand-coding one.

So the MDP's elegance — maximize reward — hides its hardest problem: saying what you actually want in the language of reward. Framing a real problem as an MDP is mostly the work of designing a Markov state and an intent-aligned reward, and that framing is where RL projects are won or lost before any algorithm runs.

The throughline: every RL problem is formalized as a **Markov decision process** — **states**, **actions**, a stochastic **transition function** (where uncertainty lives, often unknown and learned), a **reward function** (which *defines the goal*), and a **discount factor γ** (weighing future vs immediate reward) — with the objective of finding a **policy** maximizing expected cumulative *discounted* reward (the **return**). The load-bearing assumption is the **Markov property** (the future depends only on the current state), which makes the problem tractable and the recursive RL machinery possible — so **state design** must make "the present is enough" actually hold. And the subtle, decisive part is **reward design**: the agent maximizes reward *literally*, so misspecified rewards cause **reward hacking**, and aligning reward with true intent is RL's central practical difficulty — the very problem RLHF later solves by *learning* the reward.

## Key takeaways

- A **Markov decision process (MDP)** is the formal frame for every RL problem, with five parts: **states** (situations), **actions** (choices), **transition function** (stochastic dynamics — where uncertainty lives, often unknown), **reward function** (defines the goal), and **discount factor γ** (future vs immediate reward).
- The objective is a **policy** maximizing expected cumulative **discounted reward** (the **return**) — "solving the MDP" is what all RL does, from Atari to RLHF.
- The **Markov property** — the future depends only on the *current* state, not history — is the load-bearing assumption that makes RL tractable and enables the recursive value/Bellman machinery (post 3); so **state design** must make the present a sufficient summary (e.g. include velocity, stack frames).
- **Reward design is the decisive, error-prone part**: the agent maximizes reward *literally*, causing **reward hacking / specification gaming** (high score without the intended behavior); **sparse vs dense** reward trades learnability against mis-shaping.
- Aligning reward with true intent is **RL's central practical difficulty** (and an AI-safety concern) — which is exactly why **RLHF** (post 7) *learns* a reward from human preferences instead of hand-coding one; framing a real problem as a clean MDP (Markov state + intent-aligned reward) is where RL projects are won or lost.

## Further reading

- [Markov decision process — the formal model of RL](https://en.wikipedia.org/wiki/Markov_decision_process)
- [Reinforcement learning — the field MDPs frame](https://en.wikipedia.org/wiki/Reinforcement_learning)
