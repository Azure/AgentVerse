"""Upload a local file to AgentVerseWorkflowAgent hosted-session storage."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from azure.identity import AzureCliCredential

from agentverse.foundry_definitions import PROJECT_ENDPOINT

DEFAULT_AGENT_NAME = "AgentVerseWorkflowAgent"
API_VERSION = "v1"
TOKEN_SCOPE = "https://ai.azure.com/.default"
HOSTED_FEATURE_HEADER = "HostedAgents=V1Preview"


def main() -> None:
    args = _parse_args()
    local_file = args.file.resolve()
    if not local_file.is_file():
        raise FileNotFoundError(f"File not found: {local_file}")

    remote_path = args.remote_path or f"/uploads/{local_file.name}"
    if not remote_path.startswith("/"):
        remote_path = f"/{remote_path}"

    token = AzureCliCredential().get_token(TOKEN_SCOPE).token
    session_id = args.session_id or _create_session(token, args.project_endpoint, args.agent_name)
    upload_result = _upload_file(
        token=token,
        project_endpoint=args.project_endpoint,
        agent_name=args.agent_name,
        session_id=session_id,
        local_file=local_file,
        remote_path=remote_path,
    )

    print(json.dumps(upload_result, indent=2))
    print()
    print(f"Session ID: {session_id}")
    print(f"Uploaded path: {remote_path}")

    prompt = f"Analyze {remote_path} and run the full AgentVerse workflow."
    if args.invoke:
        print()
        print("Workflow response:")
        response = _invoke_agent(
            token=token,
            project_endpoint=args.project_endpoint,
            agent_name=args.agent_name,
            session_id=session_id,
            prompt=prompt,
            timeout=args.timeout,
        )
        print(_extract_response_text(response) or json.dumps(response, indent=2))
    else:
        print()
        print("Prompt to run against the same session:")
        print(prompt)
        print()
        print("If you use the REST/Code tab, include this field in the responses request body:")
        print(json.dumps({"agent_session_id": session_id}, indent=2))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upload a PDF/image/document into AgentVerseWorkflowAgent hosted-session storage. "
            "Use --invoke to start the full workflow immediately."
        )
    )
    parser.add_argument("file", type=Path, help="Local file to upload, for example data\\fabricated_documents\\shipment_request.png")
    parser.add_argument("--remote-path", help="Hosted session path. Defaults to /uploads/<filename>.")
    parser.add_argument("--session-id", help="Reuse an existing hosted agent_session_id.")
    parser.add_argument("--agent-name", default=DEFAULT_AGENT_NAME)
    parser.add_argument("--project-endpoint", default=PROJECT_ENDPOINT)
    parser.add_argument("--invoke", action="store_true", help="Invoke the workflow after uploading the file.")
    parser.add_argument("--timeout", type=int, default=300, help="Invocation timeout in seconds.")
    return parser.parse_args()


def _create_session(token: str, project_endpoint: str, agent_name: str) -> str:
    response = _invoke_agent(
        token=token,
        project_endpoint=project_endpoint,
        agent_name=agent_name,
        session_id=None,
        prompt="Create a hosted session for an upcoming file upload. Reply with one short sentence.",
        timeout=120,
    )
    session_id = response.get("agent_session_id")
    if not isinstance(session_id, str) or not session_id:
        raise RuntimeError(f"Hosted response did not include agent_session_id: {json.dumps(response, indent=2)}")
    return session_id


def _upload_file(
    *,
    token: str,
    project_endpoint: str,
    agent_name: str,
    session_id: str,
    local_file: Path,
    remote_path: str,
) -> dict[str, Any]:
    encoded_path = urllib.parse.quote(remote_path, safe="")
    url = f"{project_endpoint}/agents/{agent_name}/endpoint/sessions/{session_id}/files/content?api-version={API_VERSION}&path={encoded_path}"
    content_type = mimetypes.guess_type(local_file.name)[0] or "application/octet-stream"
    return _request_json(
        url,
        token,
        method="PUT",
        body=local_file.read_bytes(),
        extra_headers={"Content-Type": content_type},
        timeout=120,
    )


def _invoke_agent(
    *,
    token: str,
    project_endpoint: str,
    agent_name: str,
    session_id: str | None,
    prompt: str,
    timeout: int,
) -> dict[str, Any]:
    url = f"{project_endpoint}/agents/{agent_name}/endpoint/protocols/openai/responses?api-version={API_VERSION}"
    payload: dict[str, Any] = {"model": agent_name, "input": prompt, "stream": False}
    if session_id:
        payload["agent_session_id"] = session_id
    return _request_json(
        url,
        token,
        method="POST",
        body=json.dumps(payload).encode("utf-8"),
        extra_headers={"Content-Type": "application/json"},
        timeout=timeout,
    )


def _request_json(
    url: str,
    token: str,
    *,
    method: str,
    body: bytes | None,
    extra_headers: dict[str, str] | None = None,
    timeout: int,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Foundry-Features": HOSTED_FEATURE_HEADER,
        **(extra_headers or {}),
    }
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed with HTTP {error.code}: {details}") from error
    return json.loads(content) if content else {}


def _extract_response_text(response: dict[str, Any]) -> str:
    chunks = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)


if __name__ == "__main__":
    main()
