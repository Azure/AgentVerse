import json
from typing import Any, Dict

def format_sse(event: str, data: Dict[str, Any]) -> str:
    """Format data as SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
