# Value Functions and the Bellman Equation — Thinking Ahead

*The key idea that makes reinforcement learning work is deceptively simple: instead of chasing immediate reward, estimate the long-term value of being in a situation, and act to move toward high-value situations. Value functions are how an agent "thinks ahead," and the Bellman equation is the elegant recursive relationship that makes computing them possible. This is the conceptual core of RL — grasp it and the algorithms become obvious.*

Post 2 framed the problem as maximizing cumulative discounted reward. But reward is delayed (post 1's credit-assignment problem), so an agent can't just grab immediate reward — it needs to know which states and actions lead to good outcomes *eventually*. Value functions answer that, and the Bellman equation is how they're computed. This post is the hinge of the whole series.

## Value: the long-term worth of a situation

The central concept is **value** — not the immediate reward of a state, but the *total future reward you can expect from it* if you act well. A chess position with equal material might be worth little if it leads to a forced loss, and a position down a pawn might be worth a lot if it leads to a winning attack. Value captures that long-term worth, which immediate reward alone misses.

Two value functions formalize this:
- **State-value V(s)** — the expected cumulative (discounted) reward from being in state *s* and following your policy thereafter. "How good is it to be here?"
- **Action-value Q(s, a)** — the expected cumulative reward from taking action *a* in state *s* and then following your policy. "How good is it to do this, here?"

The **Q-function is the practically crucial one**, because it directly tells the agent what to do: in any state, *pick the action with the highest Q-value*. If you know Q, you have a policy for free — just act greedily with respect to it. This is why so much of RL (post 4's Q-learning) is about *estimating Q*: the Q-function converts the hard problem of "what should I do over a long horizon?" into the easy problem of "which action has the highest value right now?" Value functions are how delayed reward gets folded into a decision you can make in the present.

## The Bellman equation: value defined recursively

How do you compute value, when it depends on the entire future? The breakthrough is the **Bellman equation**, which expresses value *recursively*: the value of a state is the immediate reward plus the discounted value of wherever you land next.

```
Value(now) = immediate reward + γ × Value(next state)
```

This is the single most important equation in RL, and its beauty is that it turns an infinite look-ahead into a local, one-step relationship. You don't need to simulate the whole future to value a state — you only need the immediate reward and the value of the next state, which itself follows the same rule. Value flows *backward*: good outcomes far in the future propagate their worth, step by step, back to the states and actions that lead to them. This recursive structure is precisely what solves the credit-assignment problem (post 1) — reward earned at the end seeps backward through the Bellman relationship to credit the earlier decisions that caused it.

The Bellman equation rests entirely on the **Markov property** (post 2): because the next state's value is a sufficient summary of everything downstream, you can collapse the future into that one term. This is why the Markov assumption was load-bearing — it's what makes value computable at all.

## From Bellman to algorithms

The Bellman equation isn't just description; it's a *recipe*, and the two families of RL algorithms are two ways of using it:

- **If you know the MDP** (the transition and reward functions, post 2), you can compute the optimal value function directly with **dynamic programming** — methods like value iteration and policy iteration that repeatedly apply the Bellman equation until the values converge, then read off the optimal policy. This is **planning**: solving the MDP by computation when you have its model. It's clean but requires knowing the environment's dynamics, which you usually don't.
- **If you don't know the MDP** — the realistic case — the agent must *learn* values from experience, sampling transitions by acting in the environment and using observed rewards to update its value estimates toward the Bellman relationship. This is **reinforcement learning proper** (post 4's temporal-difference and Q-learning), and it's how an agent learns to value states without ever being told the dynamics. It approximates the dynamic-programming computation using samples instead of a known model.

This split — *planning* (known model) vs *learning* (unknown model, learn from samples) — organizes the whole field, and both rest on the same Bellman foundation. The optimal policy, in either case, comes from the optimal value function: once you know the true long-term value of every action, acting greedily with respect to it is optimal. So the entire enterprise of RL reduces to one goal — *estimate the value function well* — and the Bellman equation is the tool that makes that estimation possible, whether by computation or by experience.

The throughline: RL works by estimating **value** — the long-term expected reward of a situation, not its immediate reward — via **V(s)** ("how good to be here?") and especially **Q(s,a)** ("how good to do this here?"), because knowing Q gives a policy *for free* (act greedily on the highest Q). Value is computed through the **Bellman equation** — *value(now) = immediate reward + γ × value(next)* — which turns an infinite look-ahead into a one-step recursion, lets reward flow **backward** to solve credit assignment, and depends entirely on the **Markov property**. That recursion powers both families of algorithms: **dynamic programming / planning** when the MDP is known, and **reinforcement learning** (learning values from sampled experience) when it isn't. All of RL reduces to *estimate the value function well*, and Bellman is what makes that possible.

## Key takeaways

- **Value** is the *long-term* expected (discounted) reward from a situation, not its immediate reward — capturing that a position's worth lies in where it leads, which immediate reward misses.
- Two value functions: **V(s)** (expected return from state *s* under your policy — "how good to be here?") and **Q(s,a)** (expected return from taking action *a* in *s* — "how good to do this here?"); **Q is crucial** because acting greedily on it (pick the highest-Q action) *is* a policy — so estimating Q is most of RL.
- The **Bellman equation** defines value recursively — *value(now) = immediate reward + γ × value(next state)* — collapsing an infinite look-ahead into a one-step relationship, and letting future reward flow **backward** to credit earlier actions (solving credit assignment).
- Bellman rests on the **Markov property** (post 2): the next state's value summarizes all downstream futures, which is what makes value computable at all.
- It drives both algorithm families: **dynamic programming / planning** (compute optimal values when the MDP is *known*) and **reinforcement learning** (learn values from *sampled experience* when the MDP is unknown — the realistic case, post 4); either way, the optimal policy is "act greedily on the optimal value function," so RL reduces to *estimating value well*.

## Further reading

- [Bellman equation — value defined recursively](https://en.wikipedia.org/wiki/Bellman_equation)
- [Dynamic programming — solving known MDPs by computation](https://en.wikipedia.org/wiki/Dynamic_programming)
