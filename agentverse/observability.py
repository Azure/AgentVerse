"""Application Insights / OpenTelemetry setup for Foundry playground traces."""

from __future__ import annotations

import logging
import os

from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential

from agentverse.foundry_definitions import PROJECT_ENDPOINT


logger = logging.getLogger(__name__)
_CONFIGURED = False


def configure_foundry_tracing(project_endpoint: str | None = None) -> bool:
    """Configure local OpenAI/Foundry SDK tracing to the project's App Insights resource."""

    global _CONFIGURED
    if _CONFIGURED:
        return True

    endpoint = project_endpoint or os.environ.get("AZURE_AI_PROJECT_ENDPOINT", PROJECT_ENDPOINT)
    try:
        project_client = AIProjectClient(endpoint=endpoint, credential=AzureCliCredential())
        connection_string = (
            os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
            or project_client.telemetry.get_application_insights_connection_string()
        )
    except Exception as exc:
        logger.warning("Application Insights tracing is not configured: %s", exc)
        return False

    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

        os.environ.setdefault("AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING", "true")
        configure_azure_monitor(connection_string=connection_string, enable_live_metrics=True)
        OpenAIInstrumentor().instrument()

        try:
            from agent_framework.observability import enable_instrumentation

            enable_instrumentation(enable_sensitive_data=_capture_message_content())
        except Exception as exc:
            logger.debug("Agent Framework instrumentation was not enabled: %s", exc)

        _CONFIGURED = True
        os.environ.setdefault("APPLICATIONINSIGHTS_CONNECTION_STRING", connection_string)
        return True
    except Exception as exc:
        logger.warning("OpenTelemetry instrumentation could not be enabled: %s", exc)
        return False


def _capture_message_content() -> bool:
    configured = os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")
    return configured.lower() in {"1", "true", "yes", "on"}
