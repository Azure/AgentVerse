"""Standalone runner for the persistent Foundry flights agent.

Usage:
    python -m app.scripts.run_flights_agent

Invokes the persistent agent `vueling-flights-agent` (visible in the Foundry
portal) under your Foundry project directly via MAF, without any orchestration.
"""
import asyncio
from app.backend.agents import run_flights_agent_standalone


async def main() -> None:
    text = await run_flights_agent_standalone()
    print(text)


if __name__ == "__main__":
    asyncio.run(main())

