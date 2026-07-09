import json
from typing import Any, Dict, List

def format_sse(event: str, data: Dict[str, Any]) -> str:
    """Format a payload as a Server-Sent Events frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

def sse_heartbeat() -> str:
    """SSE comment line — keeps the connection alive through ACA ingress."""
    return ": keep-alive\n\n"
