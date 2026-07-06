# `tools/` — how an agent touches the world (block #3)

> A tool is a capability the model can invoke. Three kinds; pick the simplest that fits.
> Every tool needs a **precise name, a clear description, and typed parameters** — the model
> only uses tools it understands.

## The three kinds

| Kind | What it is | Use when | Example |
|---|---|---|---|
| **function** | A typed Python function the agent calls | The capability is your own code (DB query, calc, internal API) | `get_low_occupancy_flights()` (foundryairlines) |
| **hosted** | A Foundry-managed tool attached to the agent | Azure provides it and manages auth/runtime | Grounding with Bing Search |
| **mcp** | An external tool server over the Model Context Protocol | You want to reuse a standard, out-of-process tool ecosystem | a filesystem / GitHub / third-party MCP server |

## Function tool — sketch

```python
# agents/<agent>/tools.py
from pydantic import BaseModel, Field

class FlightQuery(BaseModel):
    limit: int = Field(5, ge=1, le=50, description="How many flights to return.")

def get_low_occupancy_flights(q: FlightQuery) -> list[dict]:
    """Return the N flights with the lowest occupancy from the bookings DB.

    The docstring + typed params ARE the tool description the model reads. Be precise.
    """
    ...
```

## Hosted tool — declare it in `agent.yaml`

```yaml
tools:
  - name: bing-grounding
    kind: hosted
    connection: bing-grounding     # the Foundry project connection name
```

Attach the connection once in the Foundry portal (Management center → Connected resources),
then the bootstrap step binds it as a persistent tool — exactly how foundryairlines' events
agent uses Bing Grounding.

## MCP tool — point at a server

```yaml
tools:
  - name: repo-tools
    kind: mcp
    server: https://your-mcp-server        # or a local stdio command
```

## Rules

- **Describe tools for the model, not for you.** The name + description are prompt surface;
  vague descriptions cause wrong tool calls.
- **Type every parameter** (Pydantic) — it constrains the model and validates the call.
- **Handle failure** — timeout, retry, and a fallback. Both existing demos fall back
  (placeholder events, direct SQL) so the demo continues if a tool fails.
- **Least privilege** — a tool should do one narrow thing; don't hand the model a
  "run anything" tool.
