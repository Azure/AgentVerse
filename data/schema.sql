PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS financial_customers (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    risk_status TEXT NOT NULL,
    credit_score INTEGER NOT NULL,
    monthly_income_eur REAL NOT NULL,
    exposure_limit_eur REAL NOT NULL,
    required_documents TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_accounts (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES financial_customers(customer_id),
    holder TEXT NOT NULL,
    balance_eur REAL NOT NULL,
    usual_withdrawal_max_eur REAL NOT NULL,
    usual_withdrawal_avg_eur REAL NOT NULL,
    usual_locations TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_transactions (
    transaction_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES financial_accounts(account_id),
    type TEXT NOT NULL,
    amount_eur REAL NOT NULL,
    timestamp TEXT NOT NULL,
    location TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credit_products (
    product_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES financial_customers(customer_id),
    status TEXT NOT NULL,
    opened_date TEXT NOT NULL,
    outstanding_eur REAL NOT NULL,
    monthly_payment_eur REAL NOT NULL,
    product_type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    primary_doctor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patient_conditions (
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    condition_name TEXT NOT NULL,
    diagnosed_date TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (patient_id, condition_name)
);

CREATE TABLE IF NOT EXISTS patient_allergies (
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    allergy TEXT NOT NULL,
    reaction TEXT NOT NULL,
    PRIMARY KEY (patient_id, allergy)
);

CREATE TABLE IF NOT EXISTS patient_medications (
    medication_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    medication_name TEXT NOT NULL,
    dosage TEXT NOT NULL,
    start_date TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clinical_events (
    event_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    event_date TEXT NOT NULL,
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    vitals TEXT NOT NULL,
    follow_up TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL UNIQUE,
    reliability_score REAL NOT NULL,
    average_lead_time_days INTEGER NOT NULL,
    on_time_rate REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_items (
    product_id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    available INTEGER NOT NULL,
    safety_stock INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_reservations (
    reservation_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES inventory_items(product_id),
    quantity INTEGER NOT NULL,
    priority TEXT NOT NULL,
    needed_by TEXT NOT NULL,
    internal_owner TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory_demand_history (
    demand_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL REFERENCES inventory_items(product_id),
    demand_date TEXT NOT NULL,
    destination TEXT NOT NULL,
    quantity_used INTEGER NOT NULL,
    demand_reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supply_clients (
    client_id TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    order_frequency_per_month REAL NOT NULL,
    consolidation_window_days INTEGER NOT NULL,
    shipping_zone TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbound_order_requests (
    order_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES supply_clients(client_id),
    product_id TEXT NOT NULL REFERENCES inventory_items(product_id),
    quantity_requested INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    needed_by TEXT NOT NULL,
    urgency TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    purchase_order_id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    expected_delivery_date TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_order_items (
    purchase_order_id TEXT NOT NULL REFERENCES purchase_orders(purchase_order_id),
    product_id TEXT NOT NULL REFERENCES inventory_items(product_id),
    quantity INTEGER NOT NULL,
    unit_price_eur REAL NOT NULL,
    PRIMARY KEY (purchase_order_id, product_id)
);

CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id TEXT PRIMARY KEY,
    purchase_order_id TEXT NOT NULL REFERENCES purchase_orders(purchase_order_id),
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    delivery_date TEXT NOT NULL,
    condition_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS delivery_items (
    delivery_id TEXT NOT NULL REFERENCES deliveries(delivery_id),
    product_id TEXT NOT NULL REFERENCES inventory_items(product_id),
    quantity_received INTEGER NOT NULL,
    condition TEXT NOT NULL,
    PRIMARY KEY (delivery_id, product_id)
);

CREATE TABLE IF NOT EXISTS supplier_invoices (
    invoice_id TEXT PRIMARY KEY,
    purchase_order_id TEXT NOT NULL REFERENCES purchase_orders(purchase_order_id),
    supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id),
    invoice_date TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS supplier_invoice_items (
    invoice_id TEXT NOT NULL REFERENCES supplier_invoices(invoice_id),
    product_id TEXT NOT NULL REFERENCES inventory_items(product_id),
    quantity INTEGER NOT NULL,
    unit_price_eur REAL NOT NULL,
    PRIMARY KEY (invoice_id, product_id)
);
