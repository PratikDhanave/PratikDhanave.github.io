# Policy Gradients and Actor-Critic — Learning the Policy Directly

*Value-based methods like Q-learning learn how good each action is, then act greedily. There's a different and often better approach: skip the value estimates and learn the policy itself, directly adjusting the probability of actions to get more reward. Policy gradient methods are how RL handles continuous control and stochastic strategies — and the actor-critic architecture that combines them with value learning is the foundation of the algorithms used to fine-tune today's language models.*

Posts 4–5 were value-based: learn Q, act greedily. This post covers the other great family — policy-based methods — and their fusion with value methods in actor-critic. This matters beyond theory: the algorithms that do RLHF (post 7), like PPO, are actor-critic policy-gradient methods, so this is the direct conceptual bridge from classic RL to LLM alignment.

## Why learn the policy directly

Value-based methods have a structural awkwardness: they learn values, then *derive* a policy by picking the highest-value action. That works when actions are a small discrete set (pick the max), but it breaks down in important cases:

- **Continuous action spaces.** A robot arm's action is a set of real-valued joint torques — infinitely many options, so you can't "take the max over actions" the way Q-learning does. Value-based methods struggle here; you'd need to optimize over a continuous action every step.
- **Stochastic optimal policies.** Sometimes the best strategy is genuinely *randomized* (bluffing in poker, or any situation where being predictable is exploitable). A greedy value-based policy is deterministic and can't represent "take action A 70% of the time"; a policy that outputs *probabilities* can.
- **Awkward value landscapes.** Sometimes the policy is simpler to represent than the value function — directly learning "do this" is easier than learning the exact value of everything.

**Policy gradient methods** address all three by learning the **policy directly**: a neural network takes a state and outputs *probabilities over actions* (or parameters of a continuous action distribution), and training adjusts those probabilities to earn more reward. No value table, no greedy max — the policy is the thing you learn and the thing you use.

## How policy gradients work

The mechanism is intuitive, and it's essentially trial-and-error with a gradient. The agent acts according to its current (stochastic) policy, collects the rewards, and then adjusts the policy by the principle:

> Increase the probability of actions that led to good outcomes; decrease the probability of actions that led to bad ones.

Concretely, you compute a **gradient** that points in the direction of higher expected reward — raising the likelihood of action sequences that earned high return, lowering those that earned low return — and take a gradient-ascent step (the mirror of the gradient *descent* from the ML series). The classic version, REINFORCE, does exactly this using the total return of each episode.

This directness is the strength, but it has a well-known weakness: **high variance**. Because it learns from the noisy total reward of whole episodes, the signal is noisy — a good action in an episode that happened to end badly gets unfairly penalized, and vice versa. Pure policy gradients therefore learn slowly and unstably, needing many episodes to average out the noise. Fixing that variance problem is what leads to actor-critic.

## Actor-critic: the best of both families

The key innovation is to combine policy-based and value-based learning into the **actor-critic** architecture, which is the workhorse of modern RL:

- **The actor** is the policy — it chooses actions (the policy-gradient part).
- **The critic** is a value function — it estimates how good states/actions are (the value-based part, learned by TD methods from post 4).
- The critic's estimate is used to *judge* the actor's actions, replacing the noisy whole-episode return with a lower-variance, step-by-step assessment. Instead of "this action was followed by a good episode," the critic says "this action was *better than expected* from this state" — a cleaner signal that cuts the variance dramatically.

This fusion gets the best of both: the actor handles continuous and stochastic policies (policy gradients' strength), while the critic provides the stable, low-variance learning signal (value methods' strength). Actor-critic methods converge faster and more reliably than pure policy gradients, and they underpin the most widely used modern RL algorithms. The most important of these is **Proximal Policy Optimization (PPO)** — an actor-critic policy-gradient method that adds a crucial stabilizer: it limits how much the policy can change in a single update ("proximal" = stay close to the previous policy), preventing the catastrophic, unrecoverable policy collapses that plagued earlier methods. PPO's reliability made it the default RL algorithm for many applications — and, decisively, the algorithm behind **RLHF** (post 7). The direct line from this post to LLM alignment runs through PPO: the actor is the language model, the critic estimates value, and the "reward" comes from human preferences.

The throughline: **policy gradient** methods learn the **policy directly** — a network outputs action *probabilities*, and training raises the probability of actions that earned reward and lowers those that didn't (gradient *ascent*) — solving what value methods can't: **continuous action spaces**, **stochastic optimal policies**, and cases where the policy is simpler than the value function. Their weakness is **high variance** (noisy whole-episode signal), fixed by the **actor-critic** architecture: the **actor** (policy) chooses actions while the **critic** (value function, learned by TD) provides a low-variance "better than expected" signal to judge them — the best of both families. The dominant such method, **PPO**, adds update-size limits for stability and is the algorithm behind **RLHF**, making this post the direct bridge from classic RL to LLM alignment.

## Key takeaways

- **Policy gradient** methods learn the **policy directly** — a network outputs action *probabilities* and training adjusts them (gradient *ascent*): raise the probability of actions that led to good outcomes, lower the bad ones — no value table, no greedy max.
- They solve what value-based methods can't: **continuous action spaces** (can't take a max over infinitely many actions), **stochastic optimal policies** (randomized strategies, e.g. bluffing), and problems where the policy is simpler to represent than the value function.
- Their weakness is **high variance** (learning from the noisy total return of whole episodes → slow, unstable) — the problem actor-critic fixes.
- **Actor-critic** combines both families: the **actor** (policy) acts, the **critic** (value function, learned via TD, post 4) judges actions with a low-variance "better-than-expected" signal — getting policy gradients' flexibility *and* value methods' stability; it's the workhorse of modern RL.
- **PPO** (Proximal Policy Optimization) is the dominant actor-critic method, adding a limit on per-update policy change for stability — the default RL algorithm for many uses and the algorithm behind **RLHF** (post 7), where the actor is the LLM and reward comes from human preferences — the direct bridge to LLM alignment.

## Further reading

- [Reinforcement learning — value-based vs policy-based methods](https://en.wikipedia.org/wiki/Reinforcement_learning)
- [Proximal policy optimization — the dominant actor-critic method](https://en.wikipedia.org/wiki/Proximal_policy_optimization)
