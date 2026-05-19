"""Build the local SQLite database and fabricated document images."""

from __future__ import annotations

import json
import random
import sqlite3
import sys
import textwrap
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentverse.paths import DATA_DIR, FABRICATED_DOCUMENTS_DIR, SIMULATED_DB_PATH


HISTORY_SUMMARY_PATH = DATA_DIR / "fabricated_history_summary.json"


RNG = random.Random(814702)
FABRICATED_CASES = {
    "credit_application": {
        "title": "Personal Credit Application",
        "image_lines": [
            "Branch note - Madrid consumer lending desk",
            "Elena Ruiz, client CUST-1001, came in on 18 May 2026 to ask for a personal loan.",
            "She said the amount needed is twelve thousand euros and that she would prefer to repay it over two years.",
            "The payslip she brought shows roughly EUR 3,300 monthly income.",
            "The file includes a scanned identity document and an income statement.",
            "Purpose discussed with the clerk: household equipment and minor home repairs.",
            "Signed by E. Ruiz at the counter.",
        ],
        "pdf_lines": [
            "Internal lending memo, Madrid Central Branch.",
            "On 18 May 2026 Elena Ruiz (customer CUST-1001) requested a consumer credit facility for EUR 12,000.",
            "The customer asked for a 24 month repayment period and declared monthly net income of approximately EUR 3,300.",
            "The clerk attached the customer's identity document and income statement. The stated purpose is home repairs and household equipment.",
        ],
    },
    "withdrawal_order_high_risk": {
        "title": "Cash Withdrawal Order",
        "image_lines": [
            "Late counter service note - Valencia Centro",
            "A customer identifying himself as Pedro Alonso asked the branch to prepare EUR 10,000 in cash.",
            "The account written on the slip is ACCT-2002.",
            "The request was logged at 22:45 on 18 May 2026.",
            "Pedro said the cash was urgently needed for a private settlement.",
            "The clerk noted that the account normally appears in the Vigo branch network, not Valencia.",
            "Customer mark: P. Alonso",
        ],
        "pdf_lines": [
            "Cash desk exception memo.",
            "At Valencia Centro Branch, Pedro Alonso requested a cash withdrawal of EUR 10,000 from account ACCT-2002.",
            "The request time was 18 May 2026 at 22:45. The customer described the purpose as an urgent private settlement.",
            "Staff note: this request is outside the customer's usual Vigo branch network.",
        ],
    },
    "clinical_note_red_flags": {
        "title": "Walk-In Nursing Note",
        "image_lines": [
            "Walk-in note from AgentVerse Demo Clinic",
            "Ana Santos, PAT-3001, arrived on 18 May 2026 saying she felt pressure across the chest.",
            "She was short of breath and described pain moving toward the left arm.",
            "The episode began earlier today and had not fully settled by the time she arrived.",
            "Observed vitals: BP 168 over 102, pulse 96.",
            "Nurse note: clinician should rule out acute coronary syndrome; urgent doctor review requested.",
            "Initials JV",
        ],
        "pdf_lines": [
            "Triage narrative for Ana Santos (PAT-3001), 18 May 2026.",
            "The patient reports chest pressure, shortness of breath, and pain radiating into the left arm since earlier today.",
            "Recorded blood pressure was 168/102 with heart rate 96. The triage nurse requested urgent medical review and cardiology follow-up because acute coronary syndrome must be ruled out.",
        ],
    },
    "prescription_allergy_conflict": {
        "title": "Prescription",
        "image_lines": [
            "Medication note - Dr. Chen",
            "Luis Paredes, PAT-3002, was given a handwritten prescription on 18 May 2026.",
            "The medicine written is amoxicillin 500 mg tablets.",
            "Dose instruction: one tablet every eight hours for seven days.",
            "Return precautions mentioned rash, fever, wheezing, or breathing issues.",
            "Signed: Chen",
        ],
        "pdf_lines": [
            "Outpatient prescription record.",
            "For Luis Paredes (PAT-3002), Dr. Chen entered amoxicillin 500 mg tablets on 18 May 2026.",
            "The intended course is one tablet every 8 hours for 7 days. The patient was told to return if rash, fever, wheezing, or breathing problems develop.",
        ],
    },
    "shipment_request": {
        "title": "Warehouse Arrival Balance Sheet",
        "image_lines": [
            "Receiving balance BSH-2026-0519-A",
            "Dock C / Central storage / counted 19 May 2026 at 07:40.",
            "Line 01: GLOVES_NITRILE - 500 boxes - sealed cartons - batch GN-2605-A.",
            "Line 02: MASK_N95 - 180 packs - intact outer cases - batch M95-2605-B.",
            "Line 03: SALINE_500ML - 300 bags - dry outer cases - lot S500-2605-C.",
            "Pallet slip destination: central stock only. No ward, clinic, or outbound client written.",
            "Put-away status: waiting for inventory desk allocation.",
        ],
        "pdf_lines": [
            "Receiving balance BSH-2026-0519-A.",
            "Dock C / Central storage / counted 19 May 2026 at 07:40.",
            "Line 01: GLOVES_NITRILE - 500 boxes - sealed cartons - batch GN-2605-A.",
            "Line 02: MASK_N95 - 180 packs - intact outer cases - batch M95-2605-B.",
            "Line 03: SALINE_500ML - 300 bags - dry outer cases - lot S500-2605-C.",
            "Pallet slip destination: central stock only. No ward, clinic, or outbound client written.",
            "Put-away status: waiting for inventory desk allocation.",
        ],
    },
    "supplier_invoice_mismatch": {
        "title": "Sterile Supplies Arrival Sheet",
        "image_lines": [
            "Receiving balance BSH-2026-0519-B",
            "Dock B / Sterile storage / counted 19 May 2026 at 09:15.",
            "Supplier label: Northwind Medical. References PO-7001 and delivery DEL-7001.",
            "Line 01: SYRINGE_5ML - 950 units physically counted - lot SYR5-2605-N.",
            "Invoice packet INV-8101 attached: billed quantity 1,200 units at EUR 0.10; invoice check pending.",
            "Physical count accepted for inventory intake: 950 units. Destination field left blank.",
            "Put-away status: ready for allocation review; stock not assigned to a ward or client yet.",
        ],
        "pdf_lines": [
            "Receiving balance BSH-2026-0519-B.",
            "Dock B / Sterile storage / counted 19 May 2026 at 09:15.",
            "Supplier label: Northwind Medical. References PO-7001 and delivery DEL-7001.",
            "Line 01: SYRINGE_5ML - 950 units physically counted - lot SYR5-2605-N.",
            "Invoice packet INV-8101 attached: billed quantity 1,200 units at EUR 0.10; invoice check pending.",
            "Physical count accepted for inventory intake: 950 units. Destination field left blank.",
            "Put-away status: ready for allocation review; stock not assigned to a ward or client yet.",
        ],
    },
    "low_quality_unknown": {
        "title": "Cropped Scan Fragment",
        "image_lines": [
            "total ...",
            "signature ...",
            "ref ...",
            "date ...",
            "amount ...",
        ],
        "pdf_lines": [
            "Fragment only.",
            "Visible words include total, signature, ref, date, and amount, but the surrounding business context is missing.",
        ],
    },
}


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FABRICATED_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    build_database()
    build_document_assets()
    print(f"Database: {SIMULATED_DB_PATH}")
    print(f"Fabricated documents: {FABRICATED_DOCUMENTS_DIR}")


def build_database() -> None:
    if SIMULATED_DB_PATH.exists():
        SIMULATED_DB_PATH.unlink()

    with sqlite3.connect(SIMULATED_DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        schema_path = Path(__file__).resolve().parent.parent / "data" / "schema.sql"
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        seed_financial(conn)
        seed_medical(conn)
        seed_supply(conn)
        conn.commit()
        write_history_summary(conn)


def seed_financial(conn: sqlite3.Connection) -> None:
    customers = [
        ("CUST-1001", "Elena Ruiz", "standard", 724, 3300, 25000, ["id", "income_statement"]),
        ("CUST-1002", "Pedro Alonso", "enhanced_monitoring", 681, 4100, 18000, ["id", "income_statement", "bank_statements"]),
        ("CUST-1003", "Sofia Moreira", "standard", 758, 5200, 35000, ["id", "income_statement"]),
    ]
    conn.executemany(
        "INSERT INTO financial_customers VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(cid, name, risk, score, income, limit, json.dumps(docs)) for cid, name, risk, score, income, limit, docs in customers],
    )

    accounts = [
        ("ACCT-1001", "CUST-1001", "Elena Ruiz", 12800, 1200, 420, ["Madrid Central Branch", "Madrid ATM 4"]),
        ("ACCT-2002", "CUST-1002", "Pedro Alonso", 11800, 900, 350, ["Vigo Centro Branch", "Vigo Industrial Estate ATM", "Vigo Port Branch"]),
        ("ACCT-3003", "CUST-1003", "Sofia Moreira", 22600, 1800, 680, ["Lisbon Business Branch", "Lisbon Airport ATM"]),
    ]
    conn.executemany(
        "INSERT INTO financial_accounts VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(aid, cid, holder, bal, max_w, avg_w, json.dumps(locs)) for aid, cid, holder, bal, max_w, avg_w, locs in accounts],
    )

    credits = [
        ("CR-4501", "CUST-1001", "current", "2025-04-11", 4200, 210, "personal_loan"),
        ("CR-7712", "CUST-1002", "late", "2024-10-03", 6400, 340, "auto_loan"),
        ("CR-8820", "CUST-1003", "current", "2023-09-15", 8700, 390, "home_improvement"),
    ]
    conn.executemany("INSERT INTO credit_products VALUES (?, ?, ?, ?, ?, ?, ?)", credits)

    start = datetime(2024, 1, 5, 9, 0)
    transaction_rows = []
    for account_id, customer_id, holder, _balance, max_withdrawal, avg_withdrawal, locations in accounts:
        for month in range(0, 29):
            base = start + timedelta(days=30 * month)
            income = 3100 if customer_id == "CUST-1001" else 3900 if customer_id == "CUST-1002" else 5100
            deposit_location = RNG.choice(locations) if customer_id == "CUST-1002" else "Payroll Transfer"
            transaction_rows.append(
                (
                    f"TX-{account_id}-{month:02d}-DEP",
                    account_id,
                    "deposit",
                    income + RNG.randint(-120, 180),
                    (base + timedelta(hours=RNG.randint(0, 5))).isoformat(),
                    deposit_location,
                    "monthly salary deposit in usual Vigo network" if customer_id == "CUST-1002" else "monthly salary deposit",
                )
            )
            for idx in range(3):
                amount = max(40, int(RNG.gauss(avg_withdrawal, avg_withdrawal * 0.25)))
                amount = min(amount, int(max_withdrawal))
                transaction_rows.append(
                    (
                        f"TX-{account_id}-{month:02d}-W{idx}",
                        account_id,
                        "withdrawal",
                        amount,
                        (base + timedelta(days=3 + idx * 7, hours=RNG.randint(8, 17))).isoformat(),
                        RNG.choice(locations),
                        "routine cash withdrawal",
                    )
                )
        if account_id == "ACCT-2002":
            transaction_rows.append(
                (
                    "TX-ACCT-2002-SUSPICIOUS-DEPOSIT",
                    "ACCT-2002",
                    "deposit",
                    8000,
                    "2026-05-18T09:10:00",
                    "Online Transfer",
                    "large same-day incoming transfer",
                )
            )
            transaction_rows.append(
                (
                    "TX-ACCT-2002-RECENT-VIGO-WITHDRAWAL",
                    "ACCT-2002",
                    "withdrawal",
                    420,
                    "2026-05-12T11:20:00",
                    "Vigo Centro Branch",
                    "recent routine cash withdrawal in usual location",
                )
            )
    conn.executemany("INSERT INTO financial_transactions VALUES (?, ?, ?, ?, ?, ?, ?)", transaction_rows)


def seed_medical(conn: sqlite3.Connection) -> None:
    patients = [
        ("PAT-3001", "Ana Santos", "1974-02-09", "Dr. Valente"),
        ("PAT-3002", "Luis Paredes", "1991-07-18", "Dr. Chen"),
        ("PAT-3003", "Marta Nunes", "1983-11-22", "Dr. Valente"),
    ]
    conn.executemany("INSERT INTO patients VALUES (?, ?, ?, ?)", patients)
    conditions = [
        ("PAT-3001", "hypertension", "2022-04-10", "active"),
        ("PAT-3001", "hyperlipidemia", "2024-01-12", "active"),
        ("PAT-3002", "asthma", "2019-06-04", "active"),
        ("PAT-3003", "type 2 diabetes", "2021-08-30", "active"),
    ]
    conn.executemany("INSERT INTO patient_conditions VALUES (?, ?, ?, ?)", conditions)
    allergies = [
        ("PAT-3001", "penicillin", "rash"),
        ("PAT-3002", "penicillin", "wheezing and rash"),
        ("PAT-3003", "sulfonamides", "hives"),
    ]
    conn.executemany("INSERT INTO patient_allergies VALUES (?, ?, ?)", allergies)
    medications = [
        ("MED-PAT-3001-1", "PAT-3001", "lisinopril", "10 mg daily", "2024-02-01", "active"),
        ("MED-PAT-3001-2", "PAT-3001", "atorvastatin", "20 mg nightly", "2024-03-01", "active"),
        ("MED-PAT-3002-1", "PAT-3002", "salbutamol", "as needed", "2022-02-15", "active"),
        ("MED-PAT-3003-1", "PAT-3003", "metformin", "850 mg twice daily", "2023-09-04", "active"),
    ]
    conn.executemany("INSERT INTO patient_medications VALUES (?, ?, ?, ?, ?, ?)", medications)

    summaries = {
        "PAT-3001": ["blood pressure review", "lipid panel review", "cardiology follow-up", "chest discomfort triage"],
        "PAT-3002": ["asthma control review", "respiratory infection", "prescription renewal", "allergy counseling"],
        "PAT-3003": ["diabetes follow-up", "nutrition counseling", "A1C review", "foot exam"],
    }
    rows = []
    for patient_id, *_ in patients:
        for idx in range(18):
            event_date = date(2024, 1, 15) + timedelta(days=35 * idx)
            summary = RNG.choice(summaries[patient_id])
            systolic = RNG.randint(118, 162 if patient_id == "PAT-3001" else 138)
            diastolic = RNG.randint(72, 98)
            rows.append(
                (
                    f"EV-{patient_id}-{idx:02d}",
                    patient_id,
                    event_date.isoformat(),
                    "visit" if idx % 3 else "lab_review",
                    summary,
                    json.dumps({"blood_pressure": f"{systolic}/{diastolic}", "heart_rate": RNG.randint(62, 92)}),
                    "routine follow-up" if idx % 4 else "review in 2 weeks if symptoms persist",
                )
            )
    conn.executemany("INSERT INTO clinical_events VALUES (?, ?, ?, ?, ?, ?, ?)", rows)


def seed_supply(conn: sqlite3.Connection) -> None:
    suppliers = [
        ("SUP-5001", "MedSupply Iberia", 0.91, 3, 0.92),
        ("SUP-5002", "Northwind Medical", 0.78, 6, 0.81),
        ("SUP-5003", "Atlantic Pharma Logistics", 0.86, 5, 0.88),
    ]
    conn.executemany("INSERT INTO suppliers VALUES (?, ?, ?, ?, ?)", suppliers)
    inventory = [
        ("GLOVES_NITRILE", "Nitrile examination gloves", 600, 200),
        ("MASK_N95", "N95 respiratory masks", 300, 100),
        ("SYRINGE_5ML", "5 ml sterile syringes", 2000, 300),
        ("SALINE_500ML", "500 ml saline bags", 760, 250),
    ]
    conn.executemany("INSERT INTO inventory_items VALUES (?, ?, ?, ?)", inventory)
    reservations = [
        ("RES-100", "GLOVES_NITRILE", 300, "low", "2026-05-30", "Training Clinic"),
        ("RES-101", "GLOVES_NITRILE", 150, "critical", "2026-05-19", "Emergency Ward"),
        ("RES-200", "MASK_N95", 100, "low", "2026-05-27", "Outreach Program"),
    ]
    conn.executemany("INSERT INTO inventory_reservations VALUES (?, ?, ?, ?, ?, ?)", reservations)
    supply_clients = [
        ("CL-100", "Lisbon Clinic", 2.0, 7, "Lisbon metro", "Usually orders twice per month; consolidate routine orders within a week when stock allows."),
        ("CL-200", "Emergency Ward", 4.0, 1, "Hospital campus", "Critical-care destination; ship urgent requests immediately."),
        ("CL-300", "Outreach Program", 1.0, 10, "Regional outreach", "Cost-sensitive route; consolidate low-urgency shipments."),
        ("CL-400", "Training Clinic", 0.5, 14, "Training center", "Low urgency training stock; ship only after critical demand is covered."),
    ]
    conn.executemany("INSERT INTO supply_clients VALUES (?, ?, ?, ?, ?, ?)", supply_clients)
    outbound_orders = [
        ("SEND-9001", "CL-100", "GLOVES_NITRILE", 320, "2026-05-14", "2026-05-22", "medium", "pending"),
        ("SEND-9002", "CL-100", "MASK_N95", 120, "2026-05-16", "2026-05-22", "medium", "pending"),
        ("SEND-9003", "CL-100", "SALINE_500ML", 180, "2026-05-18", "2026-05-29", "low", "pending"),
        ("SEND-9100", "CL-200", "GLOVES_NITRILE", 150, "2026-05-18", "2026-05-19", "critical", "pending"),
        ("SEND-9101", "CL-200", "MASK_N95", 100, "2026-05-18", "2026-05-19", "critical", "pending"),
        ("SEND-9102", "CL-200", "SYRINGE_5ML", 700, "2026-05-18", "2026-05-20", "critical", "pending"),
        ("SEND-9200", "CL-300", "MASK_N95", 80, "2026-05-13", "2026-05-27", "low", "pending"),
        ("SEND-9300", "CL-400", "GLOVES_NITRILE", 300, "2026-05-10", "2026-05-30", "low", "pending"),
        ("SEND-9301", "CL-400", "SYRINGE_5ML", 350, "2026-05-12", "2026-05-31", "low", "pending"),
    ]
    conn.executemany("INSERT INTO outbound_order_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?)", outbound_orders)
    demand_rows = []
    demand_profiles = {
        "GLOVES_NITRILE": (360, 80, "routine clinical consumption"),
        "MASK_N95": (145, 45, "respiratory protection usage"),
        "SYRINGE_5ML": (780, 140, "injection and medication prep usage"),
        "SALINE_500ML": (250, 70, "ward fluid restock"),
    }
    destinations = ["Lisbon Clinic", "Emergency Ward", "Outpatient Unit", "Training Clinic"]
    for product_id, (base_quantity, spread, reason) in demand_profiles.items():
        for month in range(18):
            demand_date = date(2024, 1, 20) + timedelta(days=30 * month)
            seasonal_bump = 140 if product_id in {"GLOVES_NITRILE", "MASK_N95"} and month in {15, 16, 17} else 0
            quantity = max(20, base_quantity + seasonal_bump + RNG.randint(-spread, spread))
            demand_rows.append(
                (
                    f"DEM-{product_id}-{month:02d}",
                    product_id,
                    demand_date.isoformat(),
                    destinations[month % len(destinations)],
                    quantity,
                    reason,
                )
            )
    conn.executemany("INSERT INTO inventory_demand_history VALUES (?, ?, ?, ?, ?, ?)", demand_rows)

    po_rows = []
    po_item_rows = []
    delivery_rows = []
    delivery_item_rows = []
    invoice_rows = []
    invoice_item_rows = []
    products = ["GLOVES_NITRILE", "MASK_N95", "SYRINGE_5ML", "SALINE_500ML"]
    for supplier_idx, (supplier_id, _name, _score, lead_time, _on_time) in enumerate(suppliers, start=1):
        for idx in range(14):
            po_id = f"PO-{supplier_idx}{idx:03d}"
            expected = date(2024, 1, 10) + timedelta(days=42 * idx + lead_time)
            po_rows.append((po_id, supplier_id, expected.isoformat(), "closed"))
            chosen_product = products[(idx + supplier_idx) % len(products)]
            quantity = RNG.choice([500, 750, 1000, 1200, 1500])
            price = {"GLOVES_NITRILE": 0.05, "MASK_N95": 0.62, "SYRINGE_5ML": 0.08, "SALINE_500ML": 1.35}[chosen_product]
            po_item_rows.append((po_id, chosen_product, quantity, price))
            delivery_id = f"DEL-{supplier_idx}{idx:03d}"
            received = quantity - RNG.choice([0, 0, 0, 25, 50])
            delivery_rows.append((delivery_id, po_id, supplier_id, (expected + timedelta(days=RNG.choice([-1, 0, 1, 2]))).isoformat(), "accepted"))
            delivery_item_rows.append((delivery_id, chosen_product, received, "accepted" if received == quantity else "accepted_with_shortage"))
            invoice_id = f"INV-{supplier_idx}{idx:03d}"
            invoice_rows.append((invoice_id, po_id, supplier_id, (expected + timedelta(days=2)).isoformat(), "paid" if idx < 12 else "pending"))
            invoice_item_rows.append((invoice_id, chosen_product, received, price))

    po_rows.append(("PO-7001", "SUP-5002", "2026-05-15", "received_with_discrepancy"))
    po_item_rows.append(("PO-7001", "SYRINGE_5ML", 1000, 0.08))
    delivery_rows.append(("DEL-7001", "PO-7001", "SUP-5002", "2026-05-17", "accepted_with_shortage"))
    delivery_item_rows.append(("DEL-7001", "SYRINGE_5ML", 950, "accepted_with_shortage"))
    invoice_rows.append(("INV-8101", "PO-7001", "SUP-5002", "2026-05-17", "pending_dispute"))
    invoice_item_rows.append(("INV-8101", "SYRINGE_5ML", 1200, 0.10))

    conn.executemany("INSERT INTO purchase_orders VALUES (?, ?, ?, ?)", po_rows)
    conn.executemany("INSERT INTO purchase_order_items VALUES (?, ?, ?, ?)", po_item_rows)
    conn.executemany("INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)", delivery_rows)
    conn.executemany("INSERT INTO delivery_items VALUES (?, ?, ?, ?)", delivery_item_rows)
    conn.executemany("INSERT INTO supplier_invoices VALUES (?, ?, ?, ?, ?)", invoice_rows)
    conn.executemany("INSERT INTO supplier_invoice_items VALUES (?, ?, ?, ?)", invoice_item_rows)


def write_history_summary(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    summary = {
        "financial_clients": [_financial_client_summary(conn, row) for row in conn.execute("SELECT * FROM financial_customers ORDER BY customer_id")],
        "patients": [_patient_summary(conn, row) for row in conn.execute("SELECT * FROM patients ORDER BY patient_id")],
        "suppliers": [_supplier_summary(conn, row) for row in conn.execute("SELECT * FROM suppliers ORDER BY supplier_id")],
        "inventory_demand": _inventory_demand_summary(conn),
        "to_send_orders": [dict(row) for row in conn.execute(
            """
            SELECT o.order_id, c.client_name, o.product_id, o.quantity_requested, o.order_date,
                   o.needed_by, o.urgency, c.order_frequency_per_month, c.consolidation_window_days
            FROM outbound_order_requests o
            JOIN supply_clients c ON o.client_id = c.client_id
            ORDER BY o.urgency DESC, o.needed_by, o.order_id
            """
        )],
    }
    HISTORY_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def _financial_client_summary(conn: sqlite3.Connection, customer: sqlite3.Row) -> dict[str, object]:
    account = conn.execute("SELECT * FROM financial_accounts WHERE customer_id = ?", (customer["customer_id"],)).fetchone()
    transactions = conn.execute(
        """
        SELECT type, ROUND(AVG(amount_eur), 2) AS avg_amount, MAX(amount_eur) AS max_amount, COUNT(*) AS count
        FROM financial_transactions
        WHERE account_id = ?
        GROUP BY type
        ORDER BY type
        """,
        (account["account_id"],),
    ).fetchall()
    common_locations = conn.execute(
        """
        SELECT location, COUNT(*) AS count
        FROM financial_transactions
        WHERE account_id = ?
        GROUP BY location
        ORDER BY count DESC, location
        LIMIT 6
        """,
        (account["account_id"],),
    ).fetchall()
    recent_events = conn.execute(
        """
        SELECT type, amount_eur, timestamp, location, description
        FROM financial_transactions
        WHERE account_id = ?
        ORDER BY timestamp DESC
        LIMIT 8
        """,
        (account["account_id"],),
    ).fetchall()
    return {
        "customer_id": customer["customer_id"],
        "name": customer["full_name"],
        "risk_status": customer["risk_status"],
        "account_id": account["account_id"],
        "balance_eur": account["balance_eur"],
        "usual_withdrawal_avg_eur": account["usual_withdrawal_avg_eur"],
        "usual_withdrawal_max_eur": account["usual_withdrawal_max_eur"],
        "usual_locations": json.loads(account["usual_locations"]),
        "transaction_patterns": [dict(row) for row in transactions],
        "common_locations": [dict(row) for row in common_locations],
        "recent_events": [dict(row) for row in recent_events],
    }


def _patient_summary(conn: sqlite3.Connection, patient: sqlite3.Row) -> dict[str, object]:
    return {
        "patient_id": patient["patient_id"],
        "name": patient["full_name"],
        "primary_doctor": patient["primary_doctor"],
        "conditions": [dict(row) for row in conn.execute("SELECT condition_name, status FROM patient_conditions WHERE patient_id = ?", (patient["patient_id"],))],
        "allergies": [dict(row) for row in conn.execute("SELECT allergy, reaction FROM patient_allergies WHERE patient_id = ?", (patient["patient_id"],))],
        "medications": [dict(row) for row in conn.execute("SELECT medication_name, dosage, status FROM patient_medications WHERE patient_id = ?", (patient["patient_id"],))],
        "recent_events": [
            dict(row)
            for row in conn.execute(
                "SELECT event_date, event_type, summary, vitals, follow_up FROM clinical_events WHERE patient_id = ? ORDER BY event_date DESC LIMIT 6",
                (patient["patient_id"],),
            )
        ],
    }


def _supplier_summary(conn: sqlite3.Connection, supplier: sqlite3.Row) -> dict[str, object]:
    recent_orders = conn.execute(
        """
        SELECT po.purchase_order_id, po.expected_delivery_date, po.status, poi.product_id, poi.quantity, poi.unit_price_eur,
               d.delivery_date, di.quantity_received, d.condition_status
        FROM purchase_orders po
        LEFT JOIN purchase_order_items poi ON po.purchase_order_id = poi.purchase_order_id
        LEFT JOIN deliveries d ON po.purchase_order_id = d.purchase_order_id
        LEFT JOIN delivery_items di ON d.delivery_id = di.delivery_id AND poi.product_id = di.product_id
        WHERE po.supplier_id = ?
        ORDER BY po.expected_delivery_date DESC
        LIMIT 8
        """,
        (supplier["supplier_id"],),
    ).fetchall()
    disputed_invoices = conn.execute(
        """
        SELECT si.invoice_id, si.purchase_order_id, si.status, sii.product_id, sii.quantity, sii.unit_price_eur
        FROM supplier_invoices si
        JOIN supplier_invoice_items sii ON si.invoice_id = sii.invoice_id
        WHERE si.supplier_id = ? AND si.status LIKE '%dispute%'
        ORDER BY si.invoice_date DESC
        """,
        (supplier["supplier_id"],),
    ).fetchall()
    return {
        "supplier_id": supplier["supplier_id"],
        "name": supplier["supplier_name"],
        "reliability_score": supplier["reliability_score"],
        "average_lead_time_days": supplier["average_lead_time_days"],
        "on_time_rate": supplier["on_time_rate"],
        "recent_orders": [dict(row) for row in recent_orders],
        "disputed_or_exception_invoices": [dict(row) for row in disputed_invoices],
    }


def _inventory_demand_summary(conn: sqlite3.Connection) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT i.product_id, i.description, i.available, i.safety_stock,
               ROUND(AVG(d.quantity_used), 2) AS average_period_demand,
               MAX(d.quantity_used) AS peak_period_demand,
               SUM(d.quantity_used) AS total_recent_demand,
               COUNT(d.demand_id) AS periods_observed
        FROM inventory_items i
        LEFT JOIN inventory_demand_history d ON i.product_id = d.product_id
        GROUP BY i.product_id, i.description, i.available, i.safety_stock
        ORDER BY i.product_id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def build_document_assets() -> None:
    try:
        font = ImageFont.truetype("arial.ttf", 28)
        title_font = ImageFont.truetype("arial.ttf", 38)
    except OSError:
        font = ImageFont.load_default()
        title_font = font

    for fixture_id, fixture in FABRICATED_CASES.items():
        image = Image.new("RGB", (1400, 1800), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((45, 45, 1355, 1755), outline=(30, 64, 175), width=4)
        draw.text((90, 90), fixture["title"], fill=(20, 40, 90), font=title_font)
        draw.text((90, 150), "Synthetic demo document - no real personal data", fill=(90, 90, 90), font=font)
        y = 230
        for source_line in fixture["image_lines"]:
            wrapped = textwrap.wrap(source_line, width=76) or [""]
            for line in wrapped:
                indent = 110 if line.startswith(" - ") else 90
                draw.text((indent, y), line, fill=(20, 20, 20), font=font)
                y += 38
            y += 12
        if fixture_id == "low_quality_unknown":
            image = image.rotate(2, expand=False, fillcolor="white")
            overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            for _ in range(220):
                x = RNG.randint(0, image.width)
                y_noise = RNG.randint(0, image.height)
                overlay_draw.ellipse((x, y_noise, x + 2, y_noise + 2), fill=(120, 120, 120, 90))
            image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        image.save(FABRICATED_DOCUMENTS_DIR / f"{fixture_id}.png")
        _save_pdf(FABRICATED_DOCUMENTS_DIR / f"{fixture_id}.pdf", fixture)


def _save_pdf(path: Path, fixture: dict[str, object]) -> None:
    page_width, page_height = A4
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle(str(fixture["title"]))
    pdf.setStrokeColorRGB(0.12, 0.25, 0.69)
    pdf.setLineWidth(2)
    pdf.rect(36, 36, page_width - 72, page_height - 72)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(72, page_height - 90, str(fixture["title"]))
    pdf.setFont("Helvetica", 10)
    pdf.setFillColorRGB(0.35, 0.35, 0.35)
    pdf.drawString(72, page_height - 112, "Synthetic demo document - no real personal data")
    pdf.setFillColorRGB(0.08, 0.08, 0.08)
    pdf.setFont("Helvetica", 12)
    y = page_height - 155
    for source_line in fixture.get("pdf_lines", fixture["image_lines"]):
        for line in _wrap_pdf_line(str(source_line), max_width=page_width - 144, font_name="Helvetica", font_size=12):
            pdf.drawString(86 if line.startswith(" - ") else 72, y, line)
            y -= 18
        y -= 7
    pdf.showPage()
    pdf.save()


def _wrap_pdf_line(text: str, max_width: float, font_name: str, font_size: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


if __name__ == "__main__":
    main()
