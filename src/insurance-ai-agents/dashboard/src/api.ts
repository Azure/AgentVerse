import { acquireApiToken } from './auth/msalConfig';

const API_BASE = import.meta.env.VITE_API_URL || '';

/**
 * Helper que añade el Authorization header con el access token de MSAL
 * cuando VITE_AUTH_ENABLED='true'. Si no, hace fetch normal (modo demo abierto).
 */
async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const token = await acquireApiToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(`${API_BASE}${path}`, { ...init, headers });
}

export interface ClaimRequest {
  policy_id: string;
  customer_id: string;
  incident_type: string;
  description: string;
  estimated_amount: number;
  claim_id?: string;
  image_b64?: string;
}

export interface ClaimResult {
  claim_id: string;
  decision: 'approve' | 'human_review' | 'reject';
  confidence: number;
  reasoning: string;
  total_duration_ms: number;
  intake_result: Record<string, unknown>;
  risk_result: Record<string, unknown>;
  compliance_result: Record<string, unknown>;
  audit_trail: AuditEntry[];
  metadata?: Record<string, unknown>;
  timestamp: string;
}

export interface AuditEntry {
  stage: string;
  status: string;
  timestamp: string;
  duration_ms: number;
  result_summary: string;
}

export interface ProgressUpdate {
  type: 'progress';
  claim_id: string;
  stage: string;
  status: 'processing' | 'completed' | 'failed';
  data: Record<string, unknown>;
  timestamp: string;
}

export interface TokenUpdate {
  type: 'token';
  claim_id: string;
  agent: string;
  text: string;
  timestamp: string;
}

export type PipelineUpdate = ProgressUpdate | TokenUpdate;

export interface Scenario {
  policy_id: string;
  customer_id: string;
  incident_type: string;
  description: string;
  estimated_amount: number;
  expected_decision: string;
}

export async function getScenarios(): Promise<Record<string, Scenario>> {
  const res = await apiFetch(`/api/scenarios`);
  if (!res.ok) throw new Error('Failed to fetch scenarios');
  return res.json();
}

export async function evaluateClaim(req: ClaimRequest): Promise<ClaimResult> {
  const res = await apiFetch(`/api/claims/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Evaluation failed');
  }
  return res.json();
}

export function connectWebSocket(
  claimId: string,
  onUpdate: (update: PipelineUpdate) => void,
): { ws: WebSocket; ready: Promise<void> } {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = API_BASE ? new URL(API_BASE).host : window.location.host;
  const ws = new WebSocket(`${proto}//${host}/ws/claims/${claimId}`);
  const ready = new Promise<void>((resolve) => {
    ws.onopen = () => resolve();
  });
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data.type !== 'pong') onUpdate(data);
    } catch { /* ignore parse errors */ }
  };
  return { ws, ready };
}

/* ── Stats ── */
export interface StatsResponse {
  total_claims: number;
  approved: number;
  human_review: number;
  rejected: number;
  avg_duration_ms: number;
  total_amount: number;
  avg_risk_score: number;
  active_policies: number;
  decisions_breakdown: Record<string, number>;
}

export async function getStats(): Promise<StatsResponse> {
  const res = await apiFetch(`/api/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

/* ── Claims list ── */
export interface ClaimSummary {
  claim_id: string;
  decision: string;
  confidence: number;
  timestamp: string;
  total_duration_ms: number;
  customer_id?: string;
  policy_id?: string;
  estimated_amount?: number;
  reasoning?: string;
}

export async function getClaims(): Promise<ClaimSummary[]> {
  const res = await apiFetch(`/api/claims`);
  if (!res.ok) throw new Error('Failed to fetch claims');
  return res.json();
}

export async function getClaimsByCustomer(customerId: string): Promise<ClaimSummary[]> {
  const res = await apiFetch(`/api/claims/by-customer/${encodeURIComponent(customerId)}`);
  if (!res.ok) throw new Error('Failed to fetch claims for customer');
  return res.json();
}

export async function getPendingReview(): Promise<ClaimSummary[]> {
  const res = await apiFetch(`/api/claims/pending-review`);
  if (!res.ok) throw new Error('Failed to fetch pending review');
  return res.json();
}

export async function getClaimAudit(claimId: string): Promise<ClaimAuditDetail> {
  const res = await apiFetch(`/api/claims/${encodeURIComponent(claimId)}/audit`);
  if (!res.ok) throw new Error('Failed to fetch audit');
  return res.json();
}

export interface ClaimAuditDetail {
  claim_id: string;
  decision: string;
  confidence: number;
  reasoning: string;
  total_duration_ms: number;
  audit_trail: AuditEntry[];
  intake_result: Record<string, any>;
  risk_result: Record<string, any>;
  compliance_result: Record<string, any>;
  metadata?: Record<string, any>;
  has_image?: boolean;
  policy?: {
    policy_id: string;
    customer_name: string;
    vehicle: string;
    coverage_type: string;
    max_coverage: number;
    status?: string;
    start_date?: string;
    end_date?: string;
  } | null;
  customer_history?: {
    customer_id: string;
    name: string;
    years_as_customer: number;
    previous_claims: number;
    previous_claims_details: Array<{ year: number; type: string; amount: number; status: string }>;
    risk_profile: string;
    payment_history: string;
  } | null;
}

export async function getClaimImage(claimId: string): Promise<string | null> {
  const res = await apiFetch(`/api/claims/${encodeURIComponent(claimId)}/image`);
  if (!res.ok) return null;
  const data = await res.json();
  return data.image_b64 ?? null;
}

/* ── Policies ── */
export interface Policy {
  policy_id: string;
  customer_id?: string;
  customer_name: string;
  vehicle: string;
  coverage_type: string;
  max_coverage: number;
  status?: string;
  start_date?: string;
  end_date?: string;
}

export interface CustomerHistory {
  customer_id: string;
  name: string;
  years_as_customer: number;
  previous_claims: number;
  previous_claims_details: Array<{ year: number; type: string; amount: number; status: string }>;
  risk_profile: string;
  payment_history: string;
}

export interface PolicyDetail extends Policy {
  customer_history?: CustomerHistory | null;
}

export interface NewPolicyRequest {
  customer_id: string;
  vehicle: string;
  coverage_type: string;
  max_coverage: number;
  start_date?: string;
  end_date?: string;
}

/* ── Customers ── */
export interface NewCustomerRequest {
  name: string;
  years_as_customer: number;
  previous_claims: number;
  risk_profile: string;
  payment_history: string;
}

export interface CustomerDetail extends CustomerHistory {
  policies?: Policy[];
}

export async function getCustomers(): Promise<CustomerHistory[]> {
  const res = await apiFetch(`/api/customers`);
  if (!res.ok) throw new Error('Failed to fetch customers');
  return res.json();
}

export async function getCustomerDetail(customerId: string): Promise<CustomerDetail> {
  const res = await apiFetch(`/api/customers/${encodeURIComponent(customerId)}`);
  if (!res.ok) throw new Error('Failed to fetch customer');
  return res.json();
}

export async function registerCustomer(req: NewCustomerRequest): Promise<CustomerHistory> {
  const res = await apiFetch(`/api/customers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to register customer');
  }
  return res.json();
}

export async function getPolicies(): Promise<Policy[]> {
  const res = await apiFetch(`/api/policies`);
  if (!res.ok) throw new Error('Failed to fetch policies');
  return res.json();
}

export async function getPolicyDetail(policyId: string): Promise<PolicyDetail> {
  const res = await apiFetch(`/api/policies/${encodeURIComponent(policyId)}`);
  if (!res.ok) throw new Error('Failed to fetch policy');
  return res.json();
}

export async function registerPolicy(req: NewPolicyRequest): Promise<Policy> {
  const res = await apiFetch(`/api/policies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to register policy');
  }
  return res.json();
}

/* ── Security incidents ── */
export interface SecurityIncident {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  incident_type: string;
  severity: string;
  detected_at: string;
  description: string;
  raw_payload_excerpt: string;
  status: string;
}

export interface SecurityIncidentsResponse {
  total: number;
  open: number;
  incidents: SecurityIncident[];
}

export async function getSecurityIncidents(): Promise<SecurityIncidentsResponse> {
  const res = await apiFetch(`/api/security/incidents`);
  if (!res.ok) throw new Error('Failed to fetch security incidents');
  return res.json();
}

/* ── Governance ── */
export interface GovernancePolicy {
  id: string;
  name: string;
  active: boolean;
}

export interface CodeOwnership {
  path: string;
  owners: string[];
}

export interface GovernanceStatus {
  pipeline_version: string;
  git_commit: string;
  model: string;
  deployed_at: string;
  apim: {
    enabled: boolean;
    gateway_url: string;
    policies: GovernancePolicy[];
  };
  evals: {
    dataset_path: string;
    workflow: string;
    latest: null | {
      timestamp: string;
      total: number;
      passed: number;
      failed: number;
      pass_rate: number;
      model: string;
      via_apim: boolean;
    };
  };
  code_ownership: CodeOwnership[];
  checks: Record<string, boolean>;
}

export async function getGovernanceStatus(): Promise<GovernanceStatus> {
  const res = await apiFetch(`/api/governance/status`);
  if (!res.ok) throw new Error('Failed to fetch governance status');
  return res.json();
}
