"""Local, illustrative repository follow-ups. No GitHub client or writes."""
from __future__ import annotations

from typing import Any


DISCLAIMER = (
    "Illustrative draft only - NOT a created GitHub issue or pull request, "
    "NOT an applicable patch. All evidence is simulated. Repository names, "
    "branches and paths are fictional examples; no repository was inspected. "
    "No live Azure calls or GitHub writes are made."
)
APPROVAL_STATUS = "Not requested - human review required before publication or changes."

FOLLOW_UPS: dict[str, dict[str, Any]] = {
    "aca-5xx-oom": {
        "kind": "pr",
        "repository": "example-org/checkout-api",
        "title": "Restore checkout memory allocation and guard against OOM regressions",
        "reviewer": "Application and platform maintainers",
        "change": "Restore the declared container memory limit from 0.5Gi to the last "
                  "healthy 1.0Gi. Keep the image and traffic configuration unchanged. "
                  "This durable fix follows, rather than authorizes, the proposed rollback.",
        "files": ["infra/checkout.tf", "tests/test_memory_budget.py"],
        "validation": [
            "In a sandbox, the rendered deployment requests 1.0Gi and passes IaC validation.",
            "Replay the incident load for 15 minutes: no OOMKilled events and HTTP 5xx < 0.2%.",
            "A regression check rejects a 0.5Gi limit for the measured 0.7Gi working set.",
        ],
        "rollback": "Reject or revert the proposed configuration change and keep the last "
                    "healthy revision serving traffic. Do not route traffic to rev-0042.",
        "prevention": "Record the working-set evidence and rollback decision in "
                      "docs/runbooks/checkout-oom.md; run the memory-budget regression in CI.",
    },
    "aks-crashloop-secret": {
        "kind": "pr",
        "repository": "example-org/payments-svc",
        "title": "Remove the stale CSI secret version pin and test rotation",
        "reviewer": "Payments maintainers and security reviewers",
        "change": "Propose removing the obsolete objectVersion pin from SecretProviderClass. "
                  "Review compatibility with the current signing key and CSI rotation settings "
                  "before rolling pods in the payments namespace. Never export secret values.",
        "files": ["deploy/secret-provider-class.yaml", "tests/test_secret_rotation.py"],
        "validation": [
            "In a sandbox, rotate a test secret and confirm new pods mount the enabled version.",
            "All 6/6 payments replicas become Ready and a synthetic signing check succeeds.",
            "Repeat rotation with autorotation configured; no stale version remains pinned.",
        ],
        "rollback": "Stop the rollout if signing compatibility fails. Re-pin only to a "
                    "security-approved, enabled version; never restore a disabled key blindly.",
        "prevention": "Document rotation and recovery in docs/runbooks/secret-rotation.md "
                      "and run a synthetic rotation regression before releases.",
    },
    "sql-dtu-saturation": {
        "kind": "pr",
        "repository": "example-org/orders-api",
        "title": "Add the customer lookup index through a reviewed schema migration",
        "reviewer": "Orders maintainers and database owners",
        "change": "Propose a migration for a nonclustered Orders(customer_id) index after "
                  "checking existing indexes, query plans and online-build support. "
                  "The temporary S2 to S4 mitigation is not a permanent capacity change.",
        "files": ["db/migrations/add_orders_customer_index.sql", "tests/test_orders_query.py"],
        "validation": [
            "Apply the migration to a sandbox copy; the customer query uses an index seek.",
            "At incident-equivalent load, p95 <= 600ms and DTU consumption <= 45% on S2.",
            "Verify migration re-run behavior and rollback without losing order data.",
        ],
        "rollback": "Have the database owner stop the migration or drop only the newly added "
                    "index if it regresses writes. Review capacity separately before scaling down.",
        "prevention": "Preserve the query-plan comparison in docs/runbooks/orders-latency.md "
                      "and add a query-plan/load regression to release checks.",
    },
    "cosmos-429-throttle": {
        "kind": "issue",
        "repository": "example-org/cart-api",
        "title": "Investigate hot-partition skew and validate a durable cart data design",
        "reviewer": "Cart maintainers and data platform owners",
        "change": "Evaluate partition-key cardinality and hot-SKU caching using a synthetic "
                  "flash-sale workload. Autoscale is only a proposed mitigation, not proof "
                  "that partition skew is fixed. Record tradeoffs before proposing a migration.",
        "files": ["docs/design/cart-partitioning.md", "tests/load/flash_sale.py"],
        "validation": [
            "Capture per-partition RU utilization and 429 rate before and after each candidate.",
            "At the same synthetic load, dependency failures stay below 1% for 15 minutes.",
            "Review consistency, cache invalidation, migration safety and cost before a PR.",
        ],
        "rollback": "Keep the current data model until a reviewed migration and recovery plan "
                    "exist. Revert experimental cache/partition changes in the sandbox only.",
        "prevention": "Attach the simulated incident record to docs/runbooks/cosmos-throttling.md "
                      "and retain a hot-key load regression; do not claim autoscale removes skew.",
    },
    "appservice-cert-expiry": {
        "kind": "issue",
        "repository": "example-org/www-portal",
        "title": "Assign certificate renewal ownership and add expiry checks",
        "reviewer": "Web platform owners and security reviewers",
        "change": "Track managed-certificate eligibility, renewal ownership and a scheduled "
                  "expiry check. Propose alerts at 30, 14 and 7 days before expiry. "
                  "Issuing or rebinding a certificate still requires separate human approval.",
        "files": ["docs/runbooks/tls-renewal.md", "tests/test_certificate_expiry.py"],
        "validation": [
            "A sandbox certificate inside the 30-day window triggers the expected alert.",
            "A synthetic HTTPS probe validates hostname, chain and validity after a test rebind.",
            "Document a renewal owner, escalation route and a successful sandbox renewal drill.",
        ],
        "rollback": "Keep a valid binding during testing. If a replacement fails validation, "
                    "restore a previously validated, unexpired certificate; never the expired one.",
        "prevention": "Save the incident timeline and renewal drill in docs/runbooks/tls-renewal.md "
                      "and run the expiry regression on a schedule.",
    },
    "private-endpoint-dns": {
        "kind": "pr",
        "repository": "example-org/orders-worker",
        "title": "Manage the Key Vault private DNS zone group in IaC and add a probe",
        "reviewer": "Networking and platform maintainers",
        "change": "Propose managing the private endpoint DNS zone group in IaC so the vault "
                  "record is maintained automatically. Preserve the existing VNet link and "
                  "disabled public access; do not hardcode the illustrative private IP.",
        "files": ["infra/key_vault_dns.tf", "tests/test_private_dns.py"],
        "validation": [
            "The IaC plan manages the DNS zone group without enabling public Key Vault access.",
            "From the sandbox worker VNet, the vault hostname resolves to the endpoint private IP.",
            "A synthetic secret-read probe succeeds without logging secret values; removing "
            "the DNS record in a sandbox makes the probe fail as expected.",
        ],
        "rollback": "Have the network owner restore the prior known-good private DNS record "
                    "and zone association. Keep public access disabled throughout recovery.",
        "prevention": "Capture the DNS drift evidence in docs/runbooks/key-vault-dns.md "
                      "and gate networking releases on the private-resolution regression.",
    },
}


def build_draft(scenario: dict[str, Any]) -> dict[str, Any]:
    """Render the same Markdown for preview and download from seeded evidence."""
    spec = FOLLOW_UPS[scenario["id"]]
    kind = spec["kind"]
    label = "PR proposal" if kind == "pr" else "Issue draft"
    root_cause = next(t["text"] for t in scenario["turns"] if t["title"] == "Root cause")
    lines = [
        f"# {spec['title']}", "", f"> {DISCLAIMER}", "",
        f"**Artifact:** {label}",
        f"**Illustrative repository:** `{spec['repository']}`",
        f"**Review required from:** {spec['reviewer']}",
        f"**Approval status:** {APPROVAL_STATUS}", "",
    ]
    branch = f"sre/{scenario['id']}"
    if kind == "pr":
        lines += [
            f"**Suggested branch:** `{branch}` -> `main` (illustrative base only)", "",
            "This is a change specification, not a code diff. Inspect the actual repository, "
            "implement and test the change on a branch before opening a PR.", "",
        ]
    lines += [
        "## Signal and impact (simulated)", "",
        f"- Scenario: `{scenario['id']}`",
        f"- Service: {scenario['service']} ({scenario['severity']})",
        f"- Signal: {scenario['signal']['title']} at {scenario['signal']['fired_at']}",
        f"- Impact: {scenario['summary']}", "",
        "## Investigation evidence (simulated, not observed live)", "",
    ]
    for turn in scenario["turns"]:
        if turn["role"] == "tool":
            lines += [
                f"### {turn['title']}", "", f"Source: {turn['tool']}", "",
                "```text", turn["kql"], "```", "", turn["result"], "",
            ]
    lines += [
        "## Root cause (simulated)", "", root_cause, "",
        "## Proposed durable change", "", spec["change"], "",
        "## Suggested files (fictional paths, not inspected)", "",
        *[f"- `{path}`" for path in spec["files"]], "",
        "## Validation / acceptance criteria (not run)", "",
        *[f"- [ ] {check}" for check in spec["validation"]], "",
        "## Rollback / containment (requires human review)", "", spec["rollback"], "",
        "## Incident memory, runbook and regression prevention (proposed)", "",
        spec["prevention"], "",
        "## Human handoff", "",
        "- [ ] Confirm the actual target repository, base branch and file paths.",
        "- [ ] Replace simulated evidence with reviewed, redacted observations.",
        "- [ ] Implement and validate any proposed change; attach real results.",
        "- [ ] A maintainer reviews publication and any subsequent merge or deployment.",
        "", "Downloading this file does not create, approve, merge or deploy anything.", "",
    ]
    return {
        "kind": kind,
        "repository": spec["repository"],
        "title": spec["title"],
        "reviewer": spec["reviewer"],
        "approval_status": APPROVAL_STATUS,
        "disclaimer": DISCLAIMER,
        "filename": f"{scenario['id']}-{kind}-draft.md",
        "markdown": "\n".join(lines),
    }
