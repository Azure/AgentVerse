# `agents/shared/` — plumbing every agent reuses

> Blocks #2 (model access) and #4 (memory), plus the helpers guardrails/observability build
> on. One copy, imported everywhere — so a change (new gateway URL, new auth) happens once.

Recommended modules (create the ones your demo needs):

| Module | Block | Responsibility |
|---|---|---|
| `azure_client.py` | #2 | The single model/agent client. Points at the **APIM gateway**, auth via `DefaultAzureCredential`. Every agent imports `get_agent_client(name)` / `get_openai_client()` from here. **No API keys anywhere else.** |
| `guardrails.py` | #6 | `guard_input(text)` / `validate_output(model, text)` used at agent boundaries. See [`../../guardrails/`](../../guardrails/). |
| `telemetry.py` | #7 | OpenTelemetry tracer setup + token/cost metric emitters. See [`../../observability/`](../../observability/). |
| `memory.py` | #4 | Long-term store access (e.g. Cosmos DB repository). Short-term memory is the MAF thread passed between executors — not here. |
| `models.py` | #1 | Enums/dataclasses shared across agents (e.g. `Decision`, `Severity`). Agent-specific schemas stay in that agent's `schemas.py`. |

## The one rule that matters

**All model access flows through `azure_client.py`, and it points at the gateway.**

```python
# agents/shared/azure_client.py  (sketch)
import os
from azure.identity import DefaultAzureCredential
from agent_framework.azure import AzureAIAgentClient

def get_agent_client(agent_name: str) -> AzureAIAgentClient:
    """One place that knows the endpoint + auth. Gateway + managed identity, no keys."""
    return AzureAIAgentClient(
        project_endpoint=os.environ["PROJECT_ENDPOINT"],   # or APIM_GATEWAY_URL
        credential=DefaultAzureCredential(),
        agent_name=agent_name,
    )
```

Why: it gives you central rate limits, content safety, and audit for free (the APIM
policies), and keeps secrets out of the codebase. See the insurance demo's
`azure_client.py` switch between direct and gateway paths for a real example.
