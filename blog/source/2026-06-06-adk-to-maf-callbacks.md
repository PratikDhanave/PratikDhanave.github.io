# Callbacks and Middleware: Porting ADK Hooks to MAF's Decorator Pattern

*How to instrument agents for observability, error handling, and audit logging.*

---

## The Shift: Named Callbacks → Middleware

**ADK** uses explicit callback hooks:
```python
def before_agent_runs(context):
    print(f"Agent {context.agent_name} is about to run")
    context.state["start_time"] = time.time()

def after_agent_runs(context):
    elapsed = time.time() - context.state["start_time"]
    print(f"Agent {context.agent_name} took {elapsed}s")

agent = Agent(
    ...,
    before_callback=before_agent_runs,
    after_callback=after_agent_runs
)
```

Callbacks are explicit parameters. They're interceptors.

**MAF** uses middleware (decorators/wrappers):
```python
def log_agent_execution(agent_func):
    async def wrapper(*args, **kwargs):
        print(f"Running {agent_func.__name__}")
        start = time.time()
        result = await agent_func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"Completed in {elapsed}s")
        return result
    return wrapper

# Apply it
from functools import wraps

@log_agent_execution
async def run_agent(agent, prompt, **kwargs):
    return await agent.run(prompt, **kwargs)
```

Middleware wraps the function. It's composable and pythonic.

## Pattern 1: Audit Logging

Track every agent call for compliance:

```python
import logging
from datetime import datetime

logger = logging.getLogger("audit")

def audit_logging(func):
    async def wrapper(agent, prompt, **kwargs):
        # Log the start
        logger.info(f"Agent {agent.name} starting", extra={
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": kwargs.get("user_id"),
            "prompt_length": len(prompt),
        })
        
        # Run the agent
        result = await func(agent, prompt, **kwargs)
        
        # Log the result
        logger.info(f"Agent {agent.name} completed", extra={
            "timestamp": datetime.utcnow().isoformat(),
            "output_length": len(result.message.content),
            "tokens_used": result.message.token_count,
        })
        
        return result
    return wrapper
```

Use it:
```python
@audit_logging
async def run_agent(agent, prompt, **kwargs):
    return await agent.run(prompt, **kwargs)

result = await run_agent(analyzer, "Analyze this", user_id="user123")
# Logs: "Agent Analyzer starting... Agent Analyzer completed..."
```

## Pattern 2: Error Recovery

ADK callbacks couldn't really recover (they were observers). MAF middleware can:

```python
async def with_retry(func):
    """Retry up to 3 times on API errors."""
    async def wrapper(agent, prompt, **kwargs):
        for attempt in range(3):
            try:
                return await func(agent, prompt, **kwargs)
            except (TimeoutError, ConnectionError) as e:
                if attempt < 2:
                    print(f"Attempt {attempt+1} failed; retrying...")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"All 3 attempts failed; giving up")
                    raise
    return wrapper

@with_retry
async def run_agent(agent, prompt, **kwargs):
    return await agent.run(prompt, **kwargs)
```

## Pattern 3: Token Budgeting

Enforce a maximum token spend per request:

```python
async def enforce_token_budget(func):
    """Ensure we don't exceed a token budget."""
    async def wrapper(agent, prompt, max_tokens=10000, **kwargs):
        kwargs["max_tokens"] = max_tokens
        result = await func(agent, prompt, **kwargs)
        
        if result.message.token_count > max_tokens * 0.9:
            logging.warning(f"Agent {agent.name} used {result.message.token_count} tokens (budget: {max_tokens})")
        
        return result
    return wrapper

@enforce_token_budget
async def run_agent(agent, prompt, **kwargs):
    return await agent.run(prompt, **kwargs)

result = await run_agent(analyzer, prompt, max_tokens=5000)
# Warns if analyzer uses > 4500 tokens
```

## Pattern 4: Observability Integration

Wire into OpenTelemetry (traces, metrics, logs):

```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

token_counter = meter.create_counter("agent.tokens.used")
latency_histogram = meter.create_histogram("agent.latency.ms")

def with_telemetry(func):
    async def wrapper(agent, prompt, **kwargs):
        with tracer.start_as_current_span(f"agent.{agent.name}") as span:
            span.set_attribute("agent.name", agent.name)
            span.set_attribute("prompt.length", len(prompt))
            
            start = time.time()
            result = await func(agent, prompt, **kwargs)
            elapsed_ms = (time.time() - start) * 1000
            
            span.set_attribute("tokens_used", result.message.token_count)
            token_counter.add(result.message.token_count)
            latency_histogram.record(elapsed_ms)
            
            return result
    return wrapper

@with_telemetry
async def run_agent(agent, prompt, **kwargs):
    return await agent.run(prompt, **kwargs)
```

Every call emits a span + metrics. Jaeger/Prometheus pick them up.

## Composing Middleware

You can stack them:

```python
@with_telemetry
@with_retry
@audit_logging
@enforce_token_budget
async def run_agent(agent, prompt, **kwargs):
    return await agent.run(prompt, **kwargs)

# Execution order (outside-in):
# 1. telemetry captures the span
# 2. retry wrapper tries up to 3 times
# 3. audit logger logs start/end
# 4. token budget checker validates spend
# 5. agent runs
```

The execution flows down, then back up through each layer.

## Real Example: Genie's Supervisor

**ADK** had:
```python
def before_tool_call(context):
    print(f"Calling tool: {context.tool_name}")

def after_tool_call(context):
    print(f"Tool returned: {context.result}")

agent = Agent(..., before_tool_callback=before_tool_call, after_tool_callback=after_tool_call)
```

Basic logging. No composition. No metrics.

**MAF**:
```python
async def run_supervisor(prompt, user_id, budget_tokens=5000):
    @with_telemetry
    @audit_logging(user_id=user_id)
    @with_retry
    @enforce_token_budget(max_tokens=budget_tokens)
    async def run_agent(agent, prompt, **kw):
        return await agent.run(prompt, **kw)
    
    supervisor = Agent(client=build_chat_client(), name="Supervisor", ...)
    return await run_agent(supervisor, prompt)
```

Result:
- Traces + metrics for observability
- Audit log for compliance
- Automatic retry for resilience
- Token budget enforcement for cost control
- All composable; each layer does one thing

---

Next: [Deployment and A2A](/blog/2026/06/07/adk-to-maf-deployment.html)
