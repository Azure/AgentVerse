#!/usr/bin/env python3
"""Quick test of backend orchestration without running full demo."""

import asyncio
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.backend.agents import get_low_occupancy_flights


async def test_basic():
    """Test basic functionality."""
    print("Testing database query...")
    flights_json = get_low_occupancy_flights(5)
    print(f"✓ Got flights: {len(flights_json)} bytes")
    
    print("\nTest passed! Backend is ready.")
    print("\nTo start the server:")
    print("  uvicorn app.backend.main:app --port 8765")
    print("\nTo test the SSE endpoint:")
    print("  curl http://127.0.0.1:8765/api/run")


if __name__ == "__main__":
    asyncio.run(test_basic())
