from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from agentverse.foundry_service import FoundryTriageService
from agentverse.foundry_service import _normalize_recommendation_json


class _FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if len(self.calls) == 1:
            text = '{"recommended_action": "ship_immediately", "reasoning_summary": "bad "quote""}'
        else:
            text = '{"recommended_action": "ship_immediately", "reasoning_summary": "bad \\"quote\\""}'
        return SimpleNamespace(output=[SimpleNamespace(content=[SimpleNamespace(text=text)])])


def test_invoke_json_repairs_malformed_agent_json_locally() -> None:
    service = FoundryTriageService.__new__(FoundryTriageService)
    fake_responses = _FakeResponses()
    service._openai_client = SimpleNamespace(responses=fake_responses)
    service._model = "test-model"

    result = service._invoke_json("AgentVerseSupplyAgent", {"hello": "world"})

    assert result["recommended_action"] == "ship_immediately"
    assert result["reasoning_summary"] == 'bad "quote"'
    assert "extra_body" in fake_responses.calls[0]
    assert len(fake_responses.calls) == 1


def test_recommendation_normalization_wraps_non_dict_evidence_values() -> None:
    result = _normalize_recommendation_json(
        {
            "evidence": [
                {
                    "source": "history_snapshot",
                    "detail": "matched to-send orders",
                    "values": [{"order_id": "SEND-9100"}],
                }
            ]
        }
    )

    assert result["evidence"][0]["values"] == {"items": [{"order_id": "SEND-9100"}]}
