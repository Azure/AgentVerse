import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.backend import config, discovery, inference, judge


def model_entry(model, source="project", name="custom-deployment"):
    return discovery._entry(name, model, "", "OpenAI", {}, source)


class ModelParameterTests(unittest.TestCase):
    def test_astra_discovery_metadata(self):
        for source in ("project", "arm"):
            with self.subTest(source=source):
                meta = model_entry("gpt-6-astra", source)
                self.assertTrue(meta["selectable"])
                self.assertTrue(meta["reasoning"])
                self.assertEqual(meta["token_param"], "max_completion_tokens")
                self.assertEqual(meta["name"], "custom-deployment")

    def test_astra_static_discovery(self):
        with patch.object(config, "STATIC_MODELS", ["gpt-6-astra"]):
            meta, = discovery._from_static()
        self.assertTrue(meta["reasoning"])
        self.assertEqual(meta["token_param"], "max_completion_tokens")

    def test_reasoning_comparison_parameters(self):
        for model in ("gpt-6-astra", "GPT-6-ASTRA", "gpt-5.4-mini", "o1", "o3", "o4-mini"):
            with self.subTest(model=model):
                params = inference.build_params(
                    model_entry(model), "Hello", "", 0.7, 0.9, 512, 42,
                )
                self.assertEqual(params["model"], "custom-deployment")
                self.assertEqual(params["max_completion_tokens"], min(512, config.MAX_OUTPUT_TOKENS))
                for unsupported in ("max_tokens", "temperature", "top_p", "seed"):
                    self.assertNotIn(unsupported, params)
                self.assertTrue(params["stream"])
                self.assertEqual(params["stream_options"], {"include_usage": True})

    def test_non_reasoning_comparison_parameters_unchanged(self):
        for model in ("gpt-4o", "gpt-4.1", "Phi-4", "Mistral-Large"):
            with self.subTest(model=model):
                meta = model_entry(model)
                self.assertFalse(meta["reasoning"])
                params = inference.build_params(meta, "Hello", "", 0.7, 0.9, 512, 42)
                self.assertEqual(params["max_tokens"], min(512, config.MAX_OUTPUT_TOKENS))
                self.assertNotIn("max_completion_tokens", params)
                self.assertEqual(params["temperature"], 0.7)
                self.assertEqual(params["top_p"], 0.9)
                self.assertEqual(params["seed"], 42)

    def test_astra_output_token_limit_preserved(self):
        with patch.object(config, "MAX_OUTPUT_TOKENS", 1024):
            for requested, expected in ((-1, 1), (512, 512), (4096, 1024)):
                with self.subTest(requested=requested):
                    params = inference.build_params(
                        model_entry("gpt-6-astra"), "Hello", "", None, None, requested, None,
                    )
                    self.assertEqual(params["max_completion_tokens"], expected)


class JudgeParameterTests(unittest.IsolatedAsyncioTestCase):
    async def test_judge_uses_discovered_capabilities(self):
        for model, token_param, budget in (
            ("gpt-6-astra", "max_completion_tokens", config.JUDGE_MAX_TOKENS),
            ("gpt-5.4-mini", "max_completion_tokens", config.JUDGE_MAX_TOKENS),
            ("gpt-4o", "max_tokens", config.JUDGE_MAX_TOKENS_NONREASONING),
        ):
            with self.subTest(model=model):
                meta = model_entry(model)
                response = SimpleNamespace(choices=[SimpleNamespace(
                    finish_reason="stop",
                    message=SimpleNamespace(content='{"winner":"tie","scores":{},"rationale":"Equal"}'),
                )])
                create = AsyncMock(return_value=response)
                client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
                with patch.object(judge, "pick_judge_model", return_value=(meta, "test")), \
                     patch.object(judge, "get_openai_client", new=AsyncMock(return_value=client)):
                    result = await judge.judge("Hello", "Answer A", "Answer B", "candidate-a", "candidate-b")
                self.assertNotIn("error", result)
                create.assert_awaited_once()
                params = create.call_args.kwargs
                self.assertEqual(params[token_param], budget)
                if token_param == "max_completion_tokens":
                    self.assertNotIn("max_tokens", params)
                    self.assertNotIn("temperature", params)
                else:
                    self.assertNotIn("max_completion_tokens", params)
                    self.assertEqual(params["temperature"], 0)


if __name__ == "__main__":
    unittest.main()
