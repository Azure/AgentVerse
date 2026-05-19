# AgentVerse document triage playground

AgentVerse is a local Microsoft Agent Framework playground for upload-driven document triage across financial, medical, and supply/procurement cases.

The dashboard no longer lets the reviewer choose a case or route. The reviewer uploads a supported document or image, Azure Content Understanding analyzes it with `prebuilt-documentSearch` / `prebuilt-imageSearch`, the Foundry intake agent decides the route, and the selected Foundry specialist returns the review recommendation.

## What is included

| Area | Current implementation |
| --- | --- |
| Reviewer UI | Upload-focused FastAPI dashboard on `http://127.0.0.1:8081` |
| Trace UI | Agent Framework DevUI on `http://127.0.0.1:8080` |
| Content analysis | Azure Content Understanding prebuilt analyzers |
| Agent routing | Foundry prompt intake agent decides financial, medical, supply, or manual review |
| Specialist agents | Foundry financial, medical, supply, and manual-review prompt agents |
| Simulated data | SQLite database with long histories for 3 financial clients, 3 patients, and 3 distributors/suppliers |
| Supply allocation | Supply agent treats arrived balance sheets as unassigned stock, compares received units with pending to-send orders, urgency, client cadence, inventory, reservations, historical demand/supply, and supplier performance, then recommends ship/store/consolidate actions |
| Observability | Log Analytics + Application Insights connected to the Foundry resource |
| Safety | Recommendation-only outputs; no real financial, medical, inventory, or procurement action is executed |

## Run the playground

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
python main.py
```

Open:

- Reviewer dashboard: `http://127.0.0.1:8081`
- DevUI traces/debug: `http://127.0.0.1:8080`

The dashboard accepts these upload types: `.pdf`, `.tiff`, `.jpg`, `.jpeg`, `.jpe`, `.png`, `.bmp`, `.heif`, `.heic`, `.docx`, `.xlsx`, `.pptx`, `.txt`, `.html`, `.md`, `.rtf`, `.eml`, `.msg`, `.xml`.

## Example DevUI request

DevUI cannot upload a browser file directly, so use a local path:

```json
{
  "file_path": "C:\\Demos offline\\AgentVerse\\data\\fabricated_documents\\withdrawal_order_high_risk.png"
}
```

## How Content Understanding is linked

In this local playground, Content Understanding is not attached to the intake prompt agent as a Foundry tool. The local app orchestrates the workflow: it receives the upload, calls Content Understanding, then passes a concise analyzer summary plus bounded evidence excerpts to `AgentVerseIntakeAgent`. The intake agent normalizes the route, subtype, and fields, and the selected specialist also receives the analyzer context for grounding.

## Rebuild demo assets

Generate the SQLite database, PNG samples, PDF samples, and history summary:

```powershell
python scripts\build_demo_assets.py
```

Configure Content Understanding default deployments:

```powershell
python scripts\configure_content_understanding_defaults.py
```

Smoke-test fabricated documents with Content Understanding:

```powershell
python scripts\analyze_fabricated_documents.py
```

Create or version the Foundry prompt agents:

```powershell
python scripts\create_foundry_agents.py
```

Generated assets are stored in:

| Path | Contents |
| --- | --- |
| `data\agentverse_simulated.db` | SQLite histories for financial, medical, and supply scenarios |
| `data\fabricated_documents\` | Natural-looking synthetic PNG and PDF upload samples used by the demo |
| `data\fabricated_history_summary.json` | Generated summary of client, patient, and supplier histories for review |
| `data\content_understanding_results\` | Optional saved Content Understanding smoke-test results for PNG and PDF samples |
| `.foundry\created-agents.json` | Foundry prompt agent names and versions |

## Azure resources

| Resource | Name |
| --- | --- |
| Foundry resource | `agent-verse-resource` |
| Foundry project | `agent-verse-project` |
| Main model deployment | `gpt-4o` |
| Content Understanding completion default | `gpt-4.1-mini` |
| Content Understanding embedding default | `text-embedding-3-large` |
| Log Analytics | `law-agent-verse-resource` |
| Application Insights | `appi-agent-verse-resource` |

## Run tests

```powershell
python -m pytest
```

The default test suite is offline and does not call Azure.

## Current boundary

This is still a local playground, not a hosted Foundry agent. The local app handles file upload, Content Understanding calls, SQLite snapshot retrieval, dashboard rendering, and Foundry prompt-agent invocation. The deterministic Python routing/specialist files were removed from the active codebase. If you later move to a hosted/tool-calling design, Content Understanding can be exposed as an agent tool or run inside the hosted agent application.
