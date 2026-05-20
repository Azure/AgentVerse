# AgentVerse hosted workflow explained

This document explains how the local dashboard and the hosted Foundry workflow run the same AgentVerse document triage process.

## High-level flow

```text
User upload
  -> Azure Content Understanding
  -> AgentVerseIntakeAgent
  -> History snapshot from SQLite
  -> Route-specific specialist agent
  -> Human-review recommendation
```

| Step | Code path | Method | What it does |
| --- | --- | --- | --- |
| Local dashboard upload | `agentverse\review_dashboard.py` | `create_review_dashboard_app(...).analyze(...)` | Reads the browser upload and creates an `UploadedDocumentRequest`. |
| Hosted file upload | `hostedagent\scripts\upload_to_hosted_workflow.py` | `_upload_file(...)` | Writes a local file into a hosted session path such as `/uploads/shipment_request.png`. |
| Hosted workflow tool | `hostedagent\hosted_workflow.py` | `analyze_uploaded_file(file_path)` | Reads the session file and calls the same `FoundryTriageService.run_upload(...)` used by the dashboard. |
| Content extraction | `agentverse\content_understanding.py` | `ContentUnderstandingClient.analyze_upload(...)` | Chooses `prebuilt-imageSearch` or `prebuilt-documentSearch`, sends bytes to Content Understanding, and normalizes the result. |
| Intake routing | `agentverse\foundry_service.py` | `FoundryTriageService.intake_upload(...)` | Sends Content Understanding evidence to `AgentVerseIntakeAgent`; receives route, subtype, confidence, warnings, and normalized fields. |
| Specialist recommendation | `agentverse\foundry_service.py` | `FoundryTriageService.recommend(...)` | Builds the relevant SQLite history snapshot and sends the case to the selected specialist agent. |
| Prompt-agent definitions | `agentverse\foundry_definitions.py` | `AGENT_INSTRUCTIONS` | Defines each prompt agent's expected input and JSON output contract. |

## Local dashboard entrypoint

Path: `agentverse\review_dashboard.py`

Method: `create_review_dashboard_app(...).analyze(...)`

```python
@app.post("/analyze", response_class=HTMLResponse)
async def analyze(file: UploadFile = File(...)) -> str:
    # 1. Read the exact bytes uploaded from the browser.
    content = await file.read()

    # 2. Wrap the upload in the same request contract used by hosted mode.
    request = UploadedDocumentRequest(
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        content_bytes=content,
        analyzer_kind=AnalyzerKind.AUTO,
        metadata={},
    )

    # 3. Run the full shared workflow: Content Understanding -> intake -> specialist.
    result = triage_service.run_upload(request)

    # 4. Render the human-review dashboard.
    return render_review_page(result=result, ...)
```

**Input:** browser multipart file upload.

**Output:** rendered dashboard HTML with route, risk, recommended action, evidence, and next steps.

## Hosted workflow entrypoint

Path: `hostedagent\hosted_workflow.py`

Method: `main()`

```python
async def main() -> None:
    # Hosted containers use managed identity, not local Azure CLI.
    os.environ["AGENTVERSE_USE_DEFAULT_AZURE_CREDENTIAL"] = "1"
    credential = DefaultAzureCredential()

    # The hosted wrapper uses FoundryChatClient so the workflow can be exposed
    # through Foundry's hosted Responses protocol.
    client = FoundryChatClient(
        project_endpoint=os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
            or os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
            or PROJECT_ENDPOINT,
        model=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", MODEL_DEPLOYMENT_NAME),
        credential=credential,
    )

    # These tools are what the hosted agent can call from chat.
    async with Agent(
        client=client,
        instructions="...",
        tools=[analyze_uploaded_file, list_uploaded_files],
        default_options={"store": False},
    ) as agent:
        await ResponsesHostServer(agent).run_async()
```

**Input:** Foundry hosted Responses API messages.

**Output:** normal chat response, usually produced after the agent calls `analyze_uploaded_file(...)`.

### Hosted tool: analyze an uploaded file

Path: `hostedagent\hosted_workflow.py`

Method: `analyze_uploaded_file(file_path)`

```python
@tool(...)
def analyze_uploaded_file(file_path: str) -> str:
    # 1. Convert a user path such as "/uploads/case.png" into an actual file
    # under the hosted session filesystem, usually /home/session/uploads/case.png.
    path = _resolve_uploaded_path(file_path)

    # 2. Read the file bytes and use AUTO analyzer selection.
    request = UploadedDocumentRequest(
        filename=path.name,
        content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        content_bytes=path.read_bytes(),
        analyzer_kind=AnalyzerKind.AUTO,
        metadata={"source": "foundry_hosted_workflow"},
    )

    # 3. Reuse the same core service as the local dashboard.
    result = _workflow_service().run_upload(request)

    # 4. Format the structured triage result into readable text for Foundry chat.
    return format_triage_result(result)
```

**Input:** a hosted session file path, for example `/uploads/shipment_request.png`.

**Output:** a formatted final triage result for the Foundry chat.

### Hosted tool: list uploaded files

Path: `hostedagent\hosted_workflow.py`

Method: `list_uploaded_files()`

```python
def list_uploaded_files() -> list[str]:
    files = []
    seen = set()

    # Only scan documented hosted-session roots, not the whole container.
    for root in _upload_roots():
        for path in _iter_supported_files(root):
            ...
            files.append(str(label).replace("\\", "/"))

    return sorted(files)
```

**Input:** none.

**Output:** relative file names that the user can ask the workflow to analyze.

## Content Understanding step

Path: `agentverse\content_understanding.py`

Method: `ContentUnderstandingClient.analyze_upload(...)`

```python
def analyze_upload(self, request: UploadedDocumentRequest) -> ContentUnderstandingResult:
    # 1. Reject empty, too-large, or unsupported files.
    self._validate_upload(request)

    # 2. Choose prebuilt-imageSearch for image extensions/content types,
    # otherwise choose prebuilt-documentSearch for PDFs/docs/text.
    analyzer_id = self._select_analyzer(
        request.filename,
        request.content_type,
        request.analyzer_kind,
    )

    # 3. Send the raw upload bytes to Content Understanding.
    result = self._analyze_binary(analyzer_id, request)

    # 4. If imageSearch returns a sparse document-like result, rerun with
    # documentSearch so scanned document images still produce useful text.
    if analyzer_id == IMAGE_SEARCH_ANALYZER and self._should_fallback_to_document_search(result):
        fallback = self._analyze_binary(DOCUMENT_SEARCH_ANALYZER, request)
        fallback.warnings.append(...)
        return fallback

    return result
```

**Input:** `UploadedDocumentRequest` with `filename`, `content_type`, and `content_bytes`.

**Output:** `ContentUnderstandingResult` containing analyzer id, markdown/text, summary, fields, tables, pages, warnings, and citations.

## Intake agent step

Path: `agentverse\foundry_service.py`

Method: `FoundryTriageService.intake_upload(...)`

```python
def intake_upload(self, request: UploadedDocumentRequest) -> DocumentContext:
    # 1. Extract document/image contents with Azure Content Understanding.
    content = self._content_client.analyze_upload(request)

    # 2. Build a compact summary so the prompt agent is grounded but not flooded.
    analyzer_context = _build_analyzer_context(content)

    # 3. Build the exact payload sent to AgentVerseIntakeAgent.
    intake_payload = {
        "source": "azure_content_understanding",
        "file": {
            "document_id": content.document_id,
            "filename": content.filename,
            "content_type": content.content_type,
            "requested_analyzer_kind": str(request.analyzer_kind),
        },
        "content_understanding_summary": analyzer_context,
        "content_understanding_evidence": {
            "markdown_excerpt": content.markdown[:4000],
            "fields": content.fields,
            "tables": content.tables[:5],
            "pages": _compact_pages(content.pages),
            "source_citations": [...],
        },
    }

    # 4. Invoke the Foundry prompt agent by reference.
    intake_response = self._invoke_json(AGENT_NAMES["intake"], intake_payload)

    # 5. Convert the intake JSON into the common DocumentContext contract.
    return DocumentContext(...)
```

**Agent called:** `AgentVerseIntakeAgent`

**Input received by intake agent:**

```json
{
  "source": "azure_content_understanding",
  "file": {
    "document_id": "...",
    "filename": "...",
    "content_type": "...",
    "requested_analyzer_kind": "auto"
  },
  "content_understanding_summary": {
    "analyzer_id": "prebuilt-imageSearch or prebuilt-documentSearch",
    "summary": "...",
    "warnings": []
  },
  "content_understanding_evidence": {
    "markdown_excerpt": "...",
    "fields": {},
    "tables": [],
    "pages": [],
    "source_citations": []
  }
}
```

**Output produced by intake agent:**

```json
{
  "document_type": "financial|medical|supply|unknown",
  "document_subtype": "credit_application|withdrawal_order|clinical_note|prescription|shipment_notice|invoice|packing_slip|inventory_balance|receiving_sheet|unknown",
  "route": "financial|medical|supply|manual_review",
  "classification_confidence": 0.0,
  "quality_warnings": [],
  "reasoning_summary": "brief routing reason",
  "extracted_fields": {}
}
```

## Specialist agent step

Path: `agentverse\foundry_service.py`

Method: `FoundryTriageService.recommend(...)`

```python
def recommend(self, context: DocumentContext) -> TriageResult:
    # 1. Pull only the relevant historical records for the selected route.
    snapshot = self._snapshots.build(context)

    # 2. Select the specialist agent from the intake route.
    specialist_agent = AGENT_NAMES.get(context.route, AGENT_NAMES["manual_review"])

    # 3. Give the specialist the normalized document, the analyzer grounding,
    # and the route-specific SQLite history.
    recommendation_payload = {
        "document_context": context.model_dump(mode="json"),
        "analyzer_context": context.analyzer_context,
        "history_snapshot": snapshot,
        "safety_instruction": "Return recommendation JSON only. The human reviewer executes any final action.",
    }

    # 4. Invoke the selected prompt agent and validate its JSON output.
    recommendation_json = self._invoke_json(specialist_agent, recommendation_payload)
    recommendation = AgentRecommendation.model_validate(recommendation_json)

    return TriageResult(...)
```

**Input received by every specialist agent:**

```json
{
  "document_context": {
    "document_id": "...",
    "document_type": "financial|medical|supply|unknown",
    "document_subtype": "...",
    "route": "...",
    "extracted_text": "...",
    "fields": {},
    "analyzer_context": {},
    "tables": [],
    "source_citations": []
  },
  "analyzer_context": {},
  "history_snapshot": {},
  "safety_instruction": "Return recommendation JSON only. The human reviewer executes any final action."
}
```

**Output produced by every specialist agent:**

```json
{
  "recommended_action": "...",
  "decision_status": "ready_for_review|needs_human_review|blocked_missing_data|unsupported_document",
  "risk_level": "low|medium|high|critical|not_applicable",
  "reasoning_summary": "concise explanation",
  "evidence": [{"source": "...", "detail": "...", "values": {}}],
  "missing_information": [],
  "next_steps": []
}
```

## Route-specific specialist behavior

Path: `agentverse\foundry_definitions.py`

### `AgentVerseFinancialAgent`

Receives: `document_context`, `analyzer_context`, and a financial history snapshot built from:

Path: `agentverse\history_snapshots.py`

Method: `HistorySnapshotBuilder._financial_snapshot(...)`

```python
# Uses customer/account identifiers from intake-normalized fields.
customer_id = str(fields.get("customer_id", ""))
account_id = str(fields.get("account_id", ""))

# Pulls customer profile, account, credit products, and recent transactions.
transactions = self._many(... LIMIT 60 ...)
```

Produces: recommendation JSON for credit or withdrawal review. It can recommend `approve`, `reject`, `hold`, or `escalate`, but it never executes the financial action.

### `AgentVerseMedicalAgent`

Receives: `document_context`, `analyzer_context`, and a patient history snapshot built from:

Path: `agentverse\history_snapshots.py`

Method: `HistorySnapshotBuilder._medical_snapshot(...)`

```python
# Uses patient_id extracted by the intake agent.
patient_id = str(context.fields.get("patient_id", ""))

# Pulls patient profile, conditions, allergies, medications, and recent clinical events.
events = self._many(... LIMIT 18 ...)
```

Produces: clinical decision-support JSON. It can summarize, flag a prescription for doctor review, or escalate. It does not diagnose or prescribe.

### `AgentVerseSupplyAgent`

Receives: `document_context`, `analyzer_context`, and a supply snapshot built from:

Path: `agentverse\history_snapshots.py`

Method: `HistorySnapshotBuilder._supply_snapshot(...)`

```python
# Uses supplier, purchase order, and product IDs from intake-normalized fields.
supplier_name = str(fields.get("supplier", ""))
purchase_order_id = str(fields.get("purchase_order_id", ""))
item_ids = [str(item.get("product_id")) for item in fields.get("items", [])]

# Pulls inventory, reservations, recent demand, recent supply, and pending to-send matches.
"to_send_matches": self._many(... WHERE o.product_id = ? AND o.status = 'pending' ...)
```

Produces: warehouse/procurement recommendation JSON. It can recommend `ship_immediately`, `store_in_inventory`, `consolidate_shipment`, `dispute_supplier_document`, and related review actions.

### `AgentVerseManualReviewAgent`

Receives: `document_context`, `analyzer_context`, and a simple note saying no specialized history is available.

Produces: escalation JSON explaining why a human must inspect the upload manually.

## How Foundry prompt agents are called

Path: `agentverse\foundry_service.py`

Method: `FoundryTriageService._invoke_json(...)`

```python
def _invoke_json(self, agent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = self._openai_client.responses.create(
        model=self._model,

        # The prompt-agent payload is JSON text.
        input=json.dumps(payload, ensure_ascii=False),

        # This tells Foundry which prompt agent should receive the payload.
        extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
    )

    # Prompt agents are instructed to return JSON only.
    text = response.output[0].content[0].text
    return _extract_json(text)
```

If a prompt agent returns malformed JSON, `_repair_json_response(...)` asks the model to convert the same response into valid JSON without adding new facts.

## How hosted session upload works

Path: `hostedagent\scripts\upload_to_hosted_workflow.py`

Method: `main()`

```python
def main() -> None:
    # 1. Resolve the local file on your machine.
    local_file = args.file.resolve()

    # 2. Choose the hosted session path. By default:
    #    data\fabricated_documents\shipment_request.png -> /uploads/shipment_request.png
    remote_path = args.remote_path or f"/uploads/{local_file.name}"

    # 3. Get a token for the Foundry hosted-agent endpoint.
    token = AzureCliCredential().get_token(TOKEN_SCOPE).token

    # 4. Create a session only if the caller did not provide --session-id.
    session_id = args.session_id or _create_session(...)

    # 5. Upload bytes to that exact session.
    _upload_file(..., session_id=session_id, remote_path=remote_path)

    # 6. If --invoke is present, call the workflow against the same session.
    _invoke_agent(..., session_id=session_id, prompt=f"Analyze {remote_path} ...")
```

Method: `_upload_file(...)`

```python
def _upload_file(..., session_id: str, local_file: Path, remote_path: str) -> dict[str, Any]:
    # Foundry file paths are URL-encoded query parameters.
    encoded_path = urllib.parse.quote(remote_path, safe="")

    # This is the hosted-session file content endpoint.
    url = (
        f"{project_endpoint}/agents/{agent_name}/endpoint/sessions/{session_id}"
        f"/files/content?api-version=v1&path={encoded_path}"
    )

    # PUT writes the local file bytes into /home/session/uploads/<file>
    # inside that hosted session.
    return _request_json(..., method="PUT", body=local_file.read_bytes(), ...)
```

Method: `_invoke_agent(...)`

```python
def _invoke_agent(..., session_id: str | None, prompt: str, timeout: int) -> dict[str, Any]:
    payload = {"model": agent_name, "input": prompt, "stream": False}

    # This is the key field: it forces the response request to reuse the same
    # session that already contains the uploaded file.
    if session_id:
        payload["agent_session_id"] = session_id

    return _request_json(..., method="POST", body=json.dumps(payload).encode("utf-8"), ...)
```

Run it:

```powershell
python hostedagent\scripts\upload_to_hosted_workflow.py data\fabricated_documents\shipment_request.png --invoke
```

To reuse an existing session instead of creating a new one:

```powershell
python hostedagent\scripts\upload_to_hosted_workflow.py data\fabricated_documents\shipment_request.png --session-id <existing_agent_session_id> --invoke
```

## Why two sessions appeared in Foundry

The helper creates exactly **one** session per run when `--session-id` is not provided:

1. `_create_session(...)` sends one `/responses` call without `agent_session_id`.
2. Foundry creates one hosted session and returns `agent_session_id`.
3. `_upload_file(...)` writes the file into that returned session.
4. `_invoke_agent(...)` includes the same `agent_session_id`, so it reuses the session.

If you saw two sessions in Foundry, the second session came from a separate session-creating action, such as:

- running the helper twice without `--session-id`;
- sending a portal/playground chat message before or after the helper;
- using the Code/REST tab without including `"agent_session_id": "<same id>"`;
- testing the agent with a simple "ready" prompt, which creates a new session if no session id is supplied.

To avoid extra sessions, reuse the printed session id:

```json
{
  "model": "AgentVerseWorkflowAgent",
  "input": "Analyze /uploads/shipment_request.png and run the full AgentVerse workflow.",
  "stream": false,
  "agent_session_id": "<same id printed by the helper>"
}
```

## Hosted-agent files after reorganization

Hosted-specific files live under `hostedagent\`:

| Path | Purpose |
| --- | --- |
| `hostedagent\hosted_workflow.py` | Hosted Responses entrypoint and tools. |
| `hostedagent\Dockerfile` | Container image definition. Build from repo root with `--file hostedagent\Dockerfile .`. |
| `hostedagent\requirements-hosted.txt` | Minimal hosted-container dependencies. |
| `hostedagent\agent.yaml` | Hosted-agent manifest for tooling/extension workflows. |
| `hostedagent\agent.manifest.yaml` | Human-readable hosted-agent metadata. |
| `hostedagent\scripts\deploy_workflow_agent.py` | Creates a new Foundry hosted-agent version from `hostedagent\.foundry\workflow-image.json`. |
| `hostedagent\scripts\upload_to_hosted_workflow.py` | Uploads local files to hosted session storage and optionally invokes the workflow. |
| `hostedagent\.foundry\workflow-image.json` | Last built ACR image tag. |
| `hostedagent\.foundry\workflow-agent.json` | Last created hosted-agent version. |

Build and deploy after changing hosted code:

```powershell
$tag = Get-Date -Format 'yyyyMMddHHmmss'
rtk az acr build --registry acragentverse814702 --image "agentverse-workflow:$tag" --platform linux/amd64 --source-acr-auth-id "[caller]" --file hostedagent\Dockerfile .
```

Then update `hostedagent\.foundry\workflow-image.json` with the new image and run:

```powershell
python hostedagent\scripts\deploy_workflow_agent.py
```
