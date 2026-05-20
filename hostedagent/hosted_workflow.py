"""Foundry-hosted workflow entrypoint for AgentVerse document triage."""

from __future__ import annotations

import asyncio
import mimetypes
import os
from pathlib import Path

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from agentverse.contracts import AnalyzerKind, UploadedDocumentRequest
from agentverse.formatter import format_triage_result
from agentverse.foundry_definitions import MODEL_DEPLOYMENT_NAME, PROJECT_ENDPOINT
from agentverse.foundry_service import FoundryTriageService


load_dotenv()

HOSTED_HOME = Path(os.environ.get("HOME", "/home/session"))
SESSION_HOME = Path("/home/session")
SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".docx", ".txt"}


def _workflow_service() -> FoundryTriageService:
    credential = DefaultAzureCredential()
    return FoundryTriageService(
        project_endpoint=os.environ.get("FOUNDRY_PROJECT_ENDPOINT") or os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or PROJECT_ENDPOINT,
        model_deployment_name=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", MODEL_DEPLOYMENT_NAME),
        credential=credential,
    )


@tool(
    description=(
        "Analyze an uploaded PDF/document/image through the AgentVerse workflow. "
        "Pass a session file path such as /data/shipment_request.pdf, or a filename if the file is in the session home."
    ),
    approval_mode="never_require",
)
def analyze_uploaded_file(file_path: str) -> str:
    """Analyze a Foundry session file using Content Understanding and Foundry prompt agents."""
    path = _resolve_uploaded_path(file_path)
    request = UploadedDocumentRequest(
        filename=path.name,
        content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        content_bytes=path.read_bytes(),
        analyzer_kind=AnalyzerKind.AUTO,
        metadata={"source": "foundry_hosted_workflow"},
    )
    result = _workflow_service().run_upload(request)
    return format_triage_result(result)


@tool(
    description="List files available in the hosted agent session so the user can choose one for analysis.",
    approval_mode="never_require",
)
def list_uploaded_files() -> list[str]:
    """List likely uploaded files under documented hosted-session upload roots."""
    files = []
    seen = set()
    for root in _upload_roots():
        for path in _iter_supported_files(root):
            key = path.resolve()
            if key in seen:
                continue
            seen.add(key)
            try:
                label = path.relative_to(root)
            except ValueError:
                label = path
            files.append(str(label).replace("\\", "/"))
    return sorted(files)


def _upload_roots() -> list[Path]:
    roots = []
    for root in (SESSION_HOME, HOSTED_HOME):
        if root not in roots and root.exists():
            roots.append(root)
        for child in (root / "data", root / "uploads"):
            if child not in roots and child.exists():
                roots.append(child)
    return roots


def _iter_supported_files(root: Path):
    if root.is_file():
        if root.suffix.lower() in SUPPORTED_UPLOAD_EXTENSIONS:
            yield root
        return
    ignored_dirs = {".cache", ".local", ".venv", "venv", "__pycache__", "site-packages"}
    stack = [root]
    while stack:
        current = stack.pop()
        for path in current.iterdir():
            if path.is_dir():
                if path.name not in ignored_dirs:
                    stack.append(path)
            elif path.is_file() and path.suffix.lower() in SUPPORTED_UPLOAD_EXTENSIONS:
                yield path


def _resolve_uploaded_path(file_path: str) -> Path:
    raw = Path(file_path.strip().strip('"').strip("'"))
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
        home_relative = Path(str(raw).lstrip("/\\"))
        for root in _upload_roots():
            candidates.extend([root / home_relative, root / home_relative.name])
    else:
        for root in _upload_roots():
            candidates.extend([root / raw, root / raw.name, root / "data" / raw.name, root / "uploads" / raw.name])
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    available = ", ".join(list_uploaded_files()[:20]) or "no supported files found"
    raise FileNotFoundError(f"Could not find uploaded file '{file_path}'. Available files: {available}")


async def main() -> None:
    os.environ["AGENTVERSE_USE_DEFAULT_AZURE_CREDENTIAL"] = "1"
    credential = DefaultAzureCredential()
    client = FoundryChatClient(
        project_endpoint=os.environ.get("FOUNDRY_PROJECT_ENDPOINT") or os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or PROJECT_ENDPOINT,
        model=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", MODEL_DEPLOYMENT_NAME),
        credential=credential,
    )
    async with Agent(
        client=client,
        instructions=(
            "You are the AgentVerse workflow agent. Your job is to provide the same workflow as the local "
            "review dashboard: analyze one uploaded document or image with Azure Content Understanding, pass "
            "the extracted evidence to AgentVerseIntakeAgent, then call the selected specialist prompt agent "
            "(financial, medical, supply, or manual review). If the user asks to analyze a file, call "
            "analyze_uploaded_file. If the path is unclear, call list_uploaded_files and ask the user to pick "
            "one of the available session files. Return the final triage result clearly; do not execute business actions."
        ),
        tools=[analyze_uploaded_file, list_uploaded_files],
        default_options={"store": False},
    ) as agent:
        await ResponsesHostServer(agent).run_async()


if __name__ == "__main__":
    asyncio.run(main())
