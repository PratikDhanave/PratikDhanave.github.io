# Models, Prompts, and Output Parsers

*Every LangChain application, no matter how elaborate, is built from three humble pieces: a model you call, a prompt you send it, and a parser that turns its reply into something usable. Master these three and the rest of LangChain is just composing them — which is exactly what the framework is designed to let you do.*

The last post framed LangChain as a standardizing toolkit. This post covers its three most basic building blocks — **models**, **prompts**, and **output parsers** — the atoms that everything else composes from. They map to the fundamental shape of any LLM interaction: format an input (prompt), send it to a model (model), and make sense of the output (parser). Understanding these as standard, swappable components is the foundation for the composition model (LCEL) that follows.

## Models: the standard interface to LLMs

The **model** is the LLM you call, and LangChain's key contribution here is the *standard interface* from the last post. LangChain distinguishes two kinds, reflecting how models actually work today:

- **Chat models** — the modern default: models that take a list of **messages** (system, human, AI) and return a message. Almost all current LLMs are chat models, and this is the interface you'll use.
- **LLMs (text completion)** — the older interface taking a string and returning a string; largely superseded by chat models.

The standardization is the point: LangChain's chat-model interface is the *same* whether the underlying provider is OpenAI, Anthropic, Google, or a local model. You instantiate a different model object, but your code — sending messages, getting a response — is identical. This is what makes LangChain applications model-agnostic (the keep-the-model-swappable principle): the model is a pluggable component behind a common interface, so swapping providers is changing one line, not rewriting your app. Chat models also expose common capabilities through this interface — streaming, tool/function calling, structured output — so those features work uniformly across providers too.

## Prompts: templating the input

You rarely send a fixed string to a model; you send a *template* filled with variables (the user's question, retrieved context, examples). LangChain's **prompt templates** handle this — reusable prompts with placeholders you fill at run time:

```python
# Illustrative shape — see the LangChain docs for exact API.
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that answers about {topic}."),
    ("human", "{question}"),
])
messages = prompt.invoke({"topic": "databases", "question": "What is an index?"})
```

Prompt templates matter for a few reasons beyond convenience:

- **Reusability and consistency** — define a prompt once and fill it many times, keeping prompting consistent rather than scattering ad-hoc strings through your code.
- **Message-aware** — chat prompt templates build the *message list* chat models expect (system + human + history), not just a string.
- **Composable** — templates are components that plug into chains (the LCEL post), so prompt construction becomes part of a pipeline rather than manual string-building.

Prompt templates are where prompt engineering meets software structure: your prompts become named, reusable, parameterized components instead of inline strings — which is both cleaner and what lets prompts participate in composition.

## Output parsers: making the reply usable

A model returns a message, but your application usually needs *structured data* — a list, a number, a typed object. **Output parsers** turn the model's raw text output into a usable form:

- **Simple parsers** — extract a string, or parse a list or other basic structure from the output.
- **Structured/typed parsers** — parse the output into a structured object (often defined with a schema, and increasingly using models' native structured-output capabilities), so you get typed data rather than text to handle by hand.

This is the same problem the [Pydantic AI structured-outputs](/blog/posts/pydai-03-structured-outputs.html) post tackled — the gap between "the model returned text" and "I have usable data" — and LangChain addresses it with parsers (and, for models that support it, native structured output through the standard interface). The modern approach leans on models' built-in structured-output/tool-calling to get reliable typed results, with parsers handling the transformation. The point to hold: the output parser is the third atom, closing the loop from text back to data, so the model's reply flows into the rest of your typed program rather than being a string you wrangle.

## The three together: the anatomy of an LLM call

Models, prompts, and parsers compose into the fundamental unit of a LangChain application:

```text
input variables → PROMPT (template)  → messages
                → MODEL (chat model)  → response message
                → OUTPUT PARSER       → usable structured data
```

This prompt → model → parser flow *is* the basic LLM interaction, and it's the simplest **chain** (the LCEL post makes composing them explicit):

```python
# Illustrative shape.
chain = prompt | model | parser        # LangChain's composition (LCEL)
result = chain.invoke({"topic": "databases", "question": "What is an index?"})
```

That `prompt | model | parser` pipeline captures the essence of LangChain: three standard, swappable components piped together into a reusable chain. Everything more complex — retrieval, tools, agents — builds on this foundation by adding components to the pipeline. Understanding these three atoms, and that they're *composable standard components*, is what makes the rest of LangChain legible: it's all variations on formatting input, calling a model, and parsing output, wired together.

## Using the atoms well

- **Rely on the standard model interface** — instantiate the model as a swappable component, keeping your app model-agnostic; don't hard-code provider-specific calls when the standard interface does the job.
- **Use prompt templates, not inline strings** — make prompts named, reusable, parameterized components; it's cleaner and enables composition.
- **Parse to structured data** — use output parsers or native structured output to get typed results, so the model's output flows into typed code rather than being handled as raw text.
- **Think in prompt → model → parser** — see every LLM interaction as this composable trio, which is the mental model the rest of LangChain builds on.

These three atoms — model, prompt, parser — are the foundation. The next post covers the mechanism that composes them (and everything else) into applications: LCEL and Runnables.

## Key takeaways

- The model is the LLM behind LangChain's standard interface (chat models taking/returning messages are the modern default), which makes applications model-agnostic — swap providers by changing the model object, not your code — and exposes streaming, tool calling, and structured output uniformly.
- Prompt templates turn prompting into reusable, parameterized, message-aware components you fill at run time, replacing scattered inline strings and letting prompt construction participate in composition.
- Output parsers turn the model's raw text into usable structured data (simple or typed/schema-based, increasingly via native structured output), closing the loop from text back to data — the same gap Pydantic AI's structured outputs address.
- The three compose into the fundamental unit — prompt → model → parser — which is the simplest chain (`prompt | model | parser` in LCEL), and everything more complex builds by adding components to this pipeline.
- Use them well: rely on the standard model interface for swappability, use prompt templates over inline strings, parse to structured data, and think in the prompt→model→parser trio that underlies all of LangChain.

## Further reading

- [What is LangChain? (previous post)](/blog/posts/lc-01-what-is-langchain.html)
- [LangChain documentation — chat models and prompts](https://python.langchain.com/)
- [Pydantic AI: structured outputs — the typed-output problem](/blog/posts/pydai-03-structured-outputs.html)
