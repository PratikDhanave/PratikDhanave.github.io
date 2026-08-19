# Structuring System Prompts and Instructions

*The system prompt is the one piece of context present on every single call, so how you structure its role, rules, and format is the highest-leverage writing in the whole system.*

Of everything in the context window, the system prompt is unique: it is durable. Retrieved documents change per query, history grows per turn, but the system prompt is there on every call, shaping every response. That makes it the highest-leverage piece of context you write — and the one most worth structuring deliberately rather than accreting by trial and error. This third post in the context engineering series is about composing system prompts and instructions that steer a model reliably.

## What the system prompt is for

The system prompt establishes the durable frame the model operates within: who it is, what it should do, what rules it must follow, and how its output should look. It is not the place for the specific request (that is the user turn) or for task data (that is retrieved context) — it is the place for the *stable policy* that governs how the model handles whatever comes. A good test: if a piece of guidance should apply to every request, it belongs in the system prompt; if it is specific to this one request, it does not.

Because it is always present, the system prompt also spends a fixed slice of your token budget on every call. That is a reason to make it tight — earn every line — but not a reason to starve it. Clear, complete guidance that prevents a class of errors pays for its tokens many times over.

## The anatomy of a good system prompt

Most effective system prompts, whatever the domain, cover the same elements. Ordering them explicitly beats letting them blur together:

- **Role and objective.** A concise statement of what the model is and what it is trying to accomplish ("You are a support assistant for X; your goal is to resolve billing questions accurately"). This anchors everything else.
- **Instructions.** The concrete behaviors you want, stated positively and specifically. "Ask a clarifying question when the account is ambiguous" beats "be helpful."
- **Constraints and rules.** The boundaries — what the model must not do, what it must always do, safety and policy limits. Be explicit; models follow stated rules far better than implied ones.
- **Tools guidance.** When and how to use available tools, if the model has them — which to prefer, when to ask before acting.
- **Output format.** The exact shape you expect: prose vs JSON, required fields, length, tone. If you need machine-parseable output, specify the format precisely and show it.
- **Examples.** A small number of high-quality examples of the behavior you want, when the task is subtle enough that showing beats telling.

Not every prompt needs every section, but running through the list surfaces what you have left implicit — and implicit expectations are where models "misbehave."

## Be specific, positive, and concrete

Three habits do most of the work. **Be specific:** vague instructions get vague compliance. "Summarize in three bullet points, each under fifteen words, focusing on action items" is followed far more reliably than "summarize concisely." **Be positive:** tell the model what to do, not only what to avoid; a wall of "don't" leaves the desired behavior undefined. **Be concrete about format:** if downstream code parses the output, do not describe the format in prose and hope — specify it exactly, and give an example of a valid response. Ambiguity in the system prompt becomes variance in the output, and variance is what breaks pipelines.

## Ordering and structure within the prompt

Structure is not just cleanliness; it affects how reliably the model follows the prompt. A few principles:

- **Lead with role and the most important instructions.** Given how models weight the start of the context, put the anchoring identity and the rules you care most about near the top.
- **Use clear delimiters.** Sections marked with headings or consistent delimiters help the model (and you) tell instructions from data from examples. This also reduces the risk of the model confusing task content with instructions.
- **Group related guidance.** Keep constraints together, format rules together; scattered rules are easy for the model to partially miss.
- **Separate instructions from data.** Never blur the durable policy with the specific input — a structural boundary between "here are your rules" and "here is the request" reduces both model confusion and prompt-injection risk.

## System versus user: drawing the line

A recurring question is what goes in the system prompt versus the user turn. The clean rule: the system prompt holds what is *true across all requests* (identity, rules, format), and the user turn holds *this request* (the specific question and its immediate data). Putting per-request data in the system prompt bloats a slice you pay for on every call and muddies the durable policy; putting durable rules in the user turn means restating them every time and risks them drifting. Keep the stable in system, the variable in user, and the model's behavior stays consistent while the requests vary.

## Iterate against evaluation, not vibes

Finally, treat the system prompt as something you *measure*, not something you tweak by feel. A change that seems better on one example can regress on others. Keep a small set of representative cases, and when you change the prompt, check that the change helps across them rather than just on the case that annoyed you. The system prompt is durable precisely because it is worth getting right — and "right" is defined by behavior on real cases, not by how the wording reads.

## Key takeaways

- The system prompt is the one piece of context present on every call, making it the highest-leverage writing in the system — reserve it for durable policy, not per-request data.
- Cover role/objective, instructions, constraints, tools guidance, output format, and (when useful) examples; running the checklist surfaces what you left implicit.
- Be specific, state behaviors positively, and specify machine-parseable formats exactly with an example — ambiguity in the prompt becomes variance in the output.
- Structure matters: lead with role and key rules, use clear delimiters, group related guidance, and separate instructions from data (which also reduces injection risk).
- Keep what is true across all requests in the system prompt and this-request specifics in the user turn, and iterate the prompt against a set of real cases rather than by feel.

## Further reading

- [OpenAI Cookbook](https://github.com/openai/openai-cookbook)
- [Anthropic documentation](https://docs.anthropic.com)
- [Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023](https://arxiv.org/abs/2307.03172)
