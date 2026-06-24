# FoundryAirlines AI Demo - Backend

FastAPI backend with 3-agent orchestration using Azure AI Foundry Agent Service.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.backend.main:app --port 8765

# Access the app
http://127.0.0.1:8765/
```

## Architecture

### Agent 1: Flight Analyst
- **Type**: Azure AI Foundry Agent with function tool
- **Function**: `get_low_occupancy_flights` - queries SQLite for 5 lowest occupancy flights
- **Model**: gpt-4.1
- **Fallback**: Direct SQL query if JSON parsing fails

### Agent 2: Event Finder
- **Type**: Azure AI Foundry Agent with Bing Grounding tool
- **Purpose**: Find public events in destination cities
- **Model**: gpt-4.1
- **Fallback**: Placeholder events if Bing search fails

### Agent 3: Banner Generator
- **Type**: Direct REST API call to gpt-image-2
- **Endpoint**: prisa-demo-comic-resource.cognitiveservices.azure.com
- **Settings**: 1536x1024, quality:low
- **Parallelism**: 5 concurrent generations with asyncio.gather
- **Duration**: ~60-90 seconds per image

## API Endpoints

### `GET /`
Serves the frontend (index.html)

### `GET /api/run`
SSE endpoint streaming orchestration events:
- `agent_start` - Agent begins work
- `agent_log` - Progress message
- `agent_done` - Agent completed
- `flight` - Flight data
- `banner` - Generated banner result
- `error` - Error message
- `done` - Orchestration complete

### Static Routes
- `/static/*` → frontend files
- `/output/*` → generated banner images

## Environment Variables

Required in `app/.env`:
```
PROJECT_ENDPOINT=https://jrubiosainz-8867-resource.services.ai.azure.com/api/projects/jrubiosainz-8867
FOUNDRY_API_KEY=<key>
MODEL_DEPLOYMENT_NAME=gpt-4.1
BING_CONNECTION_NAME=bing-grounding
IMAGE_ENDPOINT=https://prisa-demo-comic-resource.cognitiveservices.azure.com
IMAGE_DEPLOYMENT=gpt-image-2-1
IMAGE_API_KEY=<key>
IMAGE_API_VERSION=2025-04-01-preview
```

## Testing

```bash
# Test database query
python app/scripts/test_backend.py

# Test SSE stream (with server running)
curl http://127.0.0.1:8765/api/run
```

## Files

```
app/
├── backend/
│   ├── __init__.py
│   ├── main.py      # FastAPI app
│   ├── agents.py    # 3-agent orchestration
│   └── sse.py       # SSE formatting helper
├── data/
│   └── flights.db   # SQLite database (25 flights)
├── frontend/
│   └── index.html   # Web UI
└── output/          # Generated banners
```

## Dependencies

- fastapi - Web framework
- uvicorn - ASGI server
- azure-ai-agents - Foundry Agent SDK
- azure-ai-projects - Project client for connections
- azure-identity - Azure authentication
- httpx - Async HTTP client for image generation
- python-dotenv - Environment variables
- pydantic - Data validation

## Notes

- Banner generation is SLOW (~60-90s per image even at quality:low)
- All 5 banners generate concurrently to save time
- SSE events stream in real-time as each step completes
- Fallback strategies ensure demo continues even if agents fail
