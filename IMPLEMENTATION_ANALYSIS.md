# AgentVerse implementation analysis

Generated: 2026-05-19

## Executive summary

The implementation has been restructured from fixture-selected deterministic analysis to upload-driven Foundry analysis. A reviewer now uploads a supported document or image in the dashboard; Azure Content Understanding analyzes the file; the Foundry intake prompt agent classifies and routes it; and the chosen Foundry specialist prompt agent produces the recommendation.

The deterministic Python routing and specialist files were removed from the active codebase. The remaining local code is orchestration and support: file upload, Content Understanding REST calls, focused SQLite history snapshots, dashboard rendering, and Foundry prompt-agent invocation.

Content Understanding is not currently attached to the intake prompt agent as a Foundry tool. The local app calls Content Understanding first, then sends the normalized analyzer result to `AgentVerseIntakeAgent`; the intake agent decides the route from that evidence.

## Runtime surfaces

| Surface | URL | Purpose |
| --- | --- | --- |
| Reviewer dashboard | `http://127.0.0.1:8081` | Upload a document/image and see the user-friendly recommendation page. |
| Agent Framework DevUI | `http://127.0.0.1:8080` | Replay with a local `file_path` and inspect workflow traces. |
| Foundry tracing | Foundry portal / App Insights | View OpenTelemetry/OpenAI SDK traces exported to Application Insights. |

## Current architecture

```text
Uploaded file
  -> FastAPI dashboard or DevUI file_path request
  -> Azure Content Understanding
     - prebuilt-documentSearch for supported documents and document-like images
     - prebuilt-imageSearch for general image analysis, with documentSearch fallback for document-like PNG/JPG samples
  -> AgentVerseIntakeAgent in Foundry
     - extracts identifiers and fields from CU markdown/fields
     - decides financial / medical / supply / manual_review
  -> focused SQLite history snapshot
  -> Foundry specialist agent
     - AgentVerseFinancialAgent
     - AgentVerseMedicalAgent
     - AgentVerseSupplyAgent
     - AgentVerseManualReviewAgent
  -> reviewer dashboard recommendation
```

## Main files and responsibilities

| File | Responsibility |
| --- | --- |
| `main.py` | Starts dashboard and DevUI; enables MIME fix and Foundry/App Insights tracing. |
| `agentverse\content_understanding.py` | REST client for Content Understanding LRO `analyzeBinary`, analyzer selection, upload validation, and result normalization. |
| `agentverse\foundry_service.py` | Upload-driven orchestration: Content Understanding -> intake agent -> history snapshot -> specialist agent. |
| `agentverse\foundry_workflow.py` | Agent Framework workflow that accepts a local file path and routes through the Foundry-backed service. |
| `agentverse\foundry_definitions.py` | Prompt-agent names and instructions, including manual review. |
| `agentverse\history_snapshots.py` | Builds focused SQLite snapshots instead of sending the full database to prompts. |
| `agentverse\review_dashboard.py` | Upload-only reviewer dashboard; no route, case, or reviewer-role selector remains. |
| `agentverse\observability.py` | Configures Azure Monitor OpenTelemetry and OpenAI SDK instrumentation. |
| `scripts\build_demo_assets.py` | Generates SQLite DB and natural synthetic PNG upload samples. |
| `scripts\configure_content_understanding_defaults.py` | Configures Content Understanding default model deployments. |
| `scripts\analyze_fabricated_documents.py` | Optional Content Understanding smoke-test for fabricated PNG samples. |
| `scripts\create_foundry_agents.py` | Creates/versions Foundry prompt agents. |
| `.foundry\agentverse-foundry.yaml` | Local manifest of Foundry, Content Understanding, observability, agent, and data paths. |
| `.foundry\agent-metadata.yaml` | Skill-compatible metadata with project endpoint and App Insights settings. |

Removed deterministic runtime files:

```text
agentverse\service.py
agentverse\workflow.py
agentverse\intake.py
agentverse\agents\*
agentverse\mocks\*
data\document_intelligence_results\*
```

## Azure resources

| Resource | Value |
| --- | --- |
| Resource group | `rg-agent-verse` |
| Foundry resource | `agent-verse-resource` |
| Foundry project | `agent-verse-project` |
| Project endpoint | `https://agent-verse-resource.services.ai.azure.com/api/projects/agent-verse-project` |
| Content Understanding endpoint | `https://agent-verse-resource.cognitiveservices.azure.com/` |
| Main prompt-agent deployment | `gpt-4o` |
| Content Understanding completion default | `gpt-4.1-mini` |
| Content Understanding embedding default | `text-embedding-3-large` |
| Log Analytics workspace | `law-agent-verse-resource` |
| Application Insights | `appi-agent-verse-resource` |
| Foundry App Insights connection | `agent-verse-resource-appinsights` |

## Foundry agents

| Agent | Responsibility |
| --- | --- |
| `AgentVerseIntakeAgent` | Reads Content Understanding markdown/fields, extracts identifiers, selects route and subtype. |
| `AgentVerseFinancialAgent` | Reviews credit applications and withdrawal orders using focused financial history. |
| `AgentVerseMedicalAgent` | Reviews clinical notes and prescriptions using patient history and safety constraints. |
| `AgentVerseSupplyAgent` | Reviews arrived balance sheets, received units, pending to-send orders, urgency dates, client order cadence, consolidation windows, inventory balance, reservations, historical demand/supply, supplier performance, and invoice discrepancies. |
| `AgentVerseManualReviewAgent` | Creates escalation summaries for unreadable, ambiguous, unsupported, or non-routable uploads. |

## Content Understanding behavior

The upload client uses the GA `2025-11-01` Content Understanding API and handles the asynchronous operation flow:

1. `POST /contentunderstanding/analyzers/{analyzerId}:analyzeBinary`
2. Read `Operation-Location`
3. Poll until `status == Succeeded`
4. Normalize markdown, fields, tables, pages, warnings, citations, and a bounded analyzer context summary

Supported upload formats match the documented Content Understanding document/image limits used by this app:

```text
.pdf, .tiff, .jpg, .jpeg, .jpe, .png, .bmp, .heif, .heic,
.docx, .xlsx, .pptx, .txt, .html, .md, .rtf, .eml, .msg, .xml
```

For image files, the app starts with `prebuilt-imageSearch` and keeps that result when the image summary is useful. It only falls back to `prebuilt-documentSearch` if the image result is too sparse to route. PDFs and other document formats use `prebuilt-documentSearch`.

## Fabricated document compliance

The current files in `data\fabricated_documents\` include PNG images and native-text PDFs. PNG samples exercise `prebuilt-imageSearch`; PDF samples exercise direct document upload behavior through `prebuilt-documentSearch`.

| File | Size | Type | Supported |
| --- | ---: | --- | --- |
| `clinical_note_red_flags.png` | 79,411 bytes | 1400 x 1800 | yes |
| `clinical_note_red_flags.pdf` | 1,989 bytes | PDF | yes |
| `credit_application.png` | 80,702 bytes | 1400 x 1800 | yes |
| `credit_application.pdf` | 2,012 bytes | PDF | yes |
| `low_quality_unknown.png` | 44,773 bytes | 1400 x 1800 | yes |
| `low_quality_unknown.pdf` | 1,788 bytes | PDF | yes |
| `prescription_allergy_conflict.png` | 61,457 bytes | 1400 x 1800 | yes |
| `prescription_allergy_conflict.pdf` | 1,897 bytes | PDF | yes |
| `shipment_request.png` | 81,746 bytes | 1400 x 1800 | yes |
| `shipment_request.pdf` | 1,978 bytes | PDF | yes |
| `supplier_invoice_mismatch.png` | 63,858 bytes | 1400 x 1800 | yes |
| `supplier_invoice_mismatch.pdf` | 1,887 bytes | PDF | yes |
| `withdrawal_order_high_risk.png` | 79,176 bytes | 1400 x 1800 | yes |
| `withdrawal_order_high_risk.pdf` | 1,955 bytes | PDF | yes |

They are fabricated samples, not real customer/patient/supplier documents. They contain natural synthetic document text and IDs that map to the simulated SQLite database. They do not include a pre-rendered "extracted fields" section; Content Understanding and the intake agent extract the fields from the visible document content.

## Simulated database

The SQLite database remains because the Foundry specialists need realistic history context. It is no longer used for deterministic Python decisions; it is used to build compact prompt snapshots after the intake agent extracts IDs from the uploaded content.

Observed generated data volume:

| Table/domain | Count |
| --- | ---: |
| Financial customers | 3 |
| Financial transactions | 350 |
| Patients | 3 |
| Clinical events | 54 |
| Suppliers/distributors | 3 |
| Supply clients | 4 |
| Outbound to-send orders | 9 |
| Purchase orders | 43 |
| Supplier invoices | 43 |
| Inventory demand history | 72 |

`data\fabricated_history_summary.json` is generated from the SQLite database for review. The key financial pattern case is Pedro Alonso (`CUST-1002`, `ACCT-2002`): usual locations are Vigo branches/ATMs, routine withdrawals average about 350 EUR with a 900 EUR configured maximum, recent events show Vigo withdrawals and salary deposits, and the sample withdrawal requests 10,000 EUR at Valencia Centro Branch after a same-day 8,000 EUR online transfer.

The supply snapshot now includes current inventory, safety stock, critical reservations, pending outbound to-send orders, per-product order matches, client ordering cadence, consolidation windows, recent product demand, demand averages/peaks, recent purchase/delivery history, supplier reliability, and invoice/PO/delivery details. The supply fabricated cases are receiving-dock balance sheets: `BSH-2026-0519-A` receives gloves, masks, and saline with no pallet destination so the agent must allocate units across urgent and consolidatable outbound demand; `BSH-2026-0519-B` receives `SYRINGE_5ML` units while `INV-8101` / `PO-7001` has a quantity mismatch that should be reconciled without blocking urgent shipment.

## Live upload validation

All fabricated PNG/PDF samples were processed through Content Understanding. These representative uploads were also processed through the full upload path:

| Upload | Analyzer | Route | Subtype | Action | Risk |
| --- | --- | --- | --- | --- | --- |
| `clinical_note_red_flags.png` | `prebuilt-imageSearch` | medical | clinical_note | escalate | critical |
| `shipment_request.png` | `prebuilt-imageSearch` | supply | receiving_sheet | ship_immediately | low |
| `shipment_request.pdf` | `prebuilt-documentSearch` | supply | receiving_sheet | ship_immediately | low |
| `supplier_invoice_mismatch.png` | `prebuilt-imageSearch` | supply | receiving_sheet | ship_immediately | medium |
| `supplier_invoice_mismatch.pdf` | `prebuilt-documentSearch` | supply | receiving_sheet | ship_immediately | medium |
| `withdrawal_order_high_risk.png` | `prebuilt-imageSearch` | financial | withdrawal_order | hold | high |
| `withdrawal_order_high_risk.pdf` | `prebuilt-documentSearch` | financial | withdrawal_order | hold | high |

Offline regression suite:

```text
11 passed
```

## Requirement compliance matrix

| Requirement | Current state | Assessment |
| --- | --- | --- |
| Remove deterministic analysis selection | Dashboard is upload-only; no case, route, or reviewer-role selector remains. | Meets |
| Use Foundry intake agent for route decision | `AgentVerseIntakeAgent` receives Content Understanding output and selects route/subtype. | Meets |
| Use Content Understanding document/image analyzers | Implemented `prebuilt-documentSearch` and `prebuilt-imageSearch` via REST LRO. | Meets |
| Validate fabricated documents | All sample PNGs are supported, below size limits, and live-tested. | Meets |
| Remove deterministic files | Local deterministic workflow, intake, agents, mocks, and saved DI outputs were removed. | Meets |
| Deploy Log Analytics and App Insights | `law-agent-verse-resource` and `appi-agent-verse-resource` created. | Meets |
| Attach App Insights to Foundry | Foundry connection `agent-verse-resource-appinsights` created and SDK telemetry lookup succeeds. | Meets |
| Preserve human review safety | Agents return recommendations only; no real action is executed. | Meets |

## Remaining gaps

1. The app is still local, not a hosted Foundry agent.
2. SQLite access is still local orchestration rather than a Foundry-hosted tool.
3. Content Understanding defaults required extra supported deployments because the existing `gpt-4o` deployment is not supported by Content Understanding prebuilt analyzers.
4. Prompt-agent outputs should be evaluated with a larger uploaded dataset before hosting.

## Conclusion

The playground now matches the intended direction: upload first, Content Understanding extraction, Foundry intake routing, Foundry specialist recommendation, and App Insights-backed tracing. The deterministic Python decision path has been removed from the active codebase.
