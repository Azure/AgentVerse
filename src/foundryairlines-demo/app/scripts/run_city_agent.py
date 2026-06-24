"""Standalone runner for the persistent Foundry activities agent.

Usage:
    python -m app.scripts.run_city_agent

Invokes the persistent agent `activities-agent` (visible in the Foundry
portal) under your Foundry project directly via MAF, without any orchestration.
"""
import asyncio
import sys
from app.backend.city_agents import run_activities_agent_standalone


async def main() -> None:
    city = sys.argv[1] if len(sys.argv) > 1 else "Barcelona"
    print(f"Searching activities in: {city}\n")
    text = await run_activities_agent_standalone(city)
    print(text)


if __name__ == "__main__":
    asyncio.run(main())
