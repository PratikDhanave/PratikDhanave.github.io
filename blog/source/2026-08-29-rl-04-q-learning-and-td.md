# Q-Learning and Temporal-Difference Learning — Learning Value from Experience

*The elegant idea of value functions becomes a practical algorithm through one trick: learn by comparing your prediction to a slightly-better prediction, and nudge toward the difference. Temporal-difference learning and its famous instance, Q-learning, are how an agent learns the value of its actions purely from experience — no model of the world required. This is the algorithm that first made reinforcement learning work, and its core idea quietly underlies much of the field.*

Post 3 said that when you don't know the MDP's dynamics, you must learn value from sampled experience. This post is *how*. Q-learning is the canonical answer, and understanding its update rule — learning from the gap between successive predictions — is understanding the mechanism at the heart of practical RL.

## Temporal-difference learning: the core trick

The problem: the agent acts, gets rewards, and wants to learn the value of states/actions — but it never sees the "true" long-term value of anything (that would require knowing the whole future). **Temporal-difference (TD) learning** solves this with a beautifully simple idea: *learn a guess from a better guess.*

Here's the intuition. The agent has a current estimate of a state's value. It takes a step, observes the immediate reward, and lands in a new state with its own value estimate. The Bellman equation (post 3) says these should be consistent: *value(now)* ought to equal *reward + γ × value(next)*. If they don't match, the gap — the **TD error** — is a learning signal: nudge the estimate of *value(now)* toward *reward + γ × value(next)*.

```
new estimate = old estimate + learning_rate × (reward + γ × value(next) − old estimate)
                                               └──────── TD error ────────┘
```

Two things make this powerful:
- **It learns from incomplete episodes (bootstrapping).** The agent doesn't wait until the game ends to learn — it updates after *every step*, using its own next-state estimate as a stand-in for the future. This "learning a guess from a guess" is called bootstrapping, and it's why TD learning is efficient and online.
- **It needs no model.** The agent never learns the transition or reward functions; it just uses *observed* transitions to adjust estimates. This is **model-free** learning — the realistic setting where the environment's dynamics are unknown.

TD learning is often considered RL's central idea precisely because it marries sampled experience (like trial-and-error) with the Bellman recursion (like dynamic programming), getting the best of both.

## Q-learning: learning the action-values directly

**Q-learning** applies the TD idea to the **action-value function Q(s, a)** (post 3) — and because knowing Q gives a policy for free (act greedily on the highest Q), learning Q *is* learning to act. The agent keeps estimates of Q for every state-action pair and updates them from experience:

- Take an action, observe the reward and next state.
- Compute the TD target: `reward + γ × (best Q available in the next state)`.
- Nudge Q(s, a) toward that target by the TD error.

The crucial detail: Q-learning's target uses the *best* action in the next state (the max over next-state Q-values), regardless of what the agent actually does next. This makes Q-learning **off-policy** — it learns the value of the *optimal* policy even while *behaving* more randomly to explore. That separation is powerful: the agent can explore freely (try suboptimal actions to discover the environment) while still learning the optimal strategy. Over enough experience, the Q-estimates converge to the true optimal action-values, and acting greedily on them is optimal.

Exploration is handled explicitly, usually with **ε-greedy**: most of the time take the current best action (exploit), but with small probability ε take a random action (explore) — the direct, practical resolution of post 1's exploration-exploitation dilemma. Early on ε is high (explore a lot); over time it decays (increasingly exploit what's been learned).

## What Q-learning can and can't do

Classic Q-learning, as described, stores Q as a **table** — one entry per state-action pair — and this reveals both its elegance and its fatal limitation:

- **It works beautifully on small, discrete problems.** A grid world, a simple game, anything with a manageable number of states — the table fills in, converges, and you get an optimal policy from pure experience with no model. It's the clearest demonstration that an agent can learn optimal behavior from reward alone.
- **It collapses on large or continuous state spaces.** A table needs an entry per state, but real problems have astronomically many states (every possible screen of a video game, every configuration of a robot) or *continuous* states (any real-valued sensor reading) — far too many to enumerate, let alone visit. The table approach simply can't scale, and most states would never be seen even once.

This limitation is exactly what motivates the next leap: instead of a table, use a **function approximator** — a neural network — to *generalize* Q-values across similar states, so the agent can handle states it has never seen by interpolating from ones it has. That's **deep reinforcement learning** (post 5), and it's what took RL from grid worlds to mastering Atari and Go. Q-learning gives you the learning rule; replacing its table with a neural network gives you the scale. The TD error at the center stays exactly the same — only the representation of Q changes.

The throughline: **temporal-difference learning** makes value functions practical by *learning a guess from a better guess* — after each step, nudge the value estimate toward *reward + γ × value(next)* by the **TD error** — which **bootstraps** (learns from incomplete episodes, updating every step) and is **model-free** (uses observed transitions, never learning the dynamics). **Q-learning** applies this to the action-value **Q(s,a)**, so learning Q *is* learning to act (greedy on Q = policy); its max-over-next-actions target makes it **off-policy** (learns the optimal policy while exploring freely), with exploration handled by **ε-greedy**. Tabular Q-learning solves small discrete problems perfectly but **can't scale** to large/continuous state spaces — which motivates replacing the Q-table with a **neural network** (deep RL, post 5), keeping the TD update identical while gaining generalization.

## Key takeaways

- **Temporal-difference (TD) learning** learns value from experience by nudging each estimate toward *reward + γ × value(next)* — the **TD error** — "learning a guess from a better guess."
- TD **bootstraps** (updates after every step using its own next-state estimate, so it learns from incomplete episodes) and is **model-free** (uses observed transitions, never learning the environment's dynamics) — marrying sampled experience with the Bellman recursion.
- **Q-learning** applies TD to the action-value **Q(s,a)**; since acting greedily on Q is a policy, learning Q *is* learning to act — and its target uses the *best* next action, making it **off-policy** (learns the optimal policy while behaving exploratorily).
- Exploration is handled by **ε-greedy** (mostly exploit the best action, occasionally act randomly; ε decays over time) — the practical resolution of the exploration–exploitation dilemma.
- **Tabular** Q-learning converges beautifully on small discrete problems but **can't scale** to large/continuous state spaces (too many states to enumerate/visit) — motivating a **neural-network function approximator** for Q (deep RL, post 5), which keeps the same TD update but generalizes across states.

## Further reading

- [Q-learning — model-free off-policy value learning](https://en.wikipedia.org/wiki/Q-learning)
- [Temporal difference learning — learning a guess from a better guess](https://en.wikipedia.org/wiki/Temporal_difference_learning)
