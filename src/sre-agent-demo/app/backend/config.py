"""Configuration for the Azure SRE Agent demo.

The demo ships in a **guided replay** mode by default: it serves a deterministic,
seeded incident-investigation walkthrough and makes NO live Azure calls, so the
portal tab always renders with zero cost and zero blast radius.

A future **live** path (read-only proxy to a dedicated *sandbox* SRE Agent) can be
wired in without touching the frontend: set SRE_AGENT_RESOURCE_ID (and grant the
managed identity an "SRE Agent Reader"/"User" role on that agent). Until every
required live setting is present AND validated, the app stays in replay mode. See
README.md for the safety rules that any live path must honour.
"""
from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    return (os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"})


# --- live path (all OFF by default; replay mode requires no Azure at all) -----

# ARM resource id of a *dedicated sandbox* SRE Agent, e.g.
# /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.App/agents/<name>
SRE_AGENT_RESOURCE_ID = os.getenv("SRE_AGENT_RESOURCE_ID", "").strip()

# Managed-identity client id (user-assigned) for DefaultAzureCredential, injected
# by the unified deploy. Only used by the (future) live path.
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "").strip()

# Data-plane token audience for the SRE Agent (documented, PREVIEW).
SRE_DATAPLANE_SCOPE = os.getenv("SRE_DATAPLANE_SCOPE", "https://azuresre.dev/.default").strip()
ARM_SCOPE = os.getenv("ARM_SCOPE", "https://management.azure.com/.default").strip()
SRE_API_VERSION = os.getenv("SRE_API_VERSION", "2025-05-01-preview").strip()

# Hard safety rails for any live path (see rubber-duck review in README):
#  - writes (send message / approvals) are OFF unless explicitly enabled AND the
#    agent is in a non-Automatic mode; approvals stay OFF by default even then.
SRE_AGENT_ALLOW_WRITE = _flag("SRE_AGENT_ALLOW_WRITE", False)
SRE_AGENT_ALLOW_APPROVALS = _flag("SRE_AGENT_ALLOW_APPROVALS", False)

# Only *.azuresre.ai data-plane hosts are ever contacted (SSRF guard).
SRE_ALLOWED_ENDPOINT_SUFFIX = os.getenv("SRE_ALLOWED_ENDPOINT_SUFFIX", ".azuresre.ai").strip()


def live_configured() -> bool:
    """True only when a live sandbox agent is deliberately configured.

    We intentionally require an explicit resource id; a missing id means the demo
    is *meant* to run in replay mode (not that a live integration silently broke).
    """
    return bool(SRE_AGENT_RESOURCE_ID)


PORT = int(os.getenv("PORT", "8780"))
