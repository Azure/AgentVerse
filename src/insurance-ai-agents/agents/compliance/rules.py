"""Business rules for the Compliance Agent.

THIS IS THE KEY FILE FOR THE "WOW MOMENT" IN THE DEMO.
During the regulatory change demo, this file is modified via a PR to show
how business rules can be updated with full governance and traceability.

Current regulations: EU Insurance Directive 2024 / Spanish DGS Guidelines
Last updated: 2024-01-15
"""

# =============================================================================
# REGULATORY THRESHOLDS
# =============================================================================

RULES = {
    # Maximum amount for automatic approval without human review
    "auto_approve_max_amount": 20000,

    # Threshold above which human review is MANDATORY (None = no threshold)
    # NOTE: When regulators require mandatory human review above a certain
    # amount, set this value accordingly.
    "human_review_threshold": None,

    # Fraud probability threshold for automatic rejection
    "fraud_auto_reject_threshold": 0.8,

    # Maximum risk score for automatic approval
    "max_risk_score_auto_approve": 7,

    # Minimum years as customer for fast-track processing
    "fast_track_min_years": 3,
}

# =============================================================================
# COMPLIANCE CHECKS
# =============================================================================

REGULATIONS = [
    {
        "id": "REG-EU-2024-001",
        "name": "EU Insurance Distribution Directive",
        "description": "All claim decisions must be documented with full reasoning",
        "applies_to": "all_claims",
    },
    {
        "id": "REG-ES-DGS-2024-001",
        "name": "DGS - Protección del Asegurado",
        "description": "Claims must be processed within 30 business days",
        "applies_to": "all_claims",
    },
    {
        "id": "REG-ES-DGS-2024-002",
        "name": "DGS - Anti-Fraude",
        "description": "High-risk claims must undergo enhanced due diligence",
        "applies_to": "high_risk",
    },
    {
        "id": "REG-EU-2024-002",
        "name": "EU AI Act - Transparency",
        "description": "AI-assisted decisions must include explanation and human override option",
        "applies_to": "ai_decisions",
    },
]


def get_applicable_regulations(claim_amount: float, risk_score: float) -> list:
    """Return the list of regulations applicable to this claim."""
    applicable = []
    for reg in REGULATIONS:
        if reg["applies_to"] == "all_claims":
            applicable.append(reg)
        elif reg["applies_to"] == "high_risk" and risk_score >= 6:
            applicable.append(reg)
        elif reg["applies_to"] == "ai_decisions":
            applicable.append(reg)
    return applicable


def evaluate_compliance(
    claim_amount: float,
    risk_score: float,
    fraud_probability: str,
) -> dict:
    """Evaluate a claim against current business rules and regulations.
    
    Returns a decision recommendation based on the rules.
    """
    decision = "approve"
    reasons = []
    regulations_checked = get_applicable_regulations(claim_amount, risk_score)

    # Check fraud threshold
    fraud_scores = {"low": 0.2, "medium": 0.5, "high": 0.9}
    fraud_value = fraud_scores.get(fraud_probability, 0.5)

    if fraud_value >= RULES["fraud_auto_reject_threshold"]:
        decision = "reject"
        reasons.append(
            f"Probabilidad de fraude ({fraud_probability}) supera el umbral de rechazo "
            f"({RULES['fraud_auto_reject_threshold']})"
        )

    # Check human review threshold (THE KEY RULE for WOW moment)
    if RULES["human_review_threshold"] is not None:
        if claim_amount > RULES["human_review_threshold"]:
            if decision != "reject":
                decision = "human_review"
            reasons.append(
                f"El monto del siniestro ({claim_amount}€) supera el umbral de revisión humana "
                f"obligatoria ({RULES['human_review_threshold']}€)"
            )

    # Check auto-approve limits
    if claim_amount > RULES["auto_approve_max_amount"]:
        if decision == "approve":
            decision = "human_review"
        reasons.append(
            f"El monto del siniestro ({claim_amount}€) supera el límite de aprobación automática "
            f"({RULES['auto_approve_max_amount']}€)"
        )

    # Check risk score
    if risk_score > RULES["max_risk_score_auto_approve"]:
        if decision == "approve":
            decision = "human_review"
        reasons.append(
            f"El score de riesgo ({risk_score}) supera el máximo permitido para aprobación automática "
            f"({RULES['max_risk_score_auto_approve']})"
        )

    if not reasons:
        reasons.append("Todos los controles superados · apto para aprobación automática")

    return {
        "decision": decision,
        "reasons": reasons,
        "regulations_checked": [r["id"] for r in regulations_checked],
        "rules_applied": {
            "auto_approve_max_amount": RULES["auto_approve_max_amount"],
            "human_review_threshold": RULES["human_review_threshold"],
            "fraud_auto_reject_threshold": RULES["fraud_auto_reject_threshold"],
            "max_risk_score_auto_approve": RULES["max_risk_score_auto_approve"],
        },
    }
