# MAF multi-agent document triage plan

## Current state

The project directory `C:\Demos offline\AgentVerse` does not currently contain visible source files or configuration, and it is not a Git repository. This plan therefore treats the solution as a greenfield MAF design exercise focused on defining the agents, their responsibilities, capabilities, handoff contracts, and safety boundaries before any code is created.

All business-system data and integrations are assumed to be mocked for the first version. The plan should not depend on live financial, medical, inventory, procurement, supplier, storage, or OCR services. Any external capability should be represented by a mock adapter with realistic sample responses.

## Objective

Create a four-agent MAF solution for photo-uploaded documents:

1. A deciding/intake agent that analyzes an uploaded document image, extracts context, classifies the document, and hands off to the right specialized agent.
2. A financial document agent for credit and suspicious withdrawal workflows.
3. A medical document agent for clinical summarization and doctor-facing next-step recommendations.
4. A supply/procurement document agent for shipment/supply planning and a second proposed supply use case.

## Proposed document intelligence approach

Use a mocked Azure AI Document Intelligence-compatible adapter for the first version. Azure AI Document Intelligence remains the recommended production OCR/document-analysis service because it supports OCR, key-value extraction, tables, layout, custom classifiers, and structured document outputs, but the initial plan should simulate that output from fixtures instead of calling Azure.

The deciding agent can combine mocked Document Intelligence output with a MAF classification prompt or deterministic mock classifier to produce a typed context envelope for downstream agents.

If image quality is a major issue, the mock OCR adapter should include representative quality warnings such as rotation, blur, cropped text, language detection, and an "insufficient quality" fallback so the agent behavior can be designed and evaluated without real OCR.

## Shared workflow

1. User uploads a photo of a document with optional metadata such as user/customer/patient/supplier ID.
2. The deciding agent validates the file, runs mocked OCR/document analysis, classifies the document, and extracts normalized context.
3. The deciding agent routes the task to the financial, medical, or supply agent through a MAF handoff.
4. The specialized agent uses the extracted context plus mocked business-system tools to produce a recommendation and evidence summary.
5. A human reviews the recommendation before any irreversible business, financial, medical, or procurement action is executed.

## Shared handoff contracts

### DocumentContext

The deciding agent should pass a normalized context object to downstream agents:

- `document_id`: generated trace ID.
- `source_uri`: image/blob reference, not raw image bytes unless required.
- `document_type`: `financial`, `medical`, `supply`, or `unknown`.
- `document_subtype`: examples include `credit_application`, `withdrawal_order`, `clinical_note`, `prescription`, `shipment_notice`, `invoice`, or `packing_slip`.
- `language`: detected language.
- `extracted_text`: OCR text.
- `fields`: structured key-value fields extracted from the document.
- `tables`: extracted table data when present.
- `entities`: people, organizations, dates, amounts, account IDs, patient IDs, product IDs, quantities, and locations.
- `classification_confidence`: model confidence.
- `quality_warnings`: blur, cropped text, low confidence fields, missing pages, or ambiguous document type.
- `source_citations`: references to OCR spans/pages/regions that support key extracted facts.

### AgentRecommendation

Each specialized agent should return:

- `recommended_action`: approve, reject, hold, escalate, summarize, prescribe_for_review, buy, release_reserved_stock, dispute_supplier_document, or unknown.
- `decision_status`: `ready_for_review`, `needs_human_review`, `blocked_missing_data`, or `unsupported_document`.
- `risk_level`: low, medium, high, critical, or not_applicable.
- `reasoning_summary`: concise explanation suitable for personnel.
- `evidence`: source fields, data queries, and rules that support the recommendation.
- `missing_information`: required inputs or system data not available.
- `next_steps`: human-readable actions for the reviewer.

## Agent 1: Document intake and deciding agent

### Responsibilities

- Accept document photos and optional user-supplied metadata.
- Validate supported formats, file size, image quality, language, and minimum OCR confidence.
- Run mocked Azure AI Document Intelligence-compatible OCR/layout/document analysis.
- Classify the document as financial, medical, supply, or unknown.
- Detect the subtype when possible.
- Build the `DocumentContext` envelope.
- Route to the correct specialized agent with the extracted context.
- Escalate to manual review when classification is low-confidence or the document contains conflicting signals.
- Keep an audit trail of extraction, classification confidence, and handoff decision.

### Capabilities

- OCR and layout extraction through mocked document-analysis fixtures.
- Custom classifier, schema-constrained classification prompt, or deterministic mock classifier.
- Confidence thresholding and fallback behavior.
- PII/PHI-aware logging and redaction.
- MAF handoff to specialized agents.
- Human-in-the-loop escalation.

### Explicit boundaries

- It does not make domain decisions such as approving credit, stopping a withdrawal, recommending treatment, or purchasing supplies.
- It should not route low-confidence documents automatically.

## Agent 2: Financial document agent

### Responsibilities

- Process financial documents routed by the deciding agent.
- Identify whether the document is a credit request, withdrawal order, or unsupported financial subtype.
- Query mocked financial tools for credit history, existing loans, account balance, transaction history, recurrent withdrawal patterns, and customer risk status.
- Produce an evidence-backed recommendation for financial personnel.

### Use case 1: Credit request

For a credit or loan application, the agent should:

- Extract applicant identity, requested amount, requested terms, declared income or collateral if available, and requested date.
- Check whether the person already has an active credit product.
- Check the status of existing credit: current, late, delinquent, defaulted, closed, or restructured.
- Compare the request against business rules such as outstanding exposure, repayment history, and required documents.
- Recommend approve, reject, or escalate, with reasons and missing data.

### Use case 2: Withdrawal order over 5000 euros

For a withdrawal order above the configured threshold, the agent should:

- Extract account holder, account, requested withdrawal amount, location, date, and time.
- Check current balance and recent balance history.
- Compare the requested withdrawal against prior withdrawal frequency, amount, timing, and location patterns.
- Flag unusual timing, unusual amount, rapid balance changes, recent deposits followed by withdrawal, or mismatch with recurrent behavior.
- Assign a theft/fraud risk level.
- Recommend hold/escalate when risk is high, and tell personnel not to release the money until the cause is checked.

### Capabilities

- Read-only mocked financial data queries.
- Business rule evaluation.
- Transaction-pattern analysis.
- Fraud-risk scoring.
- Recommendation generation with evidence and auditability.

### Explicit boundaries

- It should recommend actions, not autonomously approve credit or execute/deny withdrawals unless a later approved scope explicitly allows that.
- It should avoid exposing unnecessary sensitive account data in summaries.

## Agent 3: Medical document agent

### Responsibilities

- Process medical documents routed by the deciding agent.
- Extract clinical facts from the document context.
- Produce a doctor-facing summary and decision-support output.
- Preserve clear separation between AI support and medical authority.

### Use case 1: Clinical summary

For a clinical note, prescription, discharge document, or similar record, the agent should:

- Summarize condition or suspected diagnosis.
- Extract prescribed medications, dosage, duration, and instructions when present.
- Extract follow-up date or recommended follow-up interval.
- Identify missing or ambiguous clinical facts.
- Return a concise summary suitable for a medical record or doctor review.

### Use case 2: Next-step and prescription suggestions

Based on the document context and configured mocked medical knowledge sources, the agent should:

- Suggest possible next steps for the doctor to consider.
- Include common and less-likely but clinically relevant possibilities when supported by symptoms/context.
- Flag urgent red flags or contraindications when detectable.
- Include uncertainty and evidence, rather than presenting suggestions as final diagnoses or prescriptions.

### Capabilities

- Medical entity extraction.
- Clinical summarization.
- Retrieval from mocked clinical guidelines or internal medical knowledge bases.
- Medication/allergy/interaction checks if mocked EHR data is available.
- Doctor-facing recommendation formatting.

### Explicit boundaries

- It must not autonomously diagnose, prescribe, or replace a clinician.
- It should label outputs as clinical decision support for doctor review.
- It should escalate emergencies, contradictions, missing patient identity, or low-confidence OCR.

## Agent 4: Supply/procurement document agent

### Responsibilities

- Process supply and procurement documents routed by the deciding agent.
- Extract product, quantity, supplier, delivery, warehouse, reservation, and schedule information.
- Query mocked inventory, reservations, purchase orders, supplier history, and delivery lead times.
- Recommend a supply action with operational evidence.

### Use case 1: Shipment or supply request viability

For a supply shipment/request document, the agent should:

- Extract requested supplies, quantities, destination, required date, supplier, and delivery terms.
- Check currently available stock.
- Check stock reserved for other internal needs.
- Determine whether some reserved stock could be safely reallocated based on reservation priority and delivery timelines.
- Estimate whether new supply can arrive in time based on previous supplier deliveries.
- Recommend using available stock, releasing reserved stock, triggering a purchase, requesting partial fulfillment, or escalating.

### Use case 2: Supplier document reconciliation

As a second supply use case, the agent can analyze invoices, packing slips, delivery notes, or shipment confirmations and reconcile them against purchase orders and inventory receipts. It should:

- Compare shipped quantities, unit prices, product identifiers, delivery dates, and supplier details against the purchase order.
- Flag missing items, over-shipments, under-shipments, duplicate invoices, price mismatches, damaged/expired items if documented, or late delivery.
- Recommend accepting the delivery, partially accepting it, disputing the supplier document, or escalating to procurement.
- Update only through a human-reviewed workflow unless later authorized.

### Capabilities

- Mock inventory and reservation lookup.
- Mock purchase order and supplier-history lookup.
- Lead-time prediction from previous deliveries.
- Reallocation feasibility checks.
- Purchase/replenishment recommendation generation.
- Supplier reconciliation and discrepancy detection.

### Explicit boundaries

- It should not automatically release reserved stock, create purchase orders, or dispute invoices without human approval unless later configured.
- It should account for priority and safety stock rules before recommending reserved-stock use.

## Cross-cutting requirements

- Human-in-the-loop review for all high-impact decisions.
- Audit logs for image ingestion, OCR results, classification, tool calls, and recommendations.
- Role-based access control around financial, medical, and procurement data should be represented as design constraints and mocked permission checks.
- PII/PHI redaction in logs and prompts should be represented in mock outputs and examples.
- Configurable confidence thresholds by document type and subtype.
- Unknown/unsupported document fallback.
- Test/evaluation sets for each route and use case.
- Clear source citations from extracted document spans to recommendations.
- Mock data adapters are mandatory for all external systems in the first version.

## Locked assumptions for this plan

- MAF is assumed to mean Microsoft Agent Framework unless corrected later.
- The current phase is agent definition, responsibilities, capabilities, handoff contracts, and mocked-data behavior only.
- All financial, medical, supply, procurement, supplier, OCR/document-intelligence, and storage dependencies are mocked.
- Azure AI Document Intelligence is the recommended production OCR/document-analysis service, but the first version uses a mock adapter with the same conceptual output shape.
- Specialized agents are recommendation-only; humans review and execute any real-world action.
- The upload surface can be decided later because it does not change the agent responsibilities.

## Implementation todos

1. Confirm scope and assumptions with the user, with mocked data as a locked constraint.
2. Define shared schemas for `DocumentContext`, `AgentRecommendation`, and confidence/error handling.
3. Define the deciding agent route map, classifier behavior, thresholds, and fallback paths.
4. Define the financial agent use cases, required tools, data contracts, rules, and recommendation format.
5. Define the medical agent use cases, approved knowledge sources, safety boundaries, and recommendation format.
6. Define the supply agent use cases, required tools, data contracts, rules, and recommendation format.
7. Define mock datasets and integration adapters for every external system.
8. Define evaluation scenarios for routing accuracy, OCR extraction quality, and each domain workflow.
9. After confirmation, map this design into the initial project structure and implementation tasks.
