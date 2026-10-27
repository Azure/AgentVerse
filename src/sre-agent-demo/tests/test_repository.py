"""Replay contract tests, using the ASGI app without network or extra dependencies."""
import asyncio
import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from app.backend import config, scenarios
from app.backend.main import app
from app.backend.repository import APPROVAL_STATUS, DISCLAIMER, FOLLOW_UPS, build_draft


async def request(path, method="GET"):
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await app({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "root_path": "", "headers": [],
        "client": ("127.0.0.1", 1), "server": ("test", 80),
    }, receive, send)
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, json.loads(body)


class RepositoryDraftTests(unittest.TestCase):
    def test_every_incident_has_the_deliberate_outcome(self):
        expected = {
            "aca-5xx-oom": "pr", "aks-crashloop-secret": "pr",
            "sql-dtu-saturation": "pr", "cosmos-429-throttle": "issue",
            "appservice-cert-expiry": "issue", "private-endpoint-dns": "pr",
        }
        self.assertEqual(set(expected), {s["id"] for s in scenarios.SCENARIOS})
        self.assertEqual(set(expected), set(FOLLOW_UPS))
        for summary in scenarios.list_scenarios():
            with self.subTest(scenario=summary["id"]):
                self.assertEqual(summary["repository_outcome"], expected[summary["id"]])
                self.assertNotIn("turns", summary)

    def test_exports_are_complete_explicitly_simulated_and_not_approved(self):
        for scenario in scenarios.SCENARIOS:
            with self.subTest(scenario=scenario["id"]):
                draft = build_draft(scenario)
                markdown = draft["markdown"]
                self.assertIn(DISCLAIMER, markdown)
                self.assertIn(APPROVAL_STATUS, markdown)
                self.assertIn("NOT an applicable patch", markdown)
                self.assertIn("example-org/", draft["repository"])
                self.assertIn("## Root cause (simulated)", markdown)
                self.assertIn("## Rollback / containment", markdown)
                self.assertIn("## Incident memory, runbook and regression prevention", markdown)
                self.assertIn("## Validation / acceptance criteria (not run)", markdown)
                self.assertGreaterEqual(markdown.count("- [ ]"), 7)
                self.assertTrue(draft["filename"].endswith("-draft.md"))
                for turn in scenario["turns"]:
                    if turn["role"] == "tool":
                        self.assertIn(turn["kql"], markdown)
                        self.assertIn(turn["result"], markdown)
                    if turn["title"] == "Root cause":
                        self.assertIn(turn["text"], markdown)
                if draft["kind"] == "pr":
                    self.assertIn("not a code diff", markdown)
                    self.assertIn("**Suggested branch:**", markdown)
                else:
                    self.assertNotIn("**Suggested branch:**", markdown)

    def test_rendering_never_mutates_or_duplicates_seeded_turns(self):
        before = deepcopy(scenarios.SCENARIOS)
        for scenario in scenarios.SCENARIOS:
            first = scenarios.get_scenario(scenario["id"])
            second = scenarios.get_scenario(scenario["id"])
            self.assertEqual(first, second)
            self.assertEqual(first["turns"][:-1], scenario["turns"])
            self.assertEqual(first["turns"][-1]["role"], "repository")
            first["turns"][-1]["draft"]["title"] = "Client mutation"
            self.assertNotEqual(first, second)
        self.assertEqual(before, scenarios.SCENARIOS)

    def test_missing_evidence_fails_instead_of_fabricating_a_root_cause(self):
        scenario = deepcopy(scenarios.SCENARIOS[0])
        scenario["turns"] = [t for t in scenario["turns"] if t["title"] != "Root cause"]
        with self.assertRaises(StopIteration):
            build_draft(scenario)

    def test_http_list_and_detail_export_the_same_content(self):
        status, listing = asyncio.run(request("/api/scenarios"))
        self.assertEqual(status, 200)
        for summary in listing["scenarios"]:
            with self.subTest(scenario=summary["id"]):
                status, detail = asyncio.run(request(f"/api/scenarios/{summary['id']}"))
                self.assertEqual(status, 200)
                turn = detail["turns"][-1]
                self.assertEqual(turn["role"], "repository")
                self.assertEqual(turn["draft"]["kind"], summary["repository_outcome"])
                seed = next(s for s in scenarios.SCENARIOS if s["id"] == summary["id"])
                self.assertEqual(turn["draft"], build_draft(seed))

    def test_unknown_incident_and_write_methods_remain_rejected(self):
        status, body = asyncio.run(request("/api/scenarios/missing"))
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "scenario not found")
        for path in ("/api/scenarios", "/api/scenarios/aca-5xx-oom"):
            status, _ = asyncio.run(request(path, "POST"))
            self.assertEqual(status, 405)

    def test_write_and_approval_flags_cannot_enable_github_writes(self):
        with patch.object(config, "SRE_AGENT_ALLOW_WRITE", True), \
                patch.object(config, "SRE_AGENT_ALLOW_APPROVALS", True):
            status, body = asyncio.run(request("/api/config"))
        self.assertEqual(status, 200)
        for flag in ("writes_enabled", "approvals_enabled", "github_writes_enabled"):
            self.assertIs(body[flag], False)
        self.assertIn("no GitHub writes", body["note"])


if __name__ == "__main__":
    unittest.main()
