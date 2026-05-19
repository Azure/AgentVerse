"""Run the local Agent Framework DevUI playground."""

from __future__ import annotations

import logging
import mimetypes
import os
import webbrowser

from agent_framework.devui import serve
from dotenv import load_dotenv

from agentverse.observability import configure_foundry_tracing
from agentverse.review_dashboard import start_review_dashboard


def ensure_browser_mime_types() -> None:
    """Register JavaScript MIME types before Starlette serves DevUI assets."""
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/javascript", ".mjs")


def main() -> None:
    """Start the reviewer dashboard and DevUI trace surface."""
    load_dotenv(override=False)
    ensure_browser_mime_types()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    agent_mode = os.environ.get("AGENTVERSE_AGENT_MODE", "foundry-tools")
    configure_foundry_tracing()
    from agentverse.foundry_workflow import workflow
    dashboard_url = start_review_dashboard(preferred_port=8081, agent_mode=agent_mode)
    devui_url = "http://127.0.0.1:8080"
    logging.info("Reviewer dashboard: %s (start here)", dashboard_url)
    logging.info("DevUI traces/debug: %s", devui_url)
    logging.info("Dashboard agent mode: %s", agent_mode)
    logging.info("Entity: Document Triage Workflow")
    if os.environ.get("AGENTVERSE_NO_BROWSER") != "1":
        webbrowser.open(dashboard_url)
    serve(entities=[workflow], port=8080, auto_open=False)


if __name__ == "__main__":
    main()
