"""Brand configuration — single source of truth for the Python services.

To rebrand the demo, set the env vars below (typically via `.env` or the
Container App configuration). The frontend has its own brand config in
``dashboard/src/brand.ts`` — keep both sides in sync.

Variables
---------
BRAND_NAME              Full company name spoken by the voice agent and
                        embedded in agent prompts. Default: "Helix Insurance".
VOICE_ASSISTANT_NAME    First name of the voice IVR character. Default: "Leo".

The voice prompt (``agents/voice/__init__.py``) and the content-understanding
schema description (``agents/content_understanding/agent.py``) both interpolate
``BRAND_NAME`` at import time, so changes require a backend restart.
"""
from __future__ import annotations

import os

BRAND_NAME: str = os.environ.get("BRAND_NAME", "Helix Insurance")
VOICE_ASSISTANT_NAME: str = os.environ.get("VOICE_ASSISTANT_NAME", "Leo")
