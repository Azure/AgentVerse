"""Simulated telemetry stream for the Signal-to-Service demo.

Produces a JSON time-series per asset in two modes:

  * ``healthy``   — values hover around the asset's nominal band with light noise.
  * ``degrading`` — values start healthy and ramp toward (and past) the alarm
                    threshold on the channel(s) implied by the asset's failure
                    mode, reproducing a "signal degrading to anomaly" trace.

The generator is fully local and deterministic-ish (seeded per asset), so the
demo behaves identically offline and in Azure.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ASSETS_PATH = DATA_DIR / "assets.json"

WINDOW = 60          # number of samples returned
SAMPLE_SECONDS = 5   # nominal spacing between samples

CHANNELS = ("vibration_mm_s", "temperature_c", "current_a")

# Which channels ramp for each failure mode, and how aggressively (fraction of
# the nominal->alarm span that the peak sample reaches; >1 overshoots alarm).
_FAILURE_PROFILE: Dict[str, Dict[str, float]] = {
    "bearing":     {"vibration_mm_s": 1.15, "temperature_c": 0.55},
    "overheating": {"temperature_c": 1.10, "current_a": 0.45},
    "overcurrent": {"current_a": 1.12, "temperature_c": 0.60},
    "imbalance":   {"vibration_mm_s": 1.20},
}


def load_assets() -> List[Dict[str, Any]]:
    return json.loads(ASSETS_PATH.read_text(encoding="utf-8"))


def get_asset(asset_id: str) -> Dict[str, Any]:
    for a in load_assets():
        if a["id"] == asset_id:
            return a
    raise KeyError(f"unknown asset {asset_id!r}")


def _noise(rng: random.Random, scale: float) -> float:
    return (rng.random() - 0.5) * 2.0 * scale


def generate_series(asset_id: str, mode: str = "healthy") -> Dict[str, Any]:
    """Return {asset_id, mode, sample_seconds, points:[...], anomaly:{...}|None}.

    ``points`` is a list of {t, vibration_mm_s, temperature_c, current_a}.
    """
    asset = get_asset(asset_id)
    rng = random.Random(hash((asset_id, mode)) & 0xFFFFFFFF)
    nominal = asset["nominal"]
    warn = asset["warn"]
    alarm = asset["alarm"]

    profile = _FAILURE_PROFILE.get(asset.get("failure_hint", ""), {}) if mode == "degrading" else {}

    points: List[Dict[str, Any]] = []
    anomaly_from: int | None = None

    for i in range(WINDOW):
        frac = i / (WINDOW - 1)  # 0..1 across the window
        point: Dict[str, Any] = {"t": i * SAMPLE_SECONDS}
        for ch in CHANNELS:
            base = float(nominal[ch])
            span = float(alarm[ch]) - base
            val = base + _noise(rng, span * 0.04)
            ramp = profile.get(ch)
            if ramp is not None:
                # No ramp for the first 45% of the window, then rise smoothly.
                if frac > 0.45:
                    prog = (frac - 0.45) / 0.55           # 0..1 over the tail
                    prog = prog * prog                     # ease-in (accelerating fault)
                    val = base + span * ramp * prog + _noise(rng, span * 0.03)
            point[ch] = round(val, 2)
            if ramp is not None and point[ch] >= warn[ch] and anomaly_from is None:
                anomaly_from = i
        points.append(point)

    anomaly = None
    if mode == "degrading" and profile:
        last = points[-1]
        breached = {
            ch: {"value": last[ch], "warn": warn[ch], "alarm": alarm[ch]}
            for ch in profile
            if last[ch] >= warn[ch]
        }
        anomaly = {
            "detected": bool(breached),
            "from_index": anomaly_from,
            "channels": breached,
            "failure_hint": asset.get("failure_hint"),
        }

    return {
        "asset_id": asset_id,
        "mode": mode,
        "sample_seconds": SAMPLE_SECONDS,
        "channels": list(CHANNELS),
        "nominal": nominal,
        "warn": warn,
        "alarm": alarm,
        "points": points,
        "anomaly": anomaly,
    }
