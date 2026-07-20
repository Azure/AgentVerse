"""Seeded, deterministic SRE incident-investigation scenarios (replay mode).

These transcripts are hand-authored to mirror how the Azure SRE Agent actually
works — ingest a signal, query telemetry through its connectors (Azure Monitor /
Log Analytics / Application Insights, surfaced as Kusto), form and test a
hypothesis, reach a root cause, and propose a remediation that a human approves in
Review mode. Nothing here calls Azure; it is illustrative content for the demo.

Each "turn" has a `role` (signal | agent | tool | approval | resolution) so the UI
can render an investigation timeline. Doc links are official Microsoft Learn pages.
"""
from __future__ import annotations

from typing import Any, Dict, List

DOCS: Dict[str, str] = {
    "overview": "https://learn.microsoft.com/azure/sre-agent/overview",
    "how_it_works": "https://learn.microsoft.com/azure/sre-agent/how-it-works",
    "modes": "https://learn.microsoft.com/azure/sre-agent/agent-modes",
    "approvals": "https://learn.microsoft.com/azure/sre-agent/approvals",
    "connectors": "https://learn.microsoft.com/azure/sre-agent/connectors",
    "incident": "https://learn.microsoft.com/azure/sre-agent/incident-management",
    "rbac": "https://learn.microsoft.com/azure/sre-agent/rbac",
    "api": "https://learn.microsoft.com/azure/sre-agent/api-reference",
    "billing": "https://learn.microsoft.com/azure/sre-agent/pricing-billing",
    "security": "https://learn.microsoft.com/azure/sre-agent/security",
    "waf": "https://learn.microsoft.com/azure/well-architected/",
    "waf_ops": "https://learn.microsoft.com/azure/well-architected/operational-excellence/",
    "waf_reliability": "https://learn.microsoft.com/azure/well-architected/reliability/",
    "waf_security": "https://learn.microsoft.com/azure/well-architected/security/",
}


SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "aca-5xx-oom",
        "title": "Container App 5xx spike after a bad rollout",
        "summary": "checkout-api starts returning HTTP 500s minutes after a new "
                   "revision. The SRE Agent traces it to an OOM crash loop caused by a "
                   "raised memory limit removed in the last deploy, and proposes a "
                   "revision rollback for human approval.",
        "service": "checkout-api (Azure Container Apps)",
        "severity": "Sev2",
        "mode": "Review",
        "waf": ["Reliability", "Operational Excellence"],
        "signal": {
            "source": "Azure Monitor alert",
            "title": "HTTP 5xx rate > 5% for 5 min on checkout-api",
            "fired_at": "08:41 UTC",
        },
        "turns": [
            {"role": "signal", "title": "Alert received",
             "text": "Azure Monitor fired 'checkout-api 5xx > 5%'. The agent opens an "
                     "investigation thread and correlates it with recent change events."},
            {"role": "agent", "title": "Establish a baseline",
             "text": "5xx jumped from ~0.1% to 34% at 08:38 UTC. A new revision "
                     "checkout-api--rev-0042 was activated at 08:36 UTC — two minutes "
                     "before the spike. Prime suspect: the rollout."},
            {"role": "tool", "title": "Query system logs (Log Analytics)",
             "tool": "Log Analytics connector",
             "kql": "ContainerAppSystemLogs_CL\n| where ContainerAppName_s == 'checkout-api'\n"
                    "| where TimeGenerated > ago(30m)\n| summarize count() by Reason_s, bin(TimeGenerated, 1m)",
             "result": "Reason 'OOMKilled' appears 214 times starting 08:37 UTC; replicas "
                       "restart every ~40s (crash loop)."},
            {"role": "tool", "title": "Diff the revision (ARM)",
             "tool": "Azure Resource Manager",
             "kql": "GET .../containerApps/checkout-api/revisions/rev-0042\n"
                    "GET .../containerApps/checkout-api/revisions/rev-0041",
             "result": "rev-0041 requested memory 1.0Gi; rev-0042 requested 0.5Gi. The "
                       "image and traffic are unchanged — only the memory limit dropped."},
            {"role": "agent", "title": "Root cause",
             "text": "The new revision halved the container memory limit. The app's steady-"
                     "state working set (~0.7Gi) now exceeds 0.5Gi, so the platform OOM-"
                     "kills every replica, producing a crash loop and 5xx responses."},
            {"role": "approval", "title": "Proposed remediation (needs approval)",
             "action": "Shift 100% traffic back to revision rev-0041 (last healthy) and "
                       "deactivate rev-0042.",
             "risk": "Low — rev-0041 ran healthy for 6 days. Reversible in one step.",
             "text": "Agent is in Review mode: it will NOT act until an SRE Agent User "
                     "approves. This demo shows the approval card read-only."},
            {"role": "resolution", "title": "After approval (expected)",
             "text": "Traffic returns to rev-0041; OOMKilled events stop within ~1 min and "
                     "5xx falls back under 0.2%. Agent files a note recommending the memory "
                     "limit be restored to 1.0Gi (or the working set profiled) before redeploy."},
        ],
        "links": [
            {"label": "How the SRE Agent works", "url": DOCS["how_it_works"]},
            {"label": "Agent modes (Review / Automatic / ReadOnly)", "url": DOCS["modes"]},
            {"label": "Approvals (human-in-the-loop)", "url": DOCS["approvals"]},
            {"label": "WAF — Reliability pillar", "url": DOCS["waf_reliability"]},
        ],
    },
    {
        "id": "aks-crashloop-secret",
        "title": "AKS pods CrashLoopBackOff after a secret rotation",
        "summary": "A payments deployment on AKS goes NotReady right after a Key Vault "
                   "secret rotation. The agent finds the pods can't mount an expired "
                   "secret reference and proposes syncing the CSI secret, gated on approval.",
        "service": "payments-svc (Azure Kubernetes Service)",
        "severity": "Sev2",
        "mode": "Review",
        "waf": ["Reliability", "Security", "Operational Excellence"],
        "signal": {
            "source": "Container Insights",
            "title": "payments-svc availability < 50% (3/6 replicas Ready)",
            "fired_at": "22:03 UTC",
        },
        "turns": [
            {"role": "signal", "title": "Alert received",
             "text": "Container Insights reports payments-svc dropped below 50% ready "
                     "replicas. Agent opens an investigation and pulls pod events."},
            {"role": "tool", "title": "Pod events (Container Insights)",
             "tool": "Log Analytics connector",
             "kql": "KubeEvents\n| where Namespace == 'payments' and Name startswith 'payments-svc'\n"
                    "| where TimeGenerated > ago(20m)\n| project TimeGenerated, Reason, Message",
             "result": "Reason 'CrashLoopBackOff'; message 'secret \"pay-signing-key\" not "
                       "found' on 3 pods created after 22:00 UTC."},
            {"role": "agent", "title": "Correlate with change events",
             "text": "A Key Vault rotation of 'pay-signing-key' completed at 21:59 UTC. New "
                     "pods reference a SecretProviderClass that still points at the previous "
                     "secret version; older pods (mounted before rotation) are still Ready."},
            {"role": "tool", "title": "Inspect the CSI mount (ARM + cluster read)",
             "tool": "Azure Resource Manager",
             "kql": "GET SecretProviderClass payments/pay-signing-key\nGET KeyVault secret versions",
             "result": "SecretProviderClass pins objectVersion=<old>; Key Vault now serves a "
                       "newer enabled version. The pinned version was disabled by rotation."},
            {"role": "agent", "title": "Root cause",
             "text": "Secret rotation disabled the pinned Key Vault secret version while the "
                     "CSI SecretProviderClass still references it, so new pods fail to mount "
                     "it and crash loop. This is a config drift, not a code defect."},
            {"role": "approval", "title": "Proposed remediation (needs approval)",
             "action": "Update the SecretProviderClass to track the latest secret version "
                       "(remove the pinned objectVersion) and roll the deployment.",
             "risk": "Medium — touches auth material; scoped to the payments namespace. "
                     "Reversible by re-pinning. Recommend Review mode + change window.",
             "text": "Agent stays in Review mode. In a public demo, approvals are shown "
                     "read-only and never executed."},
            {"role": "resolution", "title": "After approval (expected)",
             "text": "New pods mount the current secret version and reach Ready; availability "
                     "returns to 100%. Agent recommends enabling autorotation on the CSI "
                     "driver so future rotations don't require manual sync."},
        ],
        "links": [
            {"label": "Connectors (Azure Monitor / Log Analytics)", "url": DOCS["connectors"]},
            {"label": "RBAC roles", "url": DOCS["rbac"]},
            {"label": "WAF — Security pillar", "url": DOCS["waf_security"]},
        ],
    },
    {
        "id": "sql-dtu-saturation",
        "title": "API latency from Azure SQL DTU saturation",
        "summary": "orders-api p95 latency triples. The agent isolates it to Azure SQL "
                   "DTU exhaustion driven by a missing index after a query change, and "
                   "proposes a temporary tier bump plus an index, both approval-gated.",
        "service": "orders-api → Azure SQL Database",
        "severity": "Sev3",
        "mode": "Review",
        "waf": ["Performance Efficiency", "Reliability"],
        "signal": {
            "source": "Application Insights",
            "title": "orders-api p95 latency > 2s (baseline 600ms)",
            "fired_at": "14:12 UTC",
        },
        "turns": [
            {"role": "signal", "title": "Alert received",
             "text": "Application Insights shows orders-api p95 latency climbing since "
                     "14:05 UTC. Agent opens an investigation and traces dependencies."},
            {"role": "tool", "title": "Dependency breakdown (App Insights)",
             "tool": "Application Insights connector",
             "kql": "dependencies\n| where cloud_RoleName == 'orders-api' and timestamp > ago(1h)\n"
                    "| summarize p95=percentile(duration,95) by target, bin(timestamp,5m)",
             "result": "Latency is concentrated in the 'sql:ordersdb' dependency (p95 1.9s); "
                       "app-tier CPU and outbound calls are flat."},
            {"role": "tool", "title": "Database utilisation (Azure Monitor metrics)",
             "tool": "Azure Monitor",
             "kql": "AzureMetrics\n| where Resource == 'ORDERSDB' and MetricName == 'dtu_consumption_percent'\n"
                    "| summarize avg(Average) by bin(TimeGenerated, 5m)",
             "result": "DTU consumption pinned at 100% since 14:04 UTC (baseline ~45%). "
                       "Query Store shows one query's reads up 20x."},
            {"role": "agent", "title": "Root cause",
             "text": "A deploy at 14:03 UTC changed the orders list query to filter on "
                     "customer_id, which has no index → full table scans saturate DTUs and "
                     "serialise every other query, tripling p95 latency."},
            {"role": "approval", "title": "Proposed remediation (needs approval)",
             "action": "1) Temporarily scale the DB S2→S4 to absorb load; 2) create a "
                       "nonclustered index on Orders(customer_id) online; 3) scale back after.",
             "risk": "Low/Medium — online index build; brief tier change has cost impact. "
                     "Fully reversible.",
             "text": "Review mode: the agent proposes; a human approves each step. Shown "
                     "read-only in this demo."},
            {"role": "resolution", "title": "After approval (expected)",
             "text": "The index removes the scans; DTU drops to ~40% and p95 returns to "
                     "~600ms, after which the tier is scaled back to S2. Agent recommends "
                     "adding the index to the schema migration to prevent recurrence."},
        ],
        "links": [
            {"label": "Incident management", "url": DOCS["incident"]},
            {"label": "API reference (control + data plane)", "url": DOCS["api"]},
            {"label": "WAF — Operational Excellence", "url": DOCS["waf_ops"]},
        ],
    },
    {
        "id": "cosmos-429-throttle",
        "title": "Cosmos DB 429 throttling from a hot partition",
        "summary": "cart-api starts failing intermittently with 429s during a flash sale. "
                   "The SRE Agent isolates it to a Cosmos container capped at manual "
                   "throughput with a hot partition, and proposes enabling autoscale "
                   "for approval.",
        "service": "cart-api → Azure Cosmos DB (NoSQL)",
        "severity": "Sev2",
        "mode": "Review",
        "waf": ["Performance Efficiency", "Reliability"],
        "signal": {
            "source": "Application Insights",
            "title": "cart-api dependency failures > 8% (HTTP 429)",
            "fired_at": "19:24 UTC",
        },
        "turns": [
            {"role": "signal", "title": "Alert received",
             "text": "Application Insights reports a jump in failed 'cosmos:cartdb' calls. "
                     "Agent opens an investigation during a promotion traffic spike."},
            {"role": "tool", "title": "Failed dependencies (App Insights)",
             "tool": "Application Insights connector",
             "kql": "dependencies\n| where type == 'Azure DocumentDB' and success == false\n"
                    "| where timestamp > ago(30m)\n| summarize count() by resultCode, bin(timestamp,5m)",
             "result": "resultCode 429 ('Request rate too large') dominates, starting 19:20 "
                       "UTC as traffic climbs; other codes flat."},
            {"role": "tool", "title": "Throughput & partition metrics (Azure Monitor)",
             "tool": "Azure Monitor",
             "kql": "AzureMetrics\n| where Resource == 'CARTDB'\n"
                    "| where MetricName in ('NormalizedRUConsumption','ProvisionedThroughput')\n"
                    "| summarize max(Maximum) by MetricName, bin(TimeGenerated,5m)",
             "result": "Container 'sessions' is manual 10,000 RU/s; NormalizedRUConsumption "
                       "hits 100% on a single partition key range while total RU stays ~60%."},
            {"role": "agent", "title": "Root cause",
             "text": "A hot partition (a few popular SKUs) saturates one physical partition's "
                     "share of a manually capped 10,000 RU/s, so requests to it are throttled "
                     "with 429 even though aggregate utilisation looks moderate."},
            {"role": "approval", "title": "Proposed remediation (needs approval)",
             "action": "Enable autoscale (max 40,000 RU/s) on the 'sessions' container to "
                       "absorb the promotion peak; file a follow-up to improve the partition "
                       "key / add caching for hot SKUs.",
             "risk": "Low — autoscale only bills for consumed RU/s; reversible. Does not fix "
                     "the skew, only the immediate throttling.",
             "text": "Review mode: the agent proposes; a human approves. Shown read-only here."},
            {"role": "resolution", "title": "After approval (expected)",
             "text": "Autoscale absorbs the peak; 429s drop to near zero within minutes and "
                     "cart-api recovers. Agent recommends a higher-cardinality partition key "
                     "and read caching so a single SKU can't monopolise a partition."},
        ],
        "links": [
            {"label": "Connectors (Azure Monitor / App Insights)", "url": DOCS["connectors"]},
            {"label": "Agent modes", "url": DOCS["modes"]},
            {"label": "WAF — Performance Efficiency", "url": DOCS["waf"]},
        ],
    },
    {
        "id": "appservice-cert-expiry",
        "title": "HTTPS outage from an expired TLS certificate",
        "summary": "Users get certificate errors on the public web app. The SRE Agent finds "
                   "the custom-domain TLS certificate expired overnight and autorenew was "
                   "disabled, and proposes rebinding a fresh App Service managed certificate.",
        "service": "www-portal (Azure App Service)",
        "severity": "Sev1",
        "mode": "Review",
        "waf": ["Security", "Reliability", "Operational Excellence"],
        "signal": {
            "source": "Azure Monitor availability test",
            "title": "www-portal HTTPS availability 0% — TLS handshake failing",
            "fired_at": "00:07 UTC",
        },
        "turns": [
            {"role": "signal", "title": "Alert received",
             "text": "An availability test reports the HTTPS endpoint down with a certificate "
                     "error, while HTTP redirects still respond. Agent opens a Sev1 thread."},
            {"role": "tool", "title": "Availability failures (Azure Monitor)",
             "tool": "Azure Monitor",
             "kql": "AzureMetrics\n| where Resource == 'WWW-PORTAL' and MetricName == 'HealthCheckStatus'\n"
                    "| where TimeGenerated > ago(1h)\n| summarize min(Minimum) by bin(TimeGenerated,5m)",
             "result": "Health check fails from 00:02 UTC; probe detail 'certificate has "
                       "expired' (SEC_E_CERT_EXPIRED). No deploy or config change in the window."},
            {"role": "tool", "title": "Inspect TLS binding (ARM)",
             "tool": "Azure Resource Manager",
             "kql": "GET .../sites/www-portal/hostNameBindings\nGET .../certificates?$filter=...",
             "result": "The custom domain binds a certificate with NotAfter = today 00:00 UTC; "
                       "canonicalName shows autorenew was turned off during a prior manual "
                       "upload. No newer certificate is bound."},
            {"role": "agent", "title": "Root cause",
             "text": "The TLS certificate for the custom domain expired at 00:00 UTC and "
                     "automatic renewal had been disabled, so the platform served an expired "
                     "cert and every HTTPS handshake failed — a full customer-facing outage."},
            {"role": "approval", "title": "Proposed remediation (needs approval)",
             "action": "Issue a fresh App Service managed certificate for the domain, rebind "
                       "it to the HTTPS listener, and re-enable automatic renewal.",
             "risk": "Low — additive rebind, no code change; restores HTTPS immediately. "
                     "Domain validation must succeed (DNS already points at the app).",
             "text": "Review mode with human approval. For this security-sensitive change the "
                     "demo keeps the approval read-only."},
            {"role": "resolution", "title": "After approval (expected)",
             "text": "The managed certificate is bound and HTTPS recovers within minutes; "
                     "availability returns to 100%. Agent recommends a scheduled task that "
                     "alerts 30 days before any certificate expiry to prevent recurrence."},
        ],
        "links": [
            {"label": "Agent modes (Review / ReadOnly)", "url": DOCS["modes"]},
            {"label": "Security guidance", "url": DOCS["security"]},
            {"label": "WAF — Security pillar", "url": DOCS["waf_security"]},
        ],
    },
    {
        "id": "private-endpoint-dns",
        "title": "Key Vault access failing after a private endpoint change",
        "summary": "orders-worker suddenly can't read secrets from Key Vault after a "
                   "networking change. The SRE Agent traces it to a private DNS zone missing "
                   "the vault's A record, and proposes restoring the private DNS link.",
        "service": "orders-worker → Azure Key Vault (private endpoint)",
        "severity": "Sev2",
        "mode": "Review",
        "waf": ["Security", "Reliability"],
        "signal": {
            "source": "Application Insights",
            "title": "orders-worker exceptions: Key Vault name resolution failed",
            "fired_at": "11:48 UTC",
        },
        "turns": [
            {"role": "signal", "title": "Alert received",
             "text": "orders-worker exception rate spikes. Agent opens an investigation and "
                     "pulls the exception detail and recent infrastructure changes."},
            {"role": "tool", "title": "Exception detail (App Insights)",
             "tool": "Application Insights connector",
             "kql": "exceptions\n| where cloud_RoleName == 'orders-worker' and timestamp > ago(30m)\n"
                    "| summarize count() by type, outerMessage",
             "result": "SocketException 'Name or service not known' resolving "
                       "kv-orders.vault.azure.net; began 11:44 UTC. No app deploy in the window."},
            {"role": "agent", "title": "Correlate with change events",
             "text": "Activity log shows a private DNS zone 'privatelink.vaultcore.azure.net' "
                     "was modified at 11:43 UTC. Public access on the vault is disabled, so the "
                     "worker must resolve it via the private endpoint's DNS A record."},
            {"role": "tool", "title": "Inspect DNS + private endpoint (ARM)",
             "tool": "Azure Resource Manager",
             "kql": "GET privateDnsZones/privatelink.vaultcore.azure.net/A\n"
                    "GET .../privateEndpoints/kv-orders-pe (customDnsConfigs)",
             "result": "The private endpoint exists with IP 10.20.3.12, but the A record for "
                       "'kv-orders' was removed from the private DNS zone during the change; "
                       "the vnet link is intact."},
            {"role": "agent", "title": "Root cause",
             "text": "The networking change deleted the Key Vault's A record from the private "
                     "DNS zone, so with public access disabled the worker can no longer resolve "
                     "the vault to its private IP and every secret read fails — config drift, "
                     "not a code or credential issue."},
            {"role": "approval", "title": "Proposed remediation (needs approval)",
             "action": "Recreate the A record 'kv-orders' → 10.20.3.12 in the private DNS "
                       "zone (or re-enable the private endpoint's DNS zone group so it is "
                       "managed automatically).",
             "risk": "Low — restores a missing DNS record scoped to the private zone; "
                     "reversible. No change to the vault's data or access policies.",
             "text": "Review mode: proposed, not executed. Shown read-only in this demo."},
            {"role": "resolution", "title": "After approval (expected)",
             "text": "DNS resolution returns the private IP and secret reads recover within a "
                     "minute. Agent recommends locking the private DNS zone group and adding a "
                     "resolution health probe so drift is caught before it breaks workloads."},
        ],
        "links": [
            {"label": "Connectors", "url": DOCS["connectors"]},
            {"label": "RBAC roles", "url": DOCS["rbac"]},
            {"label": "WAF — Reliability pillar", "url": DOCS["waf_reliability"]},
        ],
    },
]


CAPABILITIES: List[Dict[str, str]] = [
    {"title": "Signal-driven investigations",
     "text": "Reacts to Azure Monitor / PagerDuty / ServiceNow incidents and scheduled "
             "checks, opening a thread and correlating with recent change events.",
     "doc": DOCS["incident"]},
    {"title": "Telemetry connectors",
     "text": "Queries Log Analytics, Application Insights and Azure Data Explorer (Kusto), "
             "plus MCP connectors, to gather evidence — no custom glue code.",
     "doc": DOCS["connectors"]},
    {"title": "Human-in-the-loop by design",
     "text": "Review mode requires explicit approval before any change; ReadOnly mode never "
             "acts; Automatic is opt-in. Approvals are audited.",
     "doc": DOCS["approvals"]},
    {"title": "Least-privilege RBAC",
     "text": "Administrator / User / Reader roles on the agent resource; the agent's own "
             "execution identity should be scoped to the resources it operates.",
     "doc": DOCS["rbac"]},
    {"title": "Programmable (control + data plane)",
     "text": "ARM control plane manages the agent; a per-agent data plane exposes threads, "
             "messages, approvals and SignalR streaming (api-version 2025-05-01-preview, preview).",
     "doc": DOCS["api"]},
    {"title": "Cost awareness",
     "text": "Billed in agent units; chat is a billable operation and always-on flow accrues "
             "cost until the agent is deleted. Set monthly caps and a cleanup runbook.",
     "doc": DOCS["billing"]},
]


WAF_NOTES: List[Dict[str, str]] = [
    {"pillar": "Reliability",
     "text": "The agent shortens detection→diagnosis→mitigation for incidents and proposes "
             "reversible remediations, improving MTTR.",
     "doc": DOCS["waf_reliability"]},
    {"pillar": "Security",
     "text": "Human-in-the-loop approvals, least-privilege RBAC and audited actions keep the "
             "agent from taking unbounded action. For demos, use a dedicated sandbox agent, "
             "keep approvals disabled and never point it at production.",
     "doc": DOCS["waf_security"]},
    {"pillar": "Operational Excellence",
     "text": "Investigations, evidence and recommended fixes are captured as a repeatable, "
             "auditable workflow instead of tribal knowledge.",
     "doc": DOCS["waf_ops"]},
]


def list_scenarios() -> List[Dict[str, Any]]:
    return [
        {"id": s["id"], "title": s["title"], "summary": s["summary"],
         "service": s["service"], "severity": s["severity"], "mode": s["mode"],
         "waf": s["waf"]}
        for s in SCENARIOS
    ]


def get_scenario(scenario_id: str) -> Dict[str, Any] | None:
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return s
    return None
