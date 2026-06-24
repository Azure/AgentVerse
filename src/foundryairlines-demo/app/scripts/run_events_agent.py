"""Standalone runner for the persistent Foundry events agent.

Usage:
    python -m app.scripts.run_events_agent

Invokes the persistent agent `vueling-events-agent` (visible in the Foundry
portal) under your Foundry project with a sample flights JSON payload.
"""
import asyncio
import json
from app.backend.agents import run_events_agent_standalone, _query_low_occupancy


async def main() -> None:
    flights = _query_low_occupancy(5)
    text = await run_events_agent_standalone(json.dumps(flights, indent=2))
    print(text)


if __name__ == "__main__":
    asyncio.run(main())

