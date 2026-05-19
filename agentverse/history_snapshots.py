"""Focused SQLite history snapshots for Foundry agent prompts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from agentverse.contracts import DocumentContext
from agentverse.paths import SIMULATED_DB_PATH


class HistorySnapshotBuilder:
    """Build compact, relevant history snapshots instead of dumping the whole database."""

    def __init__(self, db_path: Path = SIMULATED_DB_PATH) -> None:
        self._db_path = db_path

    def build(self, context: DocumentContext) -> dict[str, Any]:
        if context.route == "financial":
            return self._financial_snapshot(context)
        if context.route == "medical":
            return self._medical_snapshot(context)
        if context.route == "supply":
            return self._supply_snapshot(context)
        return {"note": "No specialized history snapshot for manual review route."}

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _financial_snapshot(self, context: DocumentContext) -> dict[str, Any]:
        fields = context.fields
        customer_id = str(fields.get("customer_id", ""))
        account_id = str(fields.get("account_id", ""))
        with self._connect() as conn:
            customer = self._one(conn, "SELECT * FROM financial_customers WHERE customer_id = ?", (customer_id,))
            account = self._one(conn, "SELECT * FROM financial_accounts WHERE account_id = ?", (account_id,))
            if not account and customer_id:
                account = self._one(conn, "SELECT * FROM financial_accounts WHERE customer_id = ?", (customer_id,))
            credits = self._many(conn, "SELECT * FROM credit_products WHERE customer_id = ? ORDER BY opened_date DESC", (customer_id,))
            transactions = self._many(
                conn,
                """
                SELECT type, amount_eur, timestamp, location, description
                FROM financial_transactions
                WHERE account_id = ?
                ORDER BY timestamp DESC
                LIMIT 60
                """,
                (account_id or (account or {}).get("account_id", ""),),
            )
        if customer and customer.get("required_documents"):
            customer["required_documents"] = json.loads(customer["required_documents"])
        if account and account.get("usual_locations"):
            account["usual_locations"] = json.loads(account["usual_locations"])
        return {"customer": customer, "account": account, "credit_products": credits, "recent_transactions": transactions}

    def _medical_snapshot(self, context: DocumentContext) -> dict[str, Any]:
        patient_id = str(context.fields.get("patient_id", ""))
        with self._connect() as conn:
            patient = self._one(conn, "SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
            conditions = self._many(conn, "SELECT * FROM patient_conditions WHERE patient_id = ?", (patient_id,))
            allergies = self._many(conn, "SELECT * FROM patient_allergies WHERE patient_id = ?", (patient_id,))
            medications = self._many(conn, "SELECT * FROM patient_medications WHERE patient_id = ?", (patient_id,))
            events = self._many(
                conn,
                """
                SELECT event_date, event_type, summary, vitals, follow_up
                FROM clinical_events
                WHERE patient_id = ?
                ORDER BY event_date DESC
                LIMIT 18
                """,
                (patient_id,),
            )
        for event in events:
            if event.get("vitals"):
                event["vitals"] = json.loads(event["vitals"])
        return {"patient": patient, "conditions": conditions, "allergies": allergies, "medications": medications, "recent_events": events}

    def _supply_snapshot(self, context: DocumentContext) -> dict[str, Any]:
        fields = context.fields
        supplier_name = str(fields.get("supplier", ""))
        purchase_order_id = str(fields.get("purchase_order_id", ""))
        item_ids = [str(item.get("product_id")) for item in fields.get("items", []) if isinstance(item, dict)]
        with self._connect() as conn:
            supplier = self._one(conn, "SELECT * FROM suppliers WHERE supplier_name = ?", (supplier_name,))
            inventory = [
                {
                    **item,
                    "reservations": self._many(
                        conn,
                        "SELECT reservation_id, quantity, priority, needed_by, internal_owner FROM inventory_reservations WHERE product_id = ?",
                        (item["product_id"],),
                    ),
                    "recent_demand": self._many(
                        conn,
                        """
                        SELECT demand_date, destination, quantity_used, demand_reason
                        FROM inventory_demand_history
                        WHERE product_id = ?
                        ORDER BY demand_date DESC
                        LIMIT 8
                        """,
                        (item["product_id"],),
                    ),
                    "demand_summary": self._one(
                        conn,
                        """
                        SELECT product_id,
                               ROUND(AVG(quantity_used), 2) AS average_period_demand,
                               MAX(quantity_used) AS peak_period_demand,
                               SUM(quantity_used) AS total_recent_demand,
                               COUNT(*) AS periods_observed
                        FROM inventory_demand_history
                        WHERE product_id = ?
                        GROUP BY product_id
                        """,
                        (item["product_id"],),
                    ),
                    "recent_supply": self._many(
                        conn,
                        """
                        SELECT po.purchase_order_id, po.expected_delivery_date, d.delivery_date,
                               poi.quantity AS quantity_ordered, di.quantity_received, poi.unit_price_eur, d.condition_status
                        FROM purchase_order_items poi
                        JOIN purchase_orders po ON poi.purchase_order_id = po.purchase_order_id
                        LEFT JOIN deliveries d ON po.purchase_order_id = d.purchase_order_id
                        LEFT JOIN delivery_items di ON d.delivery_id = di.delivery_id AND poi.product_id = di.product_id
                        WHERE poi.product_id = ?
                        ORDER BY po.expected_delivery_date DESC
                        LIMIT 8
                        """,
                        (item["product_id"],),
                    ),
                    "to_send_matches": self._many(
                        conn,
                        """
                        SELECT o.order_id, c.client_id, c.client_name, c.order_frequency_per_month,
                               c.consolidation_window_days, c.shipping_zone, o.quantity_requested,
                               o.order_date, o.needed_by, o.urgency, o.status
                        FROM outbound_order_requests o
                        JOIN supply_clients c ON o.client_id = c.client_id
                        WHERE o.product_id = ? AND o.status = 'pending'
                        ORDER BY
                            CASE o.urgency WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
                            o.needed_by,
                            o.order_date
                        """,
                        (item["product_id"],),
                    ),
                }
                for item in self._many(
                    conn,
                    f"SELECT * FROM inventory_items WHERE product_id IN ({','.join('?' for _ in item_ids)})",
                    tuple(item_ids),
                )
            ] if item_ids else []
            purchase_order = self._one(
                conn,
                """
                SELECT po.*, s.supplier_name
                FROM purchase_orders po
                JOIN suppliers s ON po.supplier_id = s.supplier_id
                WHERE po.purchase_order_id = ?
                """,
                (purchase_order_id,),
            )
            po_items = self._many(conn, "SELECT * FROM purchase_order_items WHERE purchase_order_id = ?", (purchase_order_id,))
            deliveries = self._many(conn, "SELECT * FROM deliveries WHERE purchase_order_id = ?", (purchase_order_id,))
            invoices = self._many(conn, "SELECT * FROM supplier_invoices WHERE purchase_order_id = ?", (purchase_order_id,))
            supplier_history = self._many(
                conn,
                """
                SELECT po.purchase_order_id, po.expected_delivery_date, d.delivery_date, d.condition_status
                FROM purchase_orders po
                LEFT JOIN deliveries d ON po.purchase_order_id = d.purchase_order_id
                WHERE po.supplier_id = (SELECT supplier_id FROM suppliers WHERE supplier_name = ?)
                ORDER BY po.expected_delivery_date DESC
                LIMIT 12
                """,
                (supplier_name,),
            )
            demand_overview = [
                {
                    **row,
                    "available": self._one(conn, "SELECT available, safety_stock FROM inventory_items WHERE product_id = ?", (row["product_id"],)),
                }
                for row in self._many(
                    conn,
                    """
                    SELECT product_id,
                           ROUND(AVG(quantity_used), 2) AS average_period_demand,
                           MAX(quantity_used) AS peak_period_demand,
                           SUM(quantity_used) AS total_recent_demand,
                           COUNT(*) AS periods_observed
                    FROM inventory_demand_history
                    GROUP BY product_id
                    ORDER BY product_id
                    """,
                    (),
                )
            ]
            to_send_list = self._many(
                conn,
                """
                SELECT o.order_id, c.client_id, c.client_name, c.order_frequency_per_month,
                       c.consolidation_window_days, c.shipping_zone, o.product_id,
                       o.quantity_requested, o.order_date, o.needed_by, o.urgency, o.status
                FROM outbound_order_requests o
                JOIN supply_clients c ON o.client_id = c.client_id
                WHERE o.status = 'pending'
                ORDER BY
                    CASE o.urgency WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END,
                    o.needed_by,
                    o.order_id
                """
                ,
                (),
            )
        return {
            "supplier": supplier,
            "inventory": inventory,
            "purchase_order": purchase_order,
            "purchase_order_items": po_items,
            "deliveries": deliveries,
            "invoices": invoices,
            "supplier_history": supplier_history,
            "demand_overview": demand_overview,
            "to_send_list": to_send_list,
        }

    @staticmethod
    def _one(conn: sqlite3.Connection, query: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _many(conn: sqlite3.Connection, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        return [dict(row) for row in conn.execute(query, params).fetchall()]
