from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import sys

# On Windows the default ProactorEventLoop is incompatible with aiohttp,
# which the azure-identity / azure-ai-* SDKs use under the hood. Use the
# selector loop instead — required for the Foundry SDK calls to connect.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .agents import orchestrate
from .city_agents import orchestrate_city
from .sse import format_sse

app = FastAPI()

# Get paths
FRONTEND_PATH = Path(__file__).parent.parent / "frontend"
FRONTEND_CITY_PATH = Path(__file__).parent.parent / "frontend_city"
OUTPUT_PATH = Path(__file__).parent.parent / "output"

# Mount static directories
app.mount("/static", StaticFiles(directory=str(FRONTEND_PATH)), name="static")
app.mount("/static_city", StaticFiles(directory=str(FRONTEND_CITY_PATH)), name="static_city")
app.mount("/output", StaticFiles(directory=str(OUTPUT_PATH)), name="output")


@app.get("/")
async def root():
    """Serve the frontend."""
    return FileResponse(FRONTEND_PATH / "index.html")


@app.get("/api/run")
async def run_orchestration(cached: int = 0):
    """SSE endpoint that streams the orchestration. cached=1 reuses pre-generated banners (fast demo mode)."""

    async def event_stream():
        async for event in orchestrate(use_cached_banners=bool(cached)):
            event_type = event.pop("type")
            yield format_sse(event_type, event)
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/city")
async def city_root():
    """Serve the city activities frontend."""
    return FileResponse(FRONTEND_CITY_PATH / "index.html")


@app.get("/api/city")
async def run_city_orchestration(city: str = "Barcelona"):
    """SSE endpoint that streams the city activities pipeline."""

    async def event_stream():
        async for event in orchestrate_city(city):
            event_type = event.pop("type")
            yield format_sse(event_type, event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
