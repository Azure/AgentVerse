"""Signal-to-Service — agentic orchestration with Microsoft Agent Framework.

Narrative "from signal to action", split into two human-in-the-loop phases:

  Phase A  ``orchestrate_diagnose``  (streamed by GET /api/diagnose)
    A MAF **sequential workflow** runs two persistent Foundry prompt agents:

        DiagnosisExecutor ─► KnowledgeExecutor
           │ wraps               │ wraps
           ▼                     ▼
      diagnosis-agent        knowledge-agent
      (classifies the        (summarises + cites the
       failure mode,          SOP retrieved by our own
       criticality, RUL)      RAG layer — Azure AI Search
                              or local TF-IDF fallback)

    The phase ends by persisting the run and emitting ``awaiting_approval``
    with a proposed work order (the governance gate).

  Phase B  ``orchestrate_dispatch``  (streamed by GET /api/dispatch?run_id=)
    Runs only after a human approves. The action-agent drafts the work-order
    summary, then in-process tools create the work order (CMMS mock) and
    schedule a technician (scheduler mock). Idempotent per run_id.

Env (see app/.env.example): PROJECT_ENDPOINT, MODEL_DEPLOYMENT_NAME and the
three prefixed agent names.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent_framework import (
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework.foundry import FoundryAgent
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from dotenv import load_dotenv

from . import cmms, rag, scheduler, telemetry

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
DIAGNOSIS_AGENT_NAME = os.getenv("DIAGNOSIS_AGENT_NAME", "signal-to-service-diagnosis-agent")
KNOWLEDGE_AGENT_NAME = os.getenv("KNOWLEDGE_AGENT_NAME", "signal-to-service-knowledge-agent")
ACTION_AGENT_NAME = os.getenv("ACTION_AGENT_NAME", "signal-to-service-action-agent")

_PRIORITY_BY_CRITICALITY = {"high": "P1", "medium": "P2", "low": "P3"}


# ============================================================================
#  Helpers
# ============================================================================

def _extract_json(text: str) -> Any:
    """Tolerant JSON extractor — strips code fences, finds the outer object/array."""
    if not text:
        raise ValueError("empty agent response")
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        nl = s.find("\n")
        if nl >= 0:
            s = s[nl + 1:]
    for opener, closer in (("{", "}"), ("[", "]")):
        start = s.find(opener)
        end = s.rfind(closer)
        if start >= 0 and end > start:
            try:
                return json.loads(s[start:end + 1])
            except json.JSONDecodeError:
                continue
    return json.loads(s)


def telemetry_summary(series: Dict[str, Any]) -> Dict[str, Any]:
    """Compact, model-friendly view of the telemetry window."""
    points = series["points"]
    last = points[-1]
    channels = {}
    for ch in series["channels"]:
        values = [p[ch] for p in points]
        channels[ch] = {
            "nominal": series["nominal"][ch],
            "warn": series["warn"][ch],
            "alarm": series["alarm"][ch],
            "current": last[ch],
            "peak": round(max(values), 2),
            "breached_warn": last[ch] >= series["warn"][ch],
            "breached_alarm": last[ch] >= series["alarm"][ch],
        }
    return {
        "asset_id": series["asset_id"],
        "sample_seconds": series["sample_seconds"],
        "channels": channels,
        "anomaly": series.get("anomaly"),
    }


def _heuristic_diagnosis(asset: Dict[str, Any], summary: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic fallback if the agent output is unparseable."""
    fm = asset.get("failure_hint", "bearing")
    breached = any(c["breached_alarm"] for c in summary["channels"].values())
    return {
        "failure_mode": fm,
        "criticality": asset.get("criticality", "medium") if breached else "medium",
        "rul_days": 3 if breached else 10,
        "confidence": 0.5,
        "rationale": "Fallback heuristic from telemetry thresholds (agent JSON unparseable).",
    }


def build_proposal(asset: Dict[str, Any], diagnosis: Dict[str, Any], sop: Dict[str, Any]) -> Dict[str, Any]:
    criticality = str(diagnosis.get("criticality", asset.get("criticality", "medium"))).lower()
    return {
        "asset_id": asset["id"],
        "asset_model": asset["model"],
        "location": asset["location"],
        "title": f"{diagnosis.get('failure_mode', 'fault').title()} on {asset['id']} — {asset['model']}",
        "failure_mode": diagnosis.get("failure_mode"),
        "criticality": criticality,
        "priority": _PRIORITY_BY_CRITICALITY.get(criticality, "P2"),
        "rul_days": diagnosis.get("rul_days"),
        "required_skill": asset.get("required_skill"),
        "sop_id": sop.get("sop_id") or sop.get("doc_id"),
        "sop_title": sop.get("title"),
        "sop_citation": sop.get("citation") or sop.get("source"),
    }


# ============================================================================
#  MAF Executors (Phase A)
# ============================================================================

class DiagnosisExecutor(Executor):
    """Step 1 — the diagnosis-agent classifies the failure from telemetry."""

    def __init__(self, agent, asset: Dict[str, Any], summary: Dict[str, Any], id: str = "diagnosis"):
        self._agent = agent
        self._asset = asset
        self._summary = summary
        self.diagnosis: Dict[str, Any] = {}
        super().__init__(id=id)

    @handler
    async def handle(self, message: Message, ctx: WorkflowContext[List[Message]]) -> None:
        from agent_framework import WorkflowEvent
        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "agent_log", "stage": "diagnosis",
            "log": f"Analysing telemetry window for {self._asset['id']} ({self._asset['model']})…",
        }))
        prompt = (
            "Asset:\n" + json.dumps({
                "id": self._asset["id"], "model": self._asset["model"],
                "criticality": self._asset["criticality"],
            }) +
            "\n\nTelemetry summary (5s samples):\n" + json.dumps(self._summary) +
            "\n\nClassify the failure and return ONLY the JSON object described in your instructions."
        )
        response = await self._agent.run(Message(role="user", contents=[prompt]))
        text = response.messages[-1].text if response.messages else ""
        try:
            diagnosis = _extract_json(text)
            assert isinstance(diagnosis, dict) and diagnosis.get("failure_mode")
        except Exception:
            diagnosis = _heuristic_diagnosis(self._asset, self._summary)
        self.diagnosis = diagnosis
        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "diagnosis_ready", "diagnosis": diagnosis,
        }))
        await ctx.send_message([Message(role="assistant", contents=[json.dumps(diagnosis)])])


class KnowledgeExecutor(Executor):
    """Step 2 — retrieve the SOP (our RAG) then the knowledge-agent cites it."""

    def __init__(self, agent, asset: Dict[str, Any], id: str = "knowledge"):
        self._agent = agent
        self._asset = asset
        self.sop: Dict[str, Any] = {}
        self.retrieved: List[Dict[str, Any]] = []
        super().__init__(id=id)

    @handler
    async def handle(self, messages: List[Message], ctx: WorkflowContext[None, List[Message]]) -> None:
        from agent_framework import WorkflowEvent
        try:
            diagnosis = _extract_json(messages[-1].text)
        except Exception:
            diagnosis = {}
        failure_mode = diagnosis.get("failure_mode", self._asset.get("failure_hint", ""))
        query = f"{self._asset['model']} {failure_mode} maintenance procedure"

        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "agent_log", "stage": "knowledge",
            "log": f"Retrieving SOP for failure mode '{failure_mode}' via {rag.backend_kind()}…",
        }))
        retrieved = rag.retrieve_sop(query, failure_mode=failure_mode, top_k=3)
        self.retrieved = retrieved
        top = retrieved[0] if retrieved else {}
        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "agent_log", "stage": "knowledge",
            "log": f"Top match: {top.get('doc_id', 'none')} — {top.get('section', '')} (score {top.get('score')})",
        }))

        snippets = "\n\n".join(
            f"[{r['doc_id']}] {r['title']} — section '{r['section']}' (source {r['source']}):\n{r['chunk']}"
            for r in retrieved
        )
        prompt = (
            f"Diagnosed failure mode: {failure_mode}.\n\n"
            f"Retrieved SOP passages:\n{snippets}\n\n"
            "Pick the single most relevant SOP and return ONLY the JSON object "
            "described in your instructions, citing the exact doc_id and source."
        )
        response = await self._agent.run(Message(role="user", contents=[prompt]))
        text = response.messages[-1].text if response.messages else ""
        try:
            sop = _extract_json(text)
            assert isinstance(sop, dict) and (sop.get("sop_id") or sop.get("doc_id"))
        except Exception:
            sop = {
                "sop_id": top.get("doc_id"), "title": top.get("title"),
                "citation": top.get("source"),
                "summary": (top.get("chunk", "")[:280]),
                "key_steps": [],
            }
        self.sop = sop
        await ctx.add_event(WorkflowEvent.emit(self.id, {
            "kind": "knowledge_ready", "sop": sop, "retrieved": retrieved,
        }))
        await ctx.yield_output([Message(role="assistant", contents=[json.dumps(sop)])])


# ============================================================================
#  Phase A orchestrator
# ============================================================================

async def orchestrate_diagnose(run_id: str, asset_id: str, mode: str) -> AsyncGenerator[Dict[str, Any], None]:
    """SSE async generator for the diagnose+retrieve phase. Ends awaiting approval."""
    seq = 0

    def ev(payload: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal seq
        seq += 1
        payload["run_id"] = run_id
        payload["seq"] = seq
        return payload

    try:
        asset = telemetry.get_asset(asset_id)
        series = telemetry.generate_series(asset_id, mode)
        summary = telemetry_summary(series)

        yield ev({"type": "anomaly_detected", "asset": asset, "summary": summary,
                  "message": f"Anomaly on {asset_id} — starting diagnosis workflow"})

        if not PROJECT_ENDPOINT:
            yield ev({"type": "error", "message": "PROJECT_ENDPOINT not configured — cannot reach Foundry"})
            return

        async with AsyncDefaultAzureCredential() as credential:
            diagnosis_agent = FoundryAgent(project_endpoint=PROJECT_ENDPOINT,
                                           agent_name=DIAGNOSIS_AGENT_NAME, credential=credential)
            knowledge_agent = FoundryAgent(project_endpoint=PROJECT_ENDPOINT,
                                           agent_name=KNOWLEDGE_AGENT_NAME, credential=credential)
            diag_exec = DiagnosisExecutor(diagnosis_agent, asset, summary)
            know_exec = KnowledgeExecutor(knowledge_agent, asset)
            workflow = (
                WorkflowBuilder(name="SignalToServiceDiagnose",
                                description="diagnosis-agent → knowledge-agent (RAG)",
                                start_executor=diag_exec)
                .add_edge(diag_exec, know_exec)
                .build()
            )

            yield ev({"type": "agent_start", "agent": "diagnosis",
                      "message": f"{DIAGNOSIS_AGENT_NAME} → {KNOWLEDGE_AGENT_NAME}"})

            diagnosis: Dict[str, Any] = {}
            sop: Dict[str, Any] = {}
            knowledge_started = False

            trigger = Message(role="user", contents=["Begin the signal-to-service pipeline."])
            async for event in workflow.run(trigger, stream=True):
                data = getattr(event, "data", None)
                if event.type == "data" and isinstance(data, dict) and "kind" in data:
                    kind = data["kind"]
                    if kind == "agent_log":
                        yield ev({"type": "agent_log", "agent": data["stage"], "message": data["log"]})
                    elif kind == "diagnosis_ready":
                        diagnosis = data["diagnosis"]
                        yield ev({"type": "diagnosis", "data": diagnosis})
                        yield ev({"type": "agent_done", "agent": "diagnosis"})
                        knowledge_started = True
                        yield ev({"type": "agent_start", "agent": "knowledge",
                                  "message": f"{KNOWLEDGE_AGENT_NAME} retrieving the SOP"})
                    elif kind == "knowledge_ready":
                        sop = data["sop"]
                        yield ev({"type": "knowledge", "data": sop, "retrieved": data.get("retrieved", [])})
                        yield ev({"type": "agent_done", "agent": "knowledge"})

            if not diagnosis:
                yield ev({"type": "error", "message": "Workflow ended without a diagnosis"})
                return
            if not knowledge_started:
                yield ev({"type": "agent_start", "agent": "knowledge", "message": "retrieving the SOP"})

        proposal = build_proposal(asset, diagnosis, sop)
        cmms.save_diagnosis(run_id, diagnosis, sop, proposal)
        yield ev({"type": "awaiting_approval", "proposal": proposal,
                  "message": "Human approval required before dispatching the work order"})
    except Exception as exc:  # pragma: no cover
        yield ev({"type": "error", "message": f"{exc.__class__.__name__}: {exc}"})


# ============================================================================
#  Phase B orchestrator (dispatch after approval)
# ============================================================================

async def orchestrate_dispatch(run_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    seq = 0

    def ev(payload: Dict[str, Any]) -> Dict[str, Any]:
        nonlocal seq
        seq += 1
        payload["run_id"] = run_id
        payload["seq"] = seq
        return payload

    try:
        run = cmms.get_run(run_id)
        if run is None:
            yield ev({"type": "error", "message": "unknown run"})
            return
        if run.get("decision") != "approve":
            yield ev({"type": "error", "message": "run is not approved — cannot dispatch"})
            return

        # Idempotency: if already dispatched, replay the existing work order.
        if run.get("work_order_id"):
            wo = cmms.get_work_order(run["work_order_id"])
            yield ev({"type": "agent_log", "agent": "action",
                      "message": f"Work order {run['work_order_id']} already exists — replaying"})
            yield ev({"type": "work_order", "data": wo})
            yield ev({"type": "done"})
            return

        asset = telemetry.get_asset(run["asset_id"])
        diagnosis = run.get("diagnosis") or {}
        sop = run.get("sop") or {}
        proposal = run.get("proposal") or {}

        yield ev({"type": "agent_start", "agent": "action",
                  "message": f"{ACTION_AGENT_NAME} preparing the work order"})

        summary_text = proposal.get("title", "Maintenance work order")
        if PROJECT_ENDPOINT:
            try:
                async with AsyncDefaultAzureCredential() as credential:
                    action_agent = FoundryAgent(project_endpoint=PROJECT_ENDPOINT,
                                                agent_name=ACTION_AGENT_NAME, credential=credential)
                    prompt = (
                        "Draft a concise (max 3 sentences) maintenance work-order summary for a "
                        "technician, given:\n"
                        f"asset: {json.dumps({'id': asset['id'], 'model': asset['model'], 'location': asset['location']})}\n"
                        f"diagnosis: {json.dumps(diagnosis)}\n"
                        f"sop: {json.dumps({k: sop.get(k) for k in ('sop_id', 'doc_id', 'title', 'citation')})}\n"
                        "Return plain text only."
                    )
                    resp = await action_agent.run(Message(role="user", contents=[prompt]))
                    if resp.messages and resp.messages[-1].text.strip():
                        summary_text = resp.messages[-1].text.strip()
                yield ev({"type": "agent_log", "agent": "action", "message": "Work-order summary drafted"})
            except Exception as exc:
                yield ev({"type": "agent_log", "agent": "action",
                          "message": f"Agent summary skipped ({exc.__class__.__name__}); using proposal title"})

        required_skill = proposal.get("required_skill") or asset.get("required_skill", "mechanical")
        assignment = scheduler.assign_technician(required_skill)
        yield ev({"type": "agent_log", "agent": "action",
                  "message": (f"Scheduled {assignment['technician']} "
                              f"({'skill match' if assignment['skill_matched'] else 'nearest available'}) "
                              f"for {assignment['scheduled_for']}")})

        wo = cmms.create_work_order(
            run_id=run_id,
            asset_id=asset["id"],
            title=proposal.get("title", "Maintenance work order"),
            priority=proposal.get("priority", "P2"),
            sop_id=proposal.get("sop_id"),
            technician=assignment["technician"],
            scheduled_for=assignment["scheduled_for"],
            summary=summary_text,
        )
        wo["assignment"] = assignment
        yield ev({"type": "agent_log", "agent": "action", "message": f"Created {wo['work_order_id']} in CMMS"})
        yield ev({"type": "work_order", "data": wo})
        yield ev({"type": "agent_done", "agent": "action"})
        yield ev({"type": "done"})
    except Exception as exc:  # pragma: no cover
        yield ev({"type": "error", "message": f"{exc.__class__.__name__}: {exc}"})
