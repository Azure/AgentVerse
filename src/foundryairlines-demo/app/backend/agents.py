"""3-agent demo orchestrated with **Microsoft Agent Framework (MAF)**.

Pipeline (following the WorkflowBuilder + sequential pattern from
https://learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential
and the worked example at
https://github.com/dsanchor/agents-observability-tt202/blob/main/from-zero-to-hero/orchestration/demo/sequential_agents.py):

    FlightsExecutor  ──►  EventsExecutor  ──►  (workflow yields the conversation)
       │ wraps                │ wraps
       ▼                      ▼
    flights-agent          events-agent
    (Foundry prompt        (Foundry prompt
     agent, persistent)     agent + Bing
                            Grounding tool)

After the MAF workflow yields its final messages, we run the gpt-image-2
banner step concurrently outside the workflow (image models aren't chat
agents and don't fit the executor pattern).

Env vars (via ``app/.env``): see ``app/.env.example``.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from agent_framework import (
    Executor,
    Message,
    Role,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    WorkflowEventType,
    handler,
)
from agent_framework.foundry import FoundryAgent
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
FLIGHTS_AGENT_NAME = os.getenv("FLIGHTS_AGENT_NAME", "flights-agent")
EVENTS_AGENT_NAME = os.getenv("EVENTS_AGENT_NAME", "events-agent")
IMAGE_ENDPOINT = os.getenv("IMAGE_ENDPOINT", "").rstrip("/")
IMAGE_DEPLOYMENT = os.getenv("IMAGE_DEPLOYMENT", "gpt-image-2")
IMAGE_API_VERSION = os.getenv("IMAGE_API_VERSION", "2025-04-01-preview")

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "flights.db"
OUTPUT_PATH = ROOT / "output"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


# ============================================================================
#  Helpers
# ============================================================================

def _query_low_occupancy(limit: int = 5) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, code, origin, destination, destination_city, destination_country,
               date, total_seats, sold_seats, price_eur,
               CAST(sold_seats AS REAL)/total_seats*100 AS occupancy_pct
        FROM flights ORDER BY occupancy_pct ASC LIMIT ?
        """,
        (limit,),
    )
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    for r in rows:
        r["occupancy_pct"] = round(r["occupancy_pct"], 1)
    return rows


def _extract_json(text: str) -> Any:
    """Tolerant JSON extractor — strips fences and finds the outermost array."""
    if not text:
        raise ValueError("empty agent response")
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        nl = s.find("\n")
        if nl >= 0:
            s = s[nl + 1 :]
    start = s.find("[")
    end = s.rfind("]")
    if start >= 0 and end > start:
        return json.loads(s[start : end + 1])
    return json.loads(s)


def _placeholder_event(flight: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": f"{flight['destination_city']} City Highlights",
        "short_description": (
            f"Top experiences awaiting you in {flight['destination_city']} this week."
        ),
        "source_url": "",
    }


_FIELD_ALIASES = {
    # snake_case variants
    "flight_id": "id",
    "flight_code": "code",
    "departure_airport": "origin",
    "arrival_airport": "destination",
    "arrival_city": "destination_city",
    "arrival_country": "destination_country",
    "flight_date": "date",
    "seats_total": "total_seats",
    "seats_sold": "sold_seats",
    "occupancy_percent": "occupancy_pct",
    # camelCase variants (the agent picks at random)
    "flightId": "id",
    "flightCode": "code",
    "departureAirport": "origin",
    "arrivalAirport": "destination",
    "destinationCity": "destination_city",
    "destinationCountry": "destination_country",
    "arrivalCity": "destination_city",
    "arrivalCountry": "destination_country",
    "flightDate": "date",
    "totalSeats": "total_seats",
    "soldSeats": "sold_seats",
    "seatsTotal": "total_seats",
    "seatsSold": "sold_seats",
    "occupancyPercent": "occupancy_pct",
    "occupancyPct": "occupancy_pct",
    "priceEur": "price_eur",
    "priceEUR": "price_eur",
}


def _normalize_flight(f: Dict[str, Any]) -> Dict[str, Any]:
    """Tolerate the agent renaming fields. Maps common aliases to the
    canonical names the rest of the pipeline expects."""
    out = dict(f)
    for src, dst in _FIELD_ALIASES.items():
        if src in out and dst not in out:
            out[dst] = out.pop(src)
    return out


def _restamp_flight_ids(
    flights: List[Dict[str, Any]], original_rows: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """The flights-agent regularly drops or renames canonical fields (id,
    destination_city, etc). Hydrate every flight by using the original DB
    row as the base and letting the agent's output overlay only non-null
    fields. Match by `code` first, then positional fallback (the prompt
    mandates same length & order)."""
    by_code = {r.get("code"): r for r in original_rows if r.get("code")}
    out: List[Dict[str, Any]] = []
    for i, f in enumerate(flights):
        match = by_code.get(f.get("code"))
        if match is None and i < len(original_rows):
            match = original_rows[i]
        if match is None:
            out.append(f)
            continue
        merged = dict(match)
        for k, v in f.items():
            if v is not None:
                merged[k] = v
        out.append(merged)
    return out


# ---------------------------------------------------------------------------
#  Agent #3 — gpt-image-2 banner generator
# ---------------------------------------------------------------------------

async def generate_banner(
    flight: Dict[str, Any], event: Dict[str, Any], client: httpx.AsyncClient
) -> Dict[str, Any]:
    """Call gpt-image-2 (REST + Entra ID) and persist the PNG. Retries on 429/503."""
    prompt = (
        f"Wide promotional travel banner for the city of {flight['destination_city']}, "
        f"{flight['destination_country']}. "
        f"IMPORTANT: Show iconic landmarks and scenery specific to {flight['destination_city']} — "
        f"do NOT depict any other city. "
        f"The banner advertises airline 'FoundryAirlines' flight {flight['code']} "
        f"from {flight['origin']} to {flight['destination_city']} on {flight['date']}. "
        f"Highlight the event: \"{event['title']}\" — {event['short_description']}. "
        f"Show the price '{flight['price_eur']} EUR' tastefully in the bottom-right. "
        "Painterly travel-poster style, vibrant yellow/white/grey palette, no text typos. "
        "Cinematic 16:9 composition, high-end advertising aesthetic."
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
            out = OUTPUT_PATH / f"banner_{flight['id']}.png"
            out.write_bytes(img_bytes)
            return {
                "flight_id": flight["id"],
                "image_url": f"/output/banner_{flight['id']}.png",
                "event": event,
            }
        last_err = f"{r.status_code}: {r.text[:200]}"
        if r.status_code in (429, 503):
            await asyncio.sleep(35 + attempt * 10)
            continue
        break
    raise RuntimeError(f"image API failed after retries: {last_err}")


# ============================================================================
#  MAF Executors — wrap the two persistent Foundry prompt agents
# ============================================================================
# We push **WorkflowEvent.emit(...)** events from inside each executor
# (custom payloads with a "kind" field). The orchestrator below subscribes
# to the event stream from `workflow.run(..., stream=True)` and forwards
# the relevant events to the SSE client.

class FlightsExecutor(Executor):
    """First step: ask the flights-agent prompt agent to format low-occupancy
    flights as JSON. The flight rows are loaded from the local SQLite DB."""

    def __init__(self, agent, id: str = "flights"):
        self._agent = agent
        super().__init__(id=id)

    @handler
    async def handle(
        self,
        message: Message,
        ctx: WorkflowContext[List[Message]],
    ) -> None:
        flights_rows = _query_low_occupancy(5)
        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "agent_log",
            "stage": "flights",
            "log": (
                f"Local DB query returned {len(flights_rows)} candidate flights — "
                "sending to flights-agent"
            ),
        }))

        prompt_text = (
            "Format the following raw flight rows as the JSON array described "
            f"in your instructions:\n{json.dumps(flights_rows)}"
        )
        user_msg = Message(role="user", contents=[prompt_text])
        response = await self._agent.run(user_msg)
        text = response.messages[-1].text if response.messages else ""

        try:
            flights = _extract_json(text)
            assert isinstance(flights, list) and flights
            flights = [_normalize_flight(f) for f in flights]
        except Exception:
            await ctx.add_event(WorkflowEvent.emit(self.id, {
                "kind": "agent_log",
                "stage": "flights",
                "log": "Agent output unparseable — falling back to raw DB rows",
            }))
            flights = flights_rows

        # The agent sometimes drops "id" even when instructed to keep it.
        # Re-stamp ids from the original DB rows, matching by flight code first
        # and falling back to positional alignment.
        flights = _restamp_flight_ids(flights, flights_rows)

        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "flights_ready",
            "flights": flights,
        }))
        # Forward a synthesized message containing the canonical (restamped)
        # flights JSON so the events-agent always sees the right `id` to key
        # its events on. The agent's raw response would intermittently drop
        # the id, breaking flight_id-based alignment downstream.
        canonical_msg = Message(
            role="assistant",
            contents=[json.dumps(flights, ensure_ascii=False)],
        )
        await ctx.send_message([user_msg, canonical_msg])


class EventsExecutor(Executor):
    """Second step: ask the events-agent prompt agent (Bing Grounding tool
    attached) to find one real public event per flight."""

    def __init__(self, agent, id: str = "events"):
        self._agent = agent
        super().__init__(id=id)

    @handler
    async def handle(
        self,
        messages: List[Message],
        ctx: WorkflowContext[None, List[Message]],
    ) -> None:
        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "agent_log",
            "stage": "events",
            "log": "Calling events-agent (Bing Grounding tool attached)…",
        }))

        ask = Message(
            role="user",
            contents=[
                "Now use the Bing Grounding tool to find one real upcoming event "
                "per flight from the JSON array in the previous turn, following "
                "your instructions. Return only the JSON array."
            ],
        )
        response = await self._agent.run([*messages, ask])
        text = response.messages[-1].text if response.messages else ""

        try:
            events = _extract_json(text)
            if not isinstance(events, list):
                events = []
        except Exception:
            events = []

        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "events_ready",
            "events": events,
        }))
        # Final executor → yield workflow output.
        await ctx.yield_output([*messages, ask, *response.messages])


# ============================================================================
#  Public orchestrator (drives SSE)
# ============================================================================

async def orchestrate(use_cached_banners: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
    """SSE-style async generator.

    Front-end contract (event types): agent_start, agent_log, flight, banner,
    agent_done, done, error.
    """
    try:
        async with AsyncDefaultAzureCredential() as credential:
            flights_agent = FoundryAgent(
                project_endpoint=PROJECT_ENDPOINT,
                agent_name=FLIGHTS_AGENT_NAME,
                credential=credential,
            )
            events_agent = FoundryAgent(
                project_endpoint=PROJECT_ENDPOINT,
                agent_name=EVENTS_AGENT_NAME,
                credential=credential,
            )

            flights_exec = FlightsExecutor(flights_agent)
            events_exec = EventsExecutor(events_agent)

            workflow = (
                WorkflowBuilder(
                    name="FoundryAirlinesSequential",
                    description="flights-agent → events-agent (Bing Grounding)",
                    start_executor=flights_exec,
                )
                .add_edge(flights_exec, events_exec)
                .build()
            )

            yield {
                "type": "agent_start",
                "agent": "flights",
                "message": (
                    f"MAF workflow started — {FLIGHTS_AGENT_NAME} "
                    f"→ {EVENTS_AGENT_NAME}"
                ),
            }

            flights: List[Dict[str, Any]] = []
            events: List[Dict[str, Any]] = []
            flights_done_emitted = False

            trigger = Message(role="user", contents=["Begin the FoundryAirlines pipeline."])

            async for event in workflow.run(trigger, stream=True):
                # We only care about our custom 'data' events emitted by
                # the executors (carry a {"kind": ...} dict).
                data = getattr(event, "data", None)
                if event.type == "data" and isinstance(data, dict) and "kind" in data:
                    kind = data["kind"]
                    if kind == "agent_log":
                        yield {
                            "type": "agent_log",
                            "agent": data["stage"],
                            "message": data["log"],
                        }
                    elif kind == "flights_ready":
                        flights = data["flights"]
                        yield {
                            "type": "agent_log",
                            "agent": "flights",
                            "message": (
                                f"flights-agent returned {len(flights)} flights "
                                "with the lowest occupancy"
                            ),
                        }
                        for f in flights:
                            yield {"type": "flight", "data": f}
                        yield {"type": "agent_done", "agent": "flights"}
                        flights_done_emitted = True
                        yield {
                            "type": "agent_start",
                            "agent": "events",
                            "message": (
                                f"{EVENTS_AGENT_NAME} starting "
                                "(Bing Grounding tool attached)"
                            ),
                        }
                    elif kind == "events_ready":
                        events_raw = data["events"]
                        events = _align_events_to_flights(flights, events_raw)
                        for f, e in zip(flights, events):
                            yield {
                                "type": "agent_log",
                                "agent": "events",
                                "message": f"{f['destination_city']}: {e['title']}",
                            }
                        yield {"type": "agent_done", "agent": "events"}

            if not flights_done_emitted:
                yield {
                    "type": "error",
                    "message": "MAF workflow ended without flights — see backend logs",
                }

        # ---- Agent #3: gpt-image-2 banners (concurrent post-workflow) -----
        yield {
            "type": "agent_start",
            "agent": "banners",
            "message": "Calling gpt-image-2 to generate 5 banners (post-workflow concurrent step)…",
        }

        if not flights or not events:
            yield {"type": "agent_log", "agent": "banners",
                   "message": "No flights/events available — skipping banners"}
            yield {"type": "agent_done", "agent": "banners"}
            yield {"type": "done", "message": "All agents completed"}
            return

        if use_cached_banners:
            yield {"type": "agent_log", "agent": "banners",
                   "message": "[cached mode] reusing previously generated banners for fast demo"}
            for f, e in zip(flights, events):
                cached = OUTPUT_PATH / f"banner_{f['id']}.png"
                if cached.exists():
                    await asyncio.sleep(2.0)
                    yield {"type": "banner", "data": {
                        "flight_id": f["id"],
                        "image_url": f"/output/banner_{f['id']}.png",
                        "event": e,
                    }}
                    yield {"type": "agent_log", "agent": "banners",
                           "message": f"✓ banner ready for flight #{f['id']} ({f['destination_city']})"}
            yield {"type": "agent_done", "agent": "banners"}
            yield {"type": "done", "message": "All agents completed"}
            return

        yield {"type": "agent_log", "agent": "banners",
               "message": "This is the slow step (~60-120 s). Banners stream as they finish."}

        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
            sem = asyncio.Semaphore(2)

            async def _gen(f, e):
                async with sem:
                    return await generate_banner(f, e, client)

            tasks = [
                asyncio.create_task(_gen(f, e))
                for f, e in zip(flights, events)
            ]
            for done in asyncio.as_completed(tasks):
                try:
                    result = await done
                    yield {"type": "banner", "data": result}
                    yield {"type": "agent_log", "agent": "banners",
                           "message": f"✓ banner ready for flight #{result['flight_id']}"}
                except Exception as ex:
                    yield {"type": "agent_log", "agent": "banners",
                           "message": f"✗ banner failed: {ex}"}

        yield {"type": "agent_done", "agent": "banners"}
        yield {"type": "done", "message": "All agents completed"}

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {"type": "error", "message": str(e)}
        yield {"type": "done", "message": "halted"}


def _align_events_to_flights(
    flights: List[Dict[str, Any]], raw_events: List[Any]
) -> List[Dict[str, Any]]:
    """Match the agent's events back to flights by flight_id, falling back to
    a placeholder event when the agent missed one. Tolerates the agent
    nesting the event under an 'event' key and using slightly different
    field names."""
    by_id: Dict[int, Dict[str, Any]] = {}
    positional: List[Optional[Dict[str, Any]]] = []
    for ev in raw_events:
        if not isinstance(ev, dict):
            positional.append(None)
            continue
        # The agent may put fields at the top level OR nested under "event".
        nested = ev.get("event") if isinstance(ev.get("event"), dict) else {}
        title = (
            ev.get("title")
            or nested.get("title")
            or nested.get("name")
            or ""
        )
        title = str(title).strip()
        if not title:
            positional.append(None)
            continue
        desc = (
            ev.get("short_description")
            or nested.get("short_description")
            or nested.get("description")
            or " ".join(
                str(x) for x in (
                    nested.get("location"),
                    nested.get("start_date"),
                ) if x
            )
        )
        url = (
            ev.get("source_url")
            or ev.get("url")
            or nested.get("source_url")
            or nested.get("url")
            or ""
        )
        clean = {
            "title": str(title)[:80],
            "short_description": str(desc)[:160],
            "source_url": str(url)[:200],
        }
        positional.append(clean)
        try:
            fid = int(ev.get("flight_id") or ev.get("id") or nested.get("flight_id"))
            by_id[fid] = clean
        except (TypeError, ValueError):
            pass

    out: List[Dict[str, Any]] = []
    for i, f in enumerate(flights):
        match = by_id.get(f.get("id"))
        # Positional fallback: prompt mandates same length & order as flights.
        if match is None and i < len(positional) and positional[i] is not None:
            match = positional[i]
        out.append(match or _placeholder_event(f))
    return out


# ============================================================================
#  Standalone runners (used by app/scripts/*)
# ============================================================================

async def run_flights_agent_standalone(prompt: Optional[str] = None) -> str:
    async with AsyncDefaultAzureCredential() as credential:
        agent = FoundryAgent(
            project_endpoint=PROJECT_ENDPOINT,
            agent_name=FLIGHTS_AGENT_NAME,
            credential=credential,
        )
        flights_rows = _query_low_occupancy(5)
        user_input = prompt or (
            "Format the following flight rows as the JSON array described "
            f"in your instructions:\n{json.dumps(flights_rows)}"
        )
        response = await agent.run(Message(role="user", contents=[user_input]))
        return response.messages[-1].text if response.messages else ""


async def run_events_agent_standalone(flights_json: str) -> str:
    async with AsyncDefaultAzureCredential() as credential:
        agent = FoundryAgent(
            project_endpoint=PROJECT_ENDPOINT,
            agent_name=EVENTS_AGENT_NAME,
            credential=credential,
        )
        user_input = (
            "The following JSON array of flights is the input. Use the Bing "
            "Grounding tool to find one real upcoming event per flight as "
            f"instructed:\n\n{flights_json}"
        )
        response = await agent.run(Message(role="user", contents=[user_input]))
        return response.messages[-1].text if response.messages else ""

