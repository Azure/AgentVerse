"""City Activities Poster — MAF orchestration + gpt-image-2.

Pipeline:

    ActivitiesExecutor  ──►  (workflow yields)  ──►  gpt-image-2 poster
       │ wraps
       ▼
    activities-agent
    (Foundry prompt agent
     + Bing Grounding tool)

The user provides a city name. The activities-agent searches Bing for real
activities/attractions and returns structured JSON. Then gpt-image-2 generates
a travel poster showcasing all activities.

Env vars (via ``app/.env``): same as the flights demo.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List

import httpx
from agent_framework import (
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    handler,
)
from agent_framework.foundry import FoundryAgent
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
ACTIVITIES_AGENT_NAME = os.getenv("ACTIVITIES_AGENT_NAME", "activities-agent")
IMAGE_ENDPOINT = os.getenv("IMAGE_ENDPOINT", "").rstrip("/")
IMAGE_DEPLOYMENT = os.getenv("IMAGE_DEPLOYMENT", "gpt-image-2")
IMAGE_API_VERSION = os.getenv("IMAGE_API_VERSION", "2025-04-01-preview")

ROOT = Path(__file__).parent.parent
OUTPUT_PATH = ROOT / "output"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


# ============================================================================
#  Helpers
# ============================================================================

def _extract_json(text: str) -> Any:
    """Tolerant JSON extractor — strips fences and finds the outermost array."""
    if not text:
        raise ValueError("empty agent response")
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        nl = s.find("\n")
        if nl >= 0:
            s = s[nl + 1:]
    start = s.find("[")
    end = s.rfind("]")
    if start >= 0 and end > start:
        return json.loads(s[start: end + 1])
    return json.loads(s)


def _sanitize_filename(city: str) -> str:
    """Convert city name to a safe filename fragment."""
    return "".join(c if c.isalnum() else "_" for c in city.lower()).strip("_")


# ---------------------------------------------------------------------------
#  gpt-image-2 poster generator
# ---------------------------------------------------------------------------

async def generate_poster(
    city: str, activities: List[Dict[str, Any]], client: httpx.AsyncClient
) -> Dict[str, Any]:
    """Call gpt-image-2 (REST + Entra ID) to create a travel poster. Retries on 429/503."""
    activities_text = "\n".join(
        f"- {a['title']} ({a.get('category', 'general')}): {a.get('description', '')}"
        for a in activities
    )
    prompt = (
        f"A vibrant, artistic travel poster for the city of {city}. "
        f"The poster should visually represent these activities and attractions:\n"
        f"{activities_text}\n\n"
        f"Style: colorful illustrated travel poster, vintage meets modern, "
        f"bold typography showing the city name '{city}' prominently at the top. "
        f"Include visual icons or scenes for each activity category. "
        f"Warm inviting colors, professional travel agency aesthetic, 16:9 composition."
    )
    payload = {
        "prompt": prompt,
        "n": 1,
        "size": "1536x1024",
        "output_format": "png",
        "quality": "low",
    }
    cred = DefaultAzureCredential()
    token = cred.get_token("https://cognitiveservices.azure.com/.default").token
    url = (
        f"{IMAGE_ENDPOINT}/openai/deployments/{IMAGE_DEPLOYMENT}"
        f"/images/generations?api-version={IMAGE_API_VERSION}"
    )
    last_err = ""
    for attempt in range(6):
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        if r.status_code == 200:
            data = r.json()["data"][0]
            img_bytes = base64.b64decode(data["b64_json"])
            filename = f"poster_{_sanitize_filename(city)}.png"
            out = OUTPUT_PATH / filename
            out.write_bytes(img_bytes)
            return {
                "city": city,
                "image_url": f"/output/{filename}",
                "activities_count": len(activities),
            }
        last_err = f"{r.status_code}: {r.text[:200]}"
        if r.status_code in (429, 503):
            await asyncio.sleep(35 + attempt * 10)
            continue
        break
    raise RuntimeError(f"image API failed after retries: {last_err}")


# ============================================================================
#  MAF Executor — wraps the persistent Foundry activities-agent
# ============================================================================

class ActivitiesExecutor(Executor):
    """Ask the activities-agent to search Bing for activities in a city."""

    def __init__(self, agent, id: str = "activities"):
        self._agent = agent
        super().__init__(id=id)

    @handler
    async def handle(
        self,
        message: Message,
        ctx: WorkflowContext,
    ) -> None:
        # The message content is the city name (Content object → str)
        city = str(message.contents[0]) if message.contents else "Paris"

        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "agent_log",
            "stage": "activities",
            "log": f"Searching for activities in {city} using Bing Grounding…",
        }))

        prompt_text = (
            f"Find activities, attractions, and experiences for a traveler visiting "
            f"the city of {city}. Use Bing Grounding to search for real, current "
            f"information. Return the JSON array as described in your instructions."
        )
        user_msg = Message(role="user", contents=[prompt_text])
        response = await self._agent.run(user_msg)
        text = response.messages[-1].text if response.messages else ""

        try:
            activities = _extract_json(text)
            assert isinstance(activities, list) and activities
        except Exception:
            await ctx.add_event(WorkflowEvent.emit(self.id, {
                "kind": "agent_log",
                "stage": "activities",
                "log": "Agent output unparseable — returning empty activities",
            }))
            activities = []

        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "activities_ready",
            "city": city,
            "activities": activities,
        }))

        # Yield workflow output
        canonical_msg = Message(
            role="assistant",
            contents=[json.dumps({"city": city, "activities": activities}, ensure_ascii=False)],
        )
        await ctx.yield_output([user_msg, canonical_msg])


# ============================================================================
#  Public orchestrator (drives SSE)
# ============================================================================

async def orchestrate_city(city: str) -> AsyncGenerator[Dict[str, Any], None]:
    """SSE-style async generator for the city activities pipeline.

    Front-end contract (event types): agent_start, agent_log, activity,
    poster, agent_done, done, error.
    """
    try:
        async with AsyncDefaultAzureCredential() as credential:
            activities_agent = FoundryAgent(
                project_endpoint=PROJECT_ENDPOINT,
                agent_name=ACTIVITIES_AGENT_NAME,
                credential=credential,
            )

            activities_exec = ActivitiesExecutor(activities_agent)

            workflow = (
                WorkflowBuilder(
                    name="CityActivitiesPipeline",
                    description="activities-agent (Bing Grounding) → poster",
                    start_executor=activities_exec,
                )
                .build()
            )

            yield {
                "type": "agent_start",
                "agent": "activities",
                "message": f"Searching for activities in {city}…",
            }

            activities: List[Dict[str, Any]] = []

            trigger = Message(role="user", contents=[city])

            async for event in workflow.run(trigger, stream=True):
                data = getattr(event, "data", None)
                if event.type == "data" and isinstance(data, dict) and "kind" in data:
                    kind = data["kind"]
                    if kind == "agent_log":
                        yield {
                            "type": "agent_log",
                            "agent": data["stage"],
                            "message": data["log"],
                        }
                    elif kind == "activities_ready":
                        activities = data["activities"]
                        yield {
                            "type": "agent_log",
                            "agent": "activities",
                            "message": f"Found {len(activities)} activities in {city}",
                        }
                        for a in activities:
                            yield {"type": "activity", "data": a}
                        yield {"type": "agent_done", "agent": "activities"}

            if not activities:
                yield {
                    "type": "error",
                    "message": "No activities found — cannot generate poster",
                }
                yield {"type": "done", "message": "halted"}
                return

            # ---- gpt-image-2 poster generation ----
            yield {
                "type": "agent_start",
                "agent": "poster",
                "message": f"Generating travel poster for {city} with gpt-image-2…",
            }

            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
                try:
                    result = await generate_poster(city, activities, client)
                    yield {"type": "poster", "data": result}
                    yield {
                        "type": "agent_log",
                        "agent": "poster",
                        "message": f"✓ Poster ready for {city}",
                    }
                except Exception as ex:
                    yield {
                        "type": "agent_log",
                        "agent": "poster",
                        "message": f"✗ Poster generation failed: {ex}",
                    }

            yield {"type": "agent_done", "agent": "poster"}
            yield {"type": "done", "message": "All steps completed"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {"type": "error", "message": str(e)}
        yield {"type": "done", "message": "halted"}


# ============================================================================
#  Standalone runner (for testing without FastAPI)
# ============================================================================

async def run_activities_agent_standalone(city: str) -> str:
    """Run just the activities-agent for a given city, return raw text."""
    async with AsyncDefaultAzureCredential() as credential:
        agent = FoundryAgent(
            project_endpoint=PROJECT_ENDPOINT,
            agent_name=ACTIVITIES_AGENT_NAME,
            credential=credential,
        )
        prompt = (
            f"Find activities, attractions, and experiences for a traveler visiting "
            f"the city of {city}. Use Bing Grounding to search for real, current "
            f"information. Return the JSON array as described in your instructions."
        )
        response = await agent.run(Message(role="user", contents=[prompt]))
        return response.messages[-1].text if response.messages else "(no response)"
