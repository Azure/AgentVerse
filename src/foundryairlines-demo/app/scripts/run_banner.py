"""Standalone runner for the gpt-image-2 banner generation step.

Usage:
    python -m app.scripts.run_banner

Generates one banner directly via the gpt-image-2 deployment (NOT a Foundry
Agent — this is an Azure OpenAI image model deployment, visible in the
Foundry portal under project → Models + endpoints).
"""
import asyncio
import httpx
from app.backend.agents import generate_banner, _query_low_occupancy


async def main() -> None:
    flight = _query_low_occupancy(1)[0]
    event = {
        "title": "Sample destination event",
        "short_description": "Standalone test of the gpt-image-2 banner step.",
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        result = await generate_banner(flight, event, client)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
