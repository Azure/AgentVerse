"""Parallel model inference with fair latency / token measurement.

One STREAMED Chat Completions request per model so latency, TTFT and token usage
describe the same generation:
  - MI token is prefetched before any timer starts (see azure_clients).
  - t0 captured immediately before the outbound request.
  - TTFT = time to the first NON-EMPTY generated text delta.
  - total latency = until the stream (incl. the final usage frame) is consumed.
  - usage via stream_options={"include_usage": true}.
  - throughput = completion_tokens / (t_end - t_first_text).
Per-model timeout + failure isolation: one model erroring never fails the run.
Parameters are filtered per model capability (reasoning models reject
temperature/top_p and use max_completion_tokens).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from . import config, discovery
from .azure_clients import get_openai_client, prefetch_token
from .guardrails import MODEL_SEMAPHORE


def build_params(model_meta: Dict[str, Any], prompt: str, system: str,
                 temperature: Optional[float], top_p: Optional[float],
                 max_tokens: int, seed: Optional[int]) -> Dict[str, Any]:
    """Assemble create() kwargs honouring the model's capabilities."""
    messages = []
    if system and system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": prompt})

    out_tokens = max(1, min(int(max_tokens or config.MAX_OUTPUT_TOKENS), config.MAX_OUTPUT_TOKENS))
    params: Dict[str, Any] = {
        "model": model_meta["name"],
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    params[model_meta.get("token_param", "max_tokens")] = out_tokens
    if not model_meta.get("reasoning"):
        # Reasoning models (gpt-5.x/o*) reject these; only send for others.
        if temperature is not None:
            params["temperature"] = float(temperature)
        if top_p is not None:
            params["top_p"] = float(top_p)
        if seed is not None:
            params["seed"] = int(seed)
    return params


async def _run_one(model_meta: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """Stream one model to completion, collecting text + fair metrics."""
    name = model_meta["name"]
    result: Dict[str, Any] = {
        "name": name, "model": model_meta.get("model", name),
        "version": model_meta.get("version", ""), "reasoning": model_meta.get("reasoning", False),
        "text": "", "error": None, "finish_reason": None,
        "latency_ms": None, "ttft_ms": None,
        "tokens": {"prompt": None, "completion": None, "total": None},
        "tokens_per_sec": None, "content_filter": None, "usage_available": False,
    }
    client = await get_openai_client()
    async with MODEL_SEMAPHORE:
        t0 = time.perf_counter()
        t_first: Optional[float] = None
        try:
            async def _consume() -> None:
                nonlocal t_first
                stream = await client.chat.completions.create(**params)
                async for chunk in stream:
                    choices = getattr(chunk, "choices", None) or []
                    if choices:
                        ch = choices[0]
                        delta = getattr(ch, "delta", None)
                        piece = getattr(delta, "content", None) if delta else None
                        if piece:
                            if t_first is None:
                                t_first = time.perf_counter()
                            result["text"] += piece
                        if getattr(ch, "finish_reason", None):
                            result["finish_reason"] = ch.finish_reason
                        cfr = getattr(ch, "content_filter_results", None)
                        if cfr:
                            result["content_filter"] = _summ_filter(cfr)
                    usage = getattr(chunk, "usage", None)
                    if usage:
                        result["tokens"] = {
                            "prompt": getattr(usage, "prompt_tokens", None),
                            "completion": getattr(usage, "completion_tokens", None),
                            "total": getattr(usage, "total_tokens", None),
                        }
                        result["usage_available"] = True

            await asyncio.wait_for(_consume(), config.INFERENCE_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            result["error"] = f"timeout after {config.INFERENCE_TIMEOUT_SECONDS}s"
        except Exception as exc:  # noqa: BLE001
            result["error"] = f"{type(exc).__name__}: {str(exc)[:400]}"

        t_end = time.perf_counter()
        result["latency_ms"] = round((t_end - t0) * 1000, 1)
        if t_first is not None:
            result["ttft_ms"] = round((t_first - t0) * 1000, 1)
            comp = result["tokens"].get("completion")
            gen_secs = max(t_end - t_first, 1e-6)
            if comp:
                result["tokens_per_sec"] = round(comp / gen_secs, 1)
    return result


def _summ_filter(cfr: Any) -> Dict[str, Any]:
    """Compact content-filter view (from the response — no extra model call)."""
    out: Dict[str, Any] = {}
    try:
        data = cfr if isinstance(cfr, dict) else dict(cfr)
        for k, v in data.items():
            if isinstance(v, dict):
                if v.get("filtered"):
                    out[k] = v.get("severity", "filtered")
            elif v:
                out[k] = str(v)
    except Exception:
        return {}
    return out


async def compare(models: List[Dict[str, Any]], prompt: str, system: str,
                  temperature: Optional[float], top_p: Optional[float],
                  max_tokens: int, seed: Optional[int]) -> List[Dict[str, Any]]:
    """Run all models truly in parallel; results keep input order."""
    await prefetch_token()
    tasks = [
        _run_one(m, build_params(m, prompt, system, temperature, top_p, max_tokens, seed))
        for m in models
    ]
    return await asyncio.gather(*tasks)
