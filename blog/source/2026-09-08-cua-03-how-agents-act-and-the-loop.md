# How Computer-Use Agents Act — and the Perceive-Act Loop

*Having understood the screen, a computer-use agent must act on it — move the cursor, click the right spot, type the right text — and then look again to see what happened. This perceive-act loop, running over a graphical interface with imprecise actions and visual feedback, is the engine of a computer-use agent, and it's both simple in shape and hard in execution. This post covers how agents act on a GUI and the loop that ties perception and action together.*

Post 2 covered perceiving the screen; this post covers acting on it and the loop that connects them. It's the computer-use specialization of the general agent loop (the [coding agents](/blog/series/coding-agents/) series' loop), with the distinctive twist that both the actions and the feedback go through the human interface, which makes the loop harder to run reliably.

## How agents act on a GUI

A computer-use agent acts by *simulating human input* — the same actions a person makes at a computer:

- **Mouse actions** — move the cursor to a location and click (left/right/double), drag, scroll. Clicking is the primary action, and it requires a *precise target location* (where on screen to click — the grounding problem, post 5).
- **Keyboard actions** — type text into fields, press keys and shortcuts (Enter, Tab, Ctrl+C), enter data. Typing is how the agent inputs information.
- **Navigation** — open applications, switch windows/tabs, scroll to reveal content, navigate menus — moving around the interface to reach what it needs.

The key characteristic: these are *low-level, human-style* actions (click *here*, type *this*), not high-level semantic operations (an API's "submit the form"). The agent must translate its intent ("submit the form") into the concrete physical actions ("click the button at coordinates X,Y") — and do so *precisely*, because acting on the wrong location (a mis-click) does the wrong thing. This translation from intent to precise physical action, through an imprecise visual interface, is where acting is hard: the agent knows *what* it wants to do but must correctly execute *where and how* on a pixel surface. Unlike an API call that either works or returns a clear error, a GUI action can "succeed" mechanically (a click landed) while doing the wrong thing (it hit the wrong element) — a failure mode the agent must catch by looking at the result.

## The perceive-act loop on a GUI

Computer-use agents run the general agent loop (perceive → decide → act → perceive, the [coding agents](/blog/series/coding-agents/) loop) specialized for the screen:

1. **Perceive** — take a screenshot and understand the current screen (post 2): what's shown, what state, what's possible.
2. **Decide** — reason about the next action given the goal and the current screen: "to submit, I click the Submit button."
3. **Act** — execute the physical action: move to the button's location and click (or type, or navigate).
4. **Perceive again** — take a *new* screenshot and see what happened: did the form submit? did a confirmation appear? did an error show? did nothing change (the click missed)?
5. **Repeat** — use the new observation to decide the next action, looping until the task is done or the agent is stuck.

This is the familiar agent loop, but with two distinctive, harder properties:
- **Both action and feedback go through the human interface.** The agent acts via simulated input and observes via screenshots (post 2) — so each loop iteration involves *interpreting an image, acting imprecisely, and interpreting another image*. There's no clean structured action result (unlike an API or the coding agent's test output) — the agent must *look to see if its action worked*, which is itself a perception problem. The loop is visual on both ends.
- **It's slow and every step can fail.** Screenshot → reason → act → screenshot is slower than an API call, and tasks need many iterations, with each step carrying perception risk (misread screen) and action risk (mis-click). Many steps × per-step failure probability makes long tasks error-prone (the reliability challenge, post 6). The loop's length and per-step fragility compound.

The critical element, as in all agent loops, is *closing the loop* — the agent must **observe the result of each action and adapt**, which for a GUI means *looking at the new screen to see what its action did* and correcting if it went wrong (the click missed, an unexpected dialog appeared). This visual feedback loop is what lets a computer-use agent recover from imprecise actions (re-click if the first missed, dismiss an unexpected popup) rather than blindly executing a plan — and it's essential, because actions on a GUI are inherently less certain than API calls, so the agent *must* verify each one visually and adapt.

## Why the loop is the engine — and where it strains

The perceive-act loop frames how computer-use agents work and where they struggle:

- **The loop enables adaptation, which is essential given imprecise actions.** Because GUI actions are uncertain (a click may miss, a page may load slowly, a dialog may appear), the agent *cannot* just execute a fixed sequence — it must observe and adapt each step (re-try, wait for loading, handle the unexpected). The loop's observe-and-adapt is what makes computer use *robust* rather than brittle-scripted, and it's the key advantage over classic coordinate-scripted RPA (post 1) — the agent *reacts to what actually happened* instead of assuming. This adaptation is the whole point of an *intelligent* computer-use agent.
- **It strains on long tasks (error accumulation).** Each loop step has a chance of a perception or action error, so over many steps, errors accumulate — a long GUI task (many clicks and screens) is more likely to go wrong somewhere, and a single wrong step can derail the rest. This is the central reliability challenge (post 6): computer-use agents are more reliable on short tasks and shakier on long ones, precisely because of per-step error compounding over a long loop.
- **It needs good perception and grounding.** The loop is only as good as its "perceive" (post 2 — understand the screen) and its action targeting ("decide where to click" — grounding, post 5). Weakness in either produces wrong actions the loop then has to recover from. The loop *amplifies* good perception/grounding and *suffers* from bad.
- **Stuck states and verification.** The agent can get stuck (can't find an element, an action keeps failing, an unexpected state it can't handle) or "finish" wrongly, so bounding the loop, detecting stuck states, verifying success (post 6), and escalating to a human (post 7) matter — just as for other agents, but more so given the loop's fragility.

The through-line: a computer-use agent **acts** by simulating human input — **mouse** (click, needing a precise target — the grounding problem), **keyboard** (type, press keys), **navigation** — translating high-level intent ("submit the form") into precise low-level physical actions ("click at X,Y") through an imprecise visual surface, where an action can mechanically succeed yet do the wrong thing. It runs the general **perceive-act loop** specialized for the screen (screenshot → decide → act → screenshot → repeat), with two hard twists: **both action and feedback go through the human interface** (visual on both ends — the agent must *look* to verify its action worked, itself a perception problem) and it's **slow with per-step failure risk** (perception + action errors accumulate over many steps). **Closing the loop** — observing each action's visual result and adapting (re-click, wait, handle the unexpected) — is essential given GUI actions' uncertainty and is the key advantage over brittle coordinate-scripted RPA; it strains on **long tasks** (error compounding) and depends on good perception (post 2) and grounding (post 5).

## Key takeaways

- A computer-use agent **acts** by **simulating human input**: **mouse** (move + click — the primary action, needing a *precise target location*), **keyboard** (type text, press keys/shortcuts), and **navigation** (open apps, switch windows/tabs, scroll, menus) — **low-level physical** actions, not high-level semantic API operations.
- The hard part is **translating intent to precise physical action** through an imprecise visual surface ("submit the form" → "click at X,Y") — and unlike an API call, a GUI action can **mechanically succeed yet do the wrong thing** (a click that lands on the wrong element), which the agent must catch by looking at the result.
- Computer-use agents run the general **perceive-act loop** specialized for the screen: **screenshot → decide the action → act → new screenshot → repeat**, until done or stuck — with two hard twists: **both action and feedback go through the human interface** (visual on both ends — verifying an action is itself a perception problem, with no clean structured result) and it's **slow with per-step failure risk**.
- **Closing the loop** — observing each action's visual result and **adapting** (re-click if it missed, wait for loading, dismiss an unexpected dialog) — is essential because GUI actions are *uncertain*, and it's the key advantage over classic **coordinate-scripted RPA** (the agent *reacts to what actually happened* rather than blindly executing a fixed sequence) — the point of an *intelligent* computer-use agent.
- The loop **strains on long tasks** (per-step perception/action errors **accumulate** — the central reliability challenge, post 6, so agents are more reliable on short tasks), **depends on good perception** (post 2) **and grounding** (post 5 — the loop amplifies both), and needs **stuck-detection, success verification, and human escalation** (posts 6–7) given its fragility.

## Further reading

- [Software agent — the perceive-act loop specialized for the screen](https://en.wikipedia.org/wiki/Software_agent)
- [Test automation — the GUI-driving techniques computer-use agents build on](https://en.wikipedia.org/wiki/Test_automation)
