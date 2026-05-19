"""Reviewer-facing upload dashboard for Foundry document triage."""

from __future__ import annotations

import socket
import threading
import time
import urllib.request
from typing import Any, Protocol

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
from jinja2 import Environment, select_autoescape

from agentverse.contracts import AnalyzerKind, TriageResult, UploadedDocumentRequest
from agentverse.foundry_service import FoundryTriageService


class UploadTriageService(Protocol):
    def run_upload(self, request: UploadedDocumentRequest) -> TriageResult:
        ...


ACTION_LABELS = {
    "approve": "Recommend approval for human review",
    "reject": "Recommend rejection for human review",
    "hold": "Hold and escalate before releasing funds",
    "escalate": "Escalate to a human specialist",
    "summarize": "Summarize for clinician review",
    "prescribe_for_review": "Send prescription to clinician for review",
    "buy": "Review replenishment purchase",
    "ship_immediately": "Ship matching orders immediately",
    "store_in_inventory": "Store units in inventory",
    "consolidate_shipment": "Consolidate client shipment",
    "release_reserved_stock": "Review reserved-stock release",
    "dispute_supplier_document": "Dispute or correct supplier document",
    "accept_delivery": "Accept after standard review",
    "partially_accept_delivery": "Partially accept after review",
    "request_partial_fulfillment": "Request partial fulfillment and escalate shortage",
    "unknown": "No strategy available",
}

RISK_CLASS = {
    "low": "good",
    "medium": "warn",
    "high": "danger",
    "critical": "critical",
    "not_applicable": "muted",
}

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AgentVerse Review Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #172033;
      --muted: #667085;
      --line: #d9e0ec;
      --primary: #3457d5;
      --good: #027a48;
      --warn: #b54708;
      --danger: #b42318;
      --critical: #7a271a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      color: var(--text);
      background: linear-gradient(180deg, #eef3ff 0, var(--bg) 360px);
    }
    header, main { max-width: 1180px; margin: 0 auto; padding: 28px; }
    .hero { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; }
    h1 { font-size: 34px; margin: 0 0 8px; }
    p { line-height: 1.5; }
    a { color: var(--primary); font-weight: 600; }
    .muted { color: var(--muted); }
    .panel {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 12px 35px rgba(24, 39, 75, 0.08);
      padding: 22px;
    }
    form {
      display: grid;
      grid-template-columns: minmax(260px, 1fr) auto;
      gap: 14px;
      align-items: end;
      margin-top: 18px;
    }
    label { display: grid; gap: 7px; font-weight: 600; }
    input, select, button {
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      font: inherit;
      background: #fff;
    }
    button {
      border-color: var(--primary);
      color: #fff;
      background: var(--primary);
      cursor: pointer;
      font-weight: 700;
    }
    .grid { display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 18px; margin-top: 18px; }
    .cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
    .metric { border: 1px solid var(--line); border-radius: 16px; padding: 16px; background: #fff; }
    .metric span { display: block; color: var(--muted); font-size: 13px; margin-bottom: 8px; }
    .metric strong { font-size: 18px; }
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 6px 10px;
      font-weight: 700;
      background: #eef4ff;
      color: #3538cd;
    }
    .good { color: var(--good); background: #ecfdf3; }
    .warn { color: var(--warn); background: #fffaeb; }
    .danger { color: var(--danger); background: #fef3f2; }
    .critical { color: #fff; background: var(--critical); }
    .muted-badge { color: var(--muted); background: #f2f4f7; }
    ul { padding-left: 20px; }
    li { margin: 8px 0; }
    .evidence {
      border-left: 4px solid #c7d7fe;
      padding: 10px 12px;
      margin: 10px 0;
      background: #f8faff;
      border-radius: 10px;
    }
    .details { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .detail { border: 1px solid var(--line); border-radius: 12px; padding: 12px; background: #fcfcfd; }
    .detail span { color: var(--muted); display: block; font-size: 12px; margin-bottom: 4px; }
    pre {
      white-space: pre-wrap;
      background: #101828;
      color: #e4e7ec;
      padding: 14px;
      border-radius: 12px;
      overflow: auto;
    }
    @media (max-width: 900px) {
      .hero, .grid { grid-template-columns: 1fr; display: grid; }
      form, .cards, .details { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="hero">
      <div>
        <h1>Document triage reviewer dashboard</h1>
        <p class="muted">Upload a supported document or image. Content Understanding extracts the content, the intake agent decides the route, and the selected Foundry specialist recommends the review strategy.</p>
        <p><span class="badge" data-testid="agent-mode">Mode: {{ agent_mode }}</span></p>
      </div>
      <p><a href="{{ devui_url }}" target="_blank" rel="noopener">Open DevUI traces</a></p>
    </div>
    <section class="panel">
      <form action="/analyze" method="post" enctype="multipart/form-data">
        <label>
          Document or image
          <input name="file" data-testid="file-input" type="file" required accept=".pdf,.tif,.tiff,.jpg,.jpeg,.jpe,.png,.bmp,.heif,.heic,.docx,.xlsx,.pptx,.txt,.html,.htm,.md,.rtf,.eml,.msg,.xml">
        </label>
        <button type="submit">Analyze upload</button>
      </form>
      <p class="muted">You no longer choose the case or route. The intake agent decides whether the file belongs to financial, medical, supply, or manual review.</p>
    </section>
  </header>
  <main>
    {% if error %}
      <section class="panel">
        <h2>Analysis could not run</h2>
        <p data-testid="error">{{ error }}</p>
      </section>
    {% elif result %}
      <section class="panel">
        <span class="badge {{ result.risk_class }}" data-testid="risk">{{ result.risk }}</span>
        <h2 data-testid="recommended-action">{{ result.strategy }}</h2>
        <p data-testid="reasoning">{{ result.reasoning }}</p>
        <div class="cards">
          <div class="metric"><span>Route</span><strong data-testid="route">{{ result.route }}</strong></div>
          <div class="metric"><span>Document</span><strong>{{ result.document_type }} / {{ result.document_subtype }}</strong></div>
          <div class="metric"><span>Status</span><strong>{{ result.status }}</strong></div>
          <div class="metric"><span>Confidence</span><strong>{{ result.confidence }}</strong></div>
        </div>
      </section>

      <div class="grid">
        <section class="panel">
          <h2>Relevant case details</h2>
          <div class="details">
            {% for detail in result.case_details %}
              <div class="detail"><span>{{ detail.label }}</span>{{ detail.value }}</div>
            {% endfor %}
          </div>

          {% if result.quality_warnings %}
            <h3>Quality warnings</h3>
            <ul>
              {% for warning in result.quality_warnings %}
                <li>{{ warning }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        </section>

        <section class="panel">
          <h2>Next steps for the reviewer</h2>
          <ul data-testid="next-steps">
            {% for step in result.next_steps %}
              <li>{{ step }}</li>
            {% endfor %}
          </ul>
          {% if result.missing_information %}
            <h3>Missing information</h3>
            <ul>
              {% for item in result.missing_information %}
                <li>{{ item }}</li>
              {% endfor %}
            </ul>
          {% endif %}
        </section>
      </div>

      <section class="panel" style="margin-top: 18px;">
        <h2>Evidence used for the strategy</h2>
        {% for item in result.evidence %}
          <div class="evidence">
            <strong>{{ item.source }}</strong>
            <p>{{ item.detail }}</p>
            {% if item.value_summary %}
              <p class="muted">{{ item.value_summary }}</p>
            {% endif %}
          </div>
        {% endfor %}
      </section>

      <section class="panel" style="margin-top: 18px;">
        <h2>Trace/debug handoff</h2>
        <p class="muted">Foundry/OpenAI SDK spans are exported to the connected Application Insights resource. DevUI accepts a local file path for replay:</p>
        <pre data-testid="trace-json">{{ result.trace_json }}</pre>
      </section>
    {% else %}
      <section class="panel">
        <h2>Upload a file to start</h2>
        <p class="muted">Supported samples include the fabricated PNG documents in <code>data\\fabricated_documents</code>. The route is no longer user-selected.</p>
      </section>
    {% endif %}
  </main>
</body>
</html>
"""

_ENV = Environment(autoescape=select_autoescape(["html", "xml"]))
_TEMPLATE = _ENV.from_string(HTML_TEMPLATE)


def create_review_dashboard_app(
    devui_url: str = "http://127.0.0.1:8080",
    agent_mode: str = "foundry-tools",
    service: UploadTriageService | None = None,
) -> FastAPI:
    app = FastAPI(title="AgentVerse Review Dashboard")
    triage_service = service or FoundryTriageService()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return render_review_page(devui_url=devui_url, agent_mode=agent_mode)

    @app.post("/analyze", response_class=HTMLResponse)
    async def analyze(
        file: UploadFile = File(...),
    ) -> str:
        try:
            content = await file.read()
            request = UploadedDocumentRequest(
                filename=file.filename or "upload.bin",
                content_type=file.content_type or "application/octet-stream",
                content_bytes=content,
                analyzer_kind=AnalyzerKind.AUTO,
                metadata={},
            )
            result = triage_service.run_upload(request)
            return render_review_page(
                result=result,
                devui_url=devui_url,
                agent_mode=agent_mode,
            )
        except Exception as exc:
            return render_review_page(
                error=str(exc),
                devui_url=devui_url,
                agent_mode=agent_mode,
            )

    return app


def render_review_page(
    result: TriageResult | None = None,
    error: str | None = None,
    devui_url: str = "http://127.0.0.1:8080",
    agent_mode: str = "foundry-tools",
) -> str:
    return _TEMPLATE.render(
        result=build_review_view_model(result) if result else None,
        error=error,
        devui_url=devui_url,
        agent_mode=agent_mode,
    )


def build_review_view_model(result: TriageResult) -> dict[str, Any]:
    context = result.context
    recommendation = result.recommendation
    action = str(recommendation.recommended_action)
    risk = str(recommendation.risk_level)
    return {
        "strategy": ACTION_LABELS.get(action, action.replace("_", " ").title()),
        "risk": risk.replace("_", " ").title(),
        "risk_class": RISK_CLASS.get(risk, "muted-badge"),
        "status": str(recommendation.decision_status).replace("_", " ").title(),
        "route": str(context.route).replace("_", " ").title(),
        "document_type": str(context.document_type).replace("_", " ").title(),
        "document_subtype": context.document_subtype.replace("_", " ").title(),
        "confidence": f"{context.classification_confidence:.0%}",
        "reasoning": recommendation.reasoning_summary,
        "case_details": _case_details(result),
        "quality_warnings": [warning.replace("_", " ") for warning in context.quality_warnings],
        "next_steps": recommendation.next_steps,
        "missing_information": recommendation.missing_information,
        "evidence": [
            {
                "source": item.source.replace("_", " ").title(),
                "detail": item.detail,
                "value_summary": _compact_values(item.values),
            }
            for item in recommendation.evidence
        ],
        "trace_json": _devui_replay_json(context.fields),
    }


def _case_details(result: TriageResult) -> list[dict[str, str]]:
    context = result.context
    fields = context.fields
    base_details = [
        {"label": "Uploaded file", "value": str(fields.get("source_filename", context.source_uri))},
        {"label": "Analyzer", "value": str(fields.get("content_understanding_analyzer", "n/a"))},
    ]
    if context.document_subtype == "credit_application":
        return base_details + [
            {"label": "Requested amount", "value": f"{fields.get('requested_amount_eur', 'n/a')} EUR"},
            {"label": "Requested term", "value": f"{fields.get('requested_term_months', 'n/a')} months"},
            {"label": "Declared income", "value": f"{fields.get('declared_income_eur', 'n/a')} EUR"},
            {"label": "Attached documents", "value": ", ".join(fields.get("attached_documents", [])) or "n/a"},
        ]
    if context.document_subtype == "withdrawal_order":
        return base_details + [
            {"label": "Requested amount", "value": f"{fields.get('requested_amount_eur', 'n/a')} EUR"},
            {"label": "Location", "value": str(fields.get("location", "n/a"))},
            {"label": "Date/time", "value": str(fields.get("requested_datetime", "n/a"))},
            {"label": "Account", "value": str(fields.get("account_id", "n/a"))},
        ]
    if context.document_subtype in {"clinical_note", "prescription"}:
        medication_names = [
            str(medication.get("name"))
            for medication in fields.get("medications", [])
            if isinstance(medication, dict) and medication.get("name")
        ]
        return base_details + [
            {"label": "Patient", "value": str(fields.get("patient_id", "n/a"))},
            {"label": "Symptoms", "value": _format_symptoms(fields)},
            {"label": "Vitals", "value": _compact_values(fields.get("vitals", {})) or "n/a"},
            {"label": "Medications", "value": ", ".join(medication_names) or "n/a"},
        ]
    if context.document_subtype in {"shipment_notice", "supply_request", "inventory_balance", "receiving_sheet"}:
        return base_details + [
            {"label": "Destination", "value": str(fields.get("destination", "n/a"))},
            {"label": "Required date", "value": str(fields.get("required_date", "n/a"))},
            {"label": "Supplier", "value": str(fields.get("supplier", "n/a"))},
            {"label": "Items", "value": _format_items(fields.get("items", []))},
        ]
    if context.document_subtype in {"invoice", "packing_slip", "delivery_note"}:
        return base_details + [
            {"label": "Invoice", "value": str(fields.get("invoice_id", "n/a"))},
            {"label": "Purchase order", "value": str(fields.get("purchase_order_id", "n/a"))},
            {"label": "Supplier", "value": str(fields.get("supplier", "n/a"))},
            {"label": "Items", "value": _format_items(fields.get("items", []))},
        ]
    return base_details + [
        {"label": "Detected subtype", "value": context.document_subtype.replace("_", " ").title()},
        {"label": "Source", "value": context.source_uri},
        {"label": "Readable text", "value": context.extracted_text[:160]},
    ]


def _format_items(items: list[dict[str, Any]]) -> str:
    formatted = []
    for item in items:
        product_id = item.get("product_id", "item")
        quantity = item.get("quantity", "n/a")
        price = item.get("unit_price_eur")
        suffix = f" at {price} EUR" if price is not None else ""
        formatted.append(f"{product_id} x {quantity}{suffix}")
    return "; ".join(formatted) or "n/a"


def _format_symptoms(fields: dict[str, Any]) -> str:
    symptoms = fields.get("symptoms")
    if isinstance(symptoms, list) and symptoms:
        return ", ".join(str(symptom) for symptom in symptoms if symptom)
    if isinstance(symptoms, str) and symptoms.strip():
        return symptoms
    for key in ("chief_complaint", "presenting_complaint", "clinical_findings", "history", "reason_for_visit"):
        value = fields.get(key)
        if isinstance(value, list) and value:
            return ", ".join(str(item) for item in value if item)
        if isinstance(value, str) and value.strip():
            return value
    return "n/a"


def _compact_values(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, dict):
        return "; ".join(f"{key}: {value}" for key, value in values.items())
    if isinstance(values, list):
        return "; ".join(str(value) for value in values)
    return str(values)


def _devui_replay_json(fields: dict[str, Any]) -> str:
    filename = fields.get("source_filename", "upload.pdf")
    return (
        "{\n"
        f'  "file_path": "C:\\\\Demos offline\\\\AgentVerse\\\\data\\\\fabricated_documents\\\\{filename}"\n'
        "}"
    )


def start_review_dashboard(
    host: str = "127.0.0.1",
    preferred_port: int = 8081,
    devui_url: str = "http://127.0.0.1:8080",
    agent_mode: str = "foundry-tools",
) -> str:
    port = _choose_available_port(host, preferred_port)
    app = create_review_dashboard_app(devui_url=devui_url, agent_mode=agent_mode)
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.config.install_signal_handlers = lambda: None
    thread = threading.Thread(target=server.run, name="agentverse-review-dashboard", daemon=True)
    thread.start()
    url = f"http://{host}:{port}"
    _wait_until_ready(f"{url}/healthz")
    return url


def _choose_available_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 5):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f"No available reviewer dashboard port found from {preferred_port} to {preferred_port + 4}.")


def _wait_until_ready(url: str, timeout_seconds: float = 5.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if response.status == 200:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Reviewer dashboard did not become ready at {url}: {last_error}")
