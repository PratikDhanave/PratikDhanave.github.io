# Deployment & A2A: From ADK's Web Deploy to MAF's Scalable Architecture

*Running agents on Cloud Run, exposing via A2A, and wiring into production systems.*

---

## Pattern 1: Cloud Run (Stateless)

Both ADK and MAF can run on Cloud Run. The main difference: MAF is explicit about state.

**ADK**:
```python
from flask import Flask, request, jsonify
from google.adk import Agent

app = Flask(__name__)
agent = Agent(model="gemini-2.5-flash", instructions="...")  # Singleton

@app.route("/ask", methods=["POST"])
def ask():
    prompt = request.json["prompt"]
    result = await agent.run(prompt)  # Shares state across requests (problematic)
    return jsonify({"answer": result.message.content})
```

Problem: The agent is stateless, but if you use callbacks or session state, it's confusing.

**MAF**:
```python
from fastapi import FastAPI
from multi_agent.providers import build_chat_client
from agent_framework import Agent, AgentThread

app = FastAPI()
client = build_chat_client()  # Client is lightweight; reusable

@app.post("/ask")
async def ask(request: dict):
    prompt = request["prompt"]
    
    # Each request gets a fresh thread (conversation state)
    thread = AgentThread()
    
    agent = Agent(client=client, instructions="...")
    result = await agent.run(prompt, thread=thread)
    
    return {"answer": result.message.content}
```

**Clear**: Client is reused. Thread (state) is per-request. No confusion.

Deploy to Cloud Run:
```bash
gcloud run deploy my-agent \
    --source . \
    --port 8000 \
    --env PROVIDER=foundry \
    --env FOUNDRY_PROJECT_ENDPOINT=... \
    --env FOUNDRY_MODEL=gpt-4o-mini
```

## Pattern 2: A2A (Agent-to-Agent Communication)

If your agent needs to call another agent (e.g., a backend agent calls a specialist agent), use A2A:

**ADK**:
```python
# Supervisor runs locally; calls specialists over HTTP
specialist = RemoteAgent(url="https://specialist-agent.run.app")
result = await specialist.ask("Analyze this")
```

No framework support. You roll your own HTTP wrapping.

**MAF**:
```python
from agent_framework_a2a import A2AAgent

# Expose the specialist agent
specialist = Agent(client=..., instructions="...")
a2a = A2AExecutor(specialist, port=8080)
await a2a.start()  # Listens on localhost:8080

# Supervisor (remote) calls the specialist
supervisor_specialist = A2AAgent(url="http://localhost:8080")

supervisor = Agent(
    client=...,
    instructions="...",
    tools=[
        tool(
            async def ask_specialist(q: str) -> str:
                return await supervisor_specialist.run(q)
        )
    ]
)

result = await supervisor.run("Delegate to specialist")
```

## Pattern 3: Load Balancing Multiple Agents

You have one agent model but many requests. Deploy N replicas:

```bash
# Deploy 3 copies of the same agent
for i in {1..3}; do
    gcloud run deploy my-agent-$i \
        --source . \
        --port 8000 \
        --memory 512Mi \
        --env PROVIDER=foundry
done

# Load balancer distributes requests across replicas
# Each replica: stateless client + per-request thread
```

MAF's per-request thread model makes this trivial. ADK's session state would cause issues (which replica owns the session?).

## Pattern 4: Observability in Production

Wire your deployed agents to observability backends:

```python
import logging
from multi_agent.observability import setup_observability

# Setup OpenTelemetry + auto-wire to Laminar (if LMNR_PROJECT_API_KEY is set)
setup_observability(service_name="genie-supervisor")

# Now every agent.run() emits a trace
agent = Agent(client=..., instructions="...")

# Traces go to:
# - Local Jaeger (if running)
# - Laminar (if LMNR_PROJECT_API_KEY is set)
# - Both (for dual redundancy)
```

Deploy:
```bash
gcloud run deploy my-agent \
    --source . \
    --env LMNR_PROJECT_API_KEY=... \
    --env LMNR_BASE_URL=https://api.lmnr.ai
```

Every request is traced. Latency, errors, token usage — all visible in Laminar's dashboard.

## Pattern 5: Graceful Shutdown

When you deploy a new version, in-flight requests should finish, not be killed:

```python
import signal
from contextlib import asynccontextmanager

# Track in-flight requests
in_flight = 0
shutdown_event = asyncio.Event()

@app.post("/ask")
async def ask(request: dict):
    global in_flight
    in_flight += 1
    
    try:
        prompt = request["prompt"]
        thread = AgentThread()
        agent = Agent(client=..., instructions="...")
        result = await agent.run(prompt, thread=thread)
        return {"answer": result.message.content}
    finally:
        in_flight -= 1
        if in_flight == 0:
            shutdown_event.set()

async def shutdown():
    print("Shutdown signal received; waiting for in-flight requests...")
    await shutdown_event.wait()
    print("All requests completed; exiting")

signal.signal(signal.SIGTERM, lambda *a: asyncio.create_task(shutdown()))
```

Deploy on Cloud Run — it sends SIGTERM before killing the container. Your agents finish gracefully.

## Real Example: Genie in Production

**Architecture**:
- 3x Genie supervisor replicas on Cloud Run
- Each replica: stateless client + per-request thread
- Specialist agents (analyzer, forecaster, etc.) deployed separately
- All agents expose A2A endpoints
- Load balancer distributes /ask requests
- Every call emitted to Laminar for tracing
- Graceful shutdown handles rolling deploys

**Deployment**:
```bash
# Build
docker build -t genie:latest .

# Deploy
for i in {1..3}; do
    gcloud run deploy genie-supervisor-$i \
        --image genie:latest \
        --memory 512Mi \
        --timeout 60 \
        --env PROVIDER=foundry \
        --env LMNR_PROJECT_API_KEY=...
done

# Route traffic
gcloud compute backend-services create genie-backend
for i in {1..3}; do
    gcloud compute backend-services add-backend genie-backend \
        --instance-group genie-supervisor-$i
done
```

Result: Scalable, observable, resilient multi-agent system.

---

Next: [Lessons Learned (18 Agents, 90 Days)](/blog/2026/06/08/adk-to-maf-lessons.html)
