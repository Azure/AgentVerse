from __future__ import annotations

from agentverse.contracts import DocumentContext, DocumentType
from agentverse.history_snapshots import HistorySnapshotBuilder


def test_financial_snapshot_exposes_pedro_vigo_baseline() -> None:
    context = DocumentContext(
        document_id="upload-test",
        source_uri="upload://withdrawal_order_high_risk.pdf",
        document_type=DocumentType.FINANCIAL,
        document_subtype="withdrawal_order",
        route="financial",
        language="unknown",
        extracted_text="Pedro Alonso requests EUR 10,000 at Valencia Centro Branch.",
        fields={
            "account_id": "ACCT-2002",
            "requested_amount_eur": 10000,
            "location": "Valencia Centro Branch",
        },
        classification_confidence=0.95,
    )

    snapshot = HistorySnapshotBuilder().build(context)

    assert snapshot["account"]["holder"] == "Pedro Alonso"
    assert "Vigo Centro Branch" in snapshot["account"]["usual_locations"]
    assert snapshot["account"]["usual_withdrawal_max_eur"] == 900
    assert any(
        event["location"].startswith("Vigo") and event["type"] == "withdrawal"
        for event in snapshot["recent_transactions"]
    )
    assert any(
        event["description"] == "large same-day incoming transfer"
        for event in snapshot["recent_transactions"]
    )


def test_supply_snapshot_includes_inventory_demand_and_supply_history() -> None:
    context = DocumentContext(
        document_id="upload-supply",
        source_uri="upload://shipment_request.pdf",
        document_type=DocumentType.SUPPLY,
        document_subtype="shipment_notice",
        route="supply",
        language="unknown",
        extracted_text="MedSupply Iberia delivered gloves and masks for REQ-9001.",
        fields={
            "supplier": "MedSupply Iberia",
            "items": [
                {"product_id": "GLOVES_NITRILE", "received_quantity": 420, "requested_quantity": 800},
                {"product_id": "MASK_N95", "received_quantity": 80, "requested_quantity": 250},
            ],
        },
        classification_confidence=0.91,
    )

    snapshot = HistorySnapshotBuilder().build(context)

    glove = next(item for item in snapshot["inventory"] if item["product_id"] == "GLOVES_NITRILE")
    assert glove["demand_summary"]["average_period_demand"] > 0
    assert glove["recent_demand"]
    assert glove["recent_supply"]
    assert any(order["client_name"] == "Emergency Ward" for order in glove["to_send_matches"])
    assert any(order["client_name"] == "Lisbon Clinic" for order in snapshot["to_send_list"])
    assert any(row["product_id"] == "MASK_N95" for row in snapshot["demand_overview"])
