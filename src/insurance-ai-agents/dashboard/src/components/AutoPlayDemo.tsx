import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import {
  AlertTriangle,
  Bell,
  ExternalLink,
  Headphones,
  Loader2,
  Mic,
  Pause,
  Play,
  Phone,
  SkipForward,
  X,
} from 'lucide-react';
import type { ClaimRequest, ClaimResult, PipelineUpdate, Scenario } from '../api';
import { connectWebSocket, getScenarios } from '../api';
import { AUTH_ENABLED, acquireApiToken } from '../auth/msalConfig';
import LiveStatsTicker from './autoplay/LiveStatsTicker';
import AgentThinkingPanel from './autoplay/AgentThinkingPanel';
import type { AgentName, AgentStatus } from './autoplay/AgentThinkingPanel';
import DecisionFinale from './autoplay/DecisionFinale';
import IntakeExtractionPanel from './autoplay/IntakeExtractionPanel';
import RiskGaugePanel from './autoplay/RiskGaugePanel';
import type { FraudProbability } from './autoplay/RiskGaugePanel';
import ComplianceChecklistPanel from './autoplay/ComplianceChecklistPanel';
import type { ComplianceRule, RuleStatus } from './autoplay/ComplianceChecklistPanel';
import SlideNavigator from './autoplay/SlideNavigator';
import type { SlideDescriptor, SlideStatus } from './autoplay/SlideNavigator';
import DecisionSlidePanel from './autoplay/DecisionSlidePanel';
import VoiceCallModal from './VoiceCallModal';
import { BRAND } from '../brand';

const API_BASE = import.meta.env.VITE_API_URL || '';
const DEMO_ORDER = ['low_risk', 'high_amount', 'human_review', 'fraudulent', 'prompt_injection'] as const;

const STAGE_TO_AGENT: Record<Stage, AgentName> = {
  intake: 'intake',
  risk_assessment: 'risk',
  compliance: 'compliance',
  decision: 'decision',
};

type ScenarioKey = (typeof DEMO_ORDER)[number];
type Stage = 'intake' | 'risk_assessment' | 'compliance' | 'decision';
type StageStatus = 'pending' | 'processing' | 'completed' | 'failed';
type DemoStatus = 'idle' | 'loading' | 'running' | 'voice' | 'finished' | 'error';
type NoticeKind = 'error' | 'info';
type ApiError = Error & { status?: number };

interface Props {
  open: boolean;
  onClose: () => void;
}

interface DemoScenario {
  key: ScenarioKey;
  scenario: Scenario;
}

interface DemoItem {
  scenarioKey: ScenarioKey;
  scenario: Scenario;
  result: ClaimResult;
  durationMs: number;
}

interface Notice {
  id: string;
  text: string;
  kind: NoticeKind;
  actionLabel?: string;
  onAction?: () => void;
}

// Slide state =================================================================
// Each pipeline agent lives as a "slide". When an agent finishes, its state is
// frozen in `snapshots[stage]` and the user can navigate between previous
// slides while the following ones keep running live.

interface AgentSnapshot {
  status: 'completed' | 'failed';
  durationMs: number;
  tokens: string;
  finalized: boolean;
  intake?: { extractedFields?: ExtractedFieldsView };
  risk?: { score: number | null; fraudProbability: FraudProbability | null };
  compliance?: { rules: ComplianceRule[] };
  decision?: {
    decision: ClaimResult['decision'];
    amount: number;
    reasoning?: string;
    riskScore: number | null;
  };
}

interface SlideState {
  viewingSlide: Stage;
  userPinnedSlide: boolean;
  snapshots: Partial<Record<Stage, AgentSnapshot>>;
  unseenCompletedSlides: Record<Stage, boolean>;
}

type SlideAction =
  | { type: 'CASE_STARTED' }
  | { type: 'SNAPSHOT_PROVISIONAL'; stage: Stage; snapshot: AgentSnapshot }
  | { type: 'SNAPSHOT_FINAL'; reconciled: Partial<Record<Stage, AgentSnapshot>> }
  | { type: 'USER_SELECTED_SLIDE'; slide: Stage }
  | { type: 'RETURN_TO_LIVE'; liveSlide: Stage }
  | { type: 'AUTO_FOLLOW_LIVE'; liveSlide: Stage };

const INITIAL_SLIDE_STATE: SlideState = {
  viewingSlide: 'intake',
  userPinnedSlide: false,
  snapshots: {},
  unseenCompletedSlides: {
    intake: false,
    risk_assessment: false,
    compliance: false,
    decision: false,
  },
};

function slideReducer(state: SlideState, action: SlideAction): SlideState {
  switch (action.type) {
    case 'CASE_STARTED':
      return { ...INITIAL_SLIDE_STATE };
    case 'SNAPSHOT_PROVISIONAL': {
      const existing = state.snapshots[action.stage];
      if (existing?.finalized) return state;
      const snapshots = { ...state.snapshots, [action.stage]: action.snapshot };
      const isViewing = state.viewingSlide === action.stage;
      const unseen = isViewing
        ? state.unseenCompletedSlides
        : { ...state.unseenCompletedSlides, [action.stage]: true };
      return { ...state, snapshots, unseenCompletedSlides: unseen };
    }
    case 'SNAPSHOT_FINAL': {
      const snapshots = { ...state.snapshots };
      (Object.keys(action.reconciled) as Stage[]).forEach((stage) => {
        const final = action.reconciled[stage];
        if (final) snapshots[stage] = final;
      });
      return { ...state, snapshots };
    }
    case 'USER_SELECTED_SLIDE': {
      const unseen = { ...state.unseenCompletedSlides, [action.slide]: false };
      return {
        ...state,
        viewingSlide: action.slide,
        userPinnedSlide: true,
        unseenCompletedSlides: unseen,
      };
    }
    case 'RETURN_TO_LIVE': {
      const unseen = { ...state.unseenCompletedSlides, [action.liveSlide]: false };
      return {
        ...state,
        viewingSlide: action.liveSlide,
        userPinnedSlide: false,
        unseenCompletedSlides: unseen,
      };
    }
    case 'AUTO_FOLLOW_LIVE': {
      if (state.userPinnedSlide) return state;
      if (state.viewingSlide === action.liveSlide) return state;
      const unseen = { ...state.unseenCompletedSlides, [action.liveSlide]: false };
      return {
        ...state,
        viewingSlide: action.liveSlide,
        unseenCompletedSlides: unseen,
      };
    }
    default:
      return state;
  }
}

const STAGE_DISPLAY_NAMES: Record<Stage, string> = {
  intake: 'Intake',
  risk_assessment: 'Risk',
  compliance: 'Compliance',
  decision: 'Decision',
};

const EMPTY_STAGE_STATUSES: Record<Stage, StageStatus> = {
  intake: 'pending',
  risk_assessment: 'pending',
  compliance: 'pending',
  decision: 'pending',
};

const COMPLETED_STAGE_STATUSES: Record<Stage, StageStatus> = {
  intake: 'completed',
  risk_assessment: 'completed',
  compliance: 'completed',
  decision: 'completed',
};

const SCENARIO_META: Record<ScenarioKey, { label: string; shortLabel: string; badge: string; glow: string }> = {
  low_risk: {
    label: 'Low Risk',
    shortLabel: 'Low Risk',
    badge: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    glow: 'shadow-md shadow-emerald-200/50',
  },
  high_amount: {
    label: 'High Amount',
    shortLabel: 'High Amount',
    badge: 'border-primary-200 bg-primary-50 text-primary-700',
    glow: 'shadow-md shadow-primary-200/50',
  },
  human_review: {
    label: 'Human Review',
    shortLabel: 'Human Review',
    badge: 'border-amber-200 bg-amber-50 text-amber-800',
    glow: 'shadow-md shadow-amber-200/50',
  },
  fraudulent: {
    label: 'Fraudulent',
    shortLabel: 'Fraudulent',
    badge: 'border-red-200 bg-red-50 text-red-700',
    glow: 'shadow-md shadow-red-200/50',
  },
  prompt_injection: {
    label: 'Prompt Injection',
    shortLabel: 'Prompt Injection',
    badge: 'border-primary-200 bg-primary-50 text-primary-700',
    glow: 'shadow-md shadow-primary-200/60',
  },
};

const DECISION_META: Record<ClaimResult['decision'], { label: string; badge: string }> = {
  approve: {
    label: 'Approved',
    badge: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  },
  human_review: {
    label: 'Human review',
    badge: 'border-amber-200 bg-amber-50 text-amber-800',
  },
  reject: {
    label: 'Rejected',
    badge: 'border-red-200 bg-red-50 text-red-700',
  },
};

const currencyFormatter = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 0,
});

function sleep(ms: number) {
  return new Promise<void>((resolve) => window.setTimeout(resolve, ms));
}

function formatElapsed(totalSeconds: number) {
  if (totalSeconds < 60) return `${totalSeconds}s`;
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes < 60) return `${minutes}m ${seconds.toString().padStart(2, '0')}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

function formatCaseDuration(durationMs: number) {
  return `${(durationMs / 1000).toFixed(1)}s`;
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) return error.message;
  return 'Unexpected error';
}

function isAbortError(error: unknown) {
  return error instanceof DOMException
    ? error.name === 'AbortError'
    : error instanceof Error && error.name === 'AbortError';
}

function createAbortError() {
  return new DOMException('Aborted', 'AbortError');
}

function getFraudProbability(result: ClaimResult): string {
  const riskResult = result.risk_result as Record<string, unknown>;
  return typeof riskResult?.fraud_probability === 'string' ? riskResult.fraud_probability.toLowerCase() : '';
}

function isSecurityFlagged(result: ClaimResult) {
  return Boolean((result as ClaimResult & { security_flagged?: boolean }).security_flagged);
}

function getFraudProbabilityTyped(result: ClaimResult | null): FraudProbability | null {
  if (!result) return null;
  const value = getFraudProbability(result);
  if (value === 'low' || value === 'medium' || value === 'high') return value;
  if (value === 'baja') return 'low';
  if (value === 'media') return 'medium';
  if (value === 'alta') return 'high';
  return null;
}

function getRiskScore(result: ClaimResult | null): number | null {
  if (!result) return null;
  const risk = result.risk_result as Record<string, unknown>;
  const raw = risk?.risk_score;
  if (typeof raw === 'number') return Math.round(raw * (raw <= 10 ? 10 : 1));
  if (typeof raw === 'string') {
    const n = parseFloat(raw);
    if (!Number.isNaN(n)) return Math.round(n * (n <= 10 ? 10 : 1));
  }
  return null;
}

interface ExtractedFieldsView {
  incident_type?: string;
  estimated_amount?: number;
  vehicle?: string;
  date?: string;
  location?: string;
}

// === Streaming JSON parsing helpers ============================================
// The LLM tokens stream raw JSON (response_format=PydanticModel). To avoid
// waiting for `executor_completed`, we extract top-level fields as they get
// closed in the partial JSON. This feeds the live viz panels.

function extractStringField(text: string, key: string): string | undefined {
  const regex = new RegExp(`"${key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"`, 'i');
  const m = text.match(regex);
  if (!m) return undefined;
  try {
    return JSON.parse(`"${m[1]}"`) as string;
  } catch {
    return m[1];
  }
}

function extractNumberField(text: string, key: string): number | undefined {
  const regex = new RegExp(`"${key}"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)`, 'i');
  const m = text.match(regex);
  if (!m) return undefined;
  const n = parseFloat(m[1]);
  return Number.isFinite(n) ? n : undefined;
}

function extractBooleanField(text: string, key: string): boolean | undefined {
  const regex = new RegExp(`"${key}"\\s*:\\s*(true|false)`, 'i');
  const m = text.match(regex);
  if (!m) return undefined;
  return m[1].toLowerCase() === 'true';
}

function parseStreamingIntake(tokens: string): ExtractedFieldsView | undefined {
  if (!tokens) return undefined;
  const view: ExtractedFieldsView = {};
  const incidentType = extractStringField(tokens, 'incident_type');
  if (incidentType) view.incident_type = incidentType;
  const amount = extractNumberField(tokens, 'estimated_amount');
  if (amount !== undefined && amount > 0) view.estimated_amount = amount;
  const vehicle = extractStringField(tokens, 'vehicle');
  if (vehicle) view.vehicle = vehicle;
  const date = extractStringField(tokens, 'date_of_incident');
  if (date) view.date = date;
  const location = extractStringField(tokens, 'location');
  if (location) view.location = location;
  return Object.keys(view).length > 0 ? view : undefined;
}

function parseStreamingRisk(tokens: string): { score: number | null; fraud: FraudProbability | null } {
  if (!tokens) return { score: null, fraud: null };
  let score: number | null = null;
  const raw = extractNumberField(tokens, 'risk_score');
  if (raw !== undefined) score = Math.round(raw * (raw <= 10 ? 10 : 1));
  let fraud: FraudProbability | null = null;
  const fp = extractStringField(tokens, 'fraud_probability')?.toLowerCase();
  if (fp === 'low' || fp === 'medium' || fp === 'high') fraud = fp;
  else if (fp === 'baja') fraud = 'low';
  else if (fp === 'media') fraud = 'medium';
  else if (fp === 'alta') fraud = 'high';
  return { score, fraud };
}

function parseStreamingCompliance(tokens: string): { compliant?: boolean } {
  if (!tokens) return {};
  return { compliant: extractBooleanField(tokens, 'compliant') };
}

function getExtractedFields(result: ClaimResult | null): ExtractedFieldsView | undefined {
  if (!result) return undefined;
  const intake = result.intake_result as Record<string, unknown>;
  const data = (intake?.extracted_data ?? {}) as Record<string, unknown>;
  const view: ExtractedFieldsView = {};
  if (typeof data.incident_type === 'string' && data.incident_type) view.incident_type = data.incident_type;
  if (typeof data.estimated_amount === 'number' && data.estimated_amount > 0) view.estimated_amount = data.estimated_amount;
  if (typeof data.vehicle === 'string' && data.vehicle) view.vehicle = data.vehicle;
  if (typeof data.date_of_incident === 'string' && data.date_of_incident) view.date = data.date_of_incident;
  if (typeof data.location === 'string' && data.location) view.location = data.location;
  return Object.keys(view).length > 0 ? view : undefined;
}

function buildComplianceRules(result: ClaimResult | null, stageStatuses: Record<Stage, StageStatus>): ComplianceRule[] {
  const base: ComplianceRule[] = [
    { id: 'policy_valid', label: 'Policy in force', status: 'pending' },
    { id: 'coverage', label: 'Coverage applies to the incident', status: 'pending' },
    { id: 'amount_threshold', label: 'Amount within the automatic limit', status: 'pending' },
    { id: 'fraud_indicators', label: 'No fraud patterns detected', status: 'pending' },
    { id: 'documentation', label: 'Complete documentation', status: 'pending' },
  ];

  const status = stageStatuses.compliance;
  if (status === 'pending') return base;

  if (status === 'processing' && !result) {
    return base.map((r, idx) => ({ ...r, status: idx === 0 ? 'checking' : 'pending' as RuleStatus }));
  }

  if (!result) return base;

  const compliance = result.compliance_result as Record<string, unknown>;
  const rulesApplied = (compliance?.rules_applied ?? {}) as Record<string, unknown>;
  const decision = result.decision;
  const reasoning = (result.reasoning ?? '').toLowerCase();
  const fraudProb = getFraudProbability(result);
  const securityFlagged = isSecurityFlagged(result);
  const amount = result.intake_result
    ? ((result.intake_result as Record<string, unknown>).extracted_data as Record<string, unknown> | undefined)?.estimated_amount
    : undefined;
  const numericAmount = typeof amount === 'number' ? amount : 0;
  const threshold = typeof rulesApplied.human_review_threshold === 'number' ? rulesApplied.human_review_threshold : 20000;
  const policyValid = typeof rulesApplied.policy_valid === 'boolean' ? rulesApplied.policy_valid : true;
  const coverageOk = typeof rulesApplied.coverage_applies === 'boolean' ? rulesApplied.coverage_applies : decision !== 'reject';

  return [
    {
      id: 'policy_valid',
      label: 'Policy in force',
      status: policyValid ? 'passed' : 'failed',
      detail: policyValid ? undefined : 'Policy not found or expired.',
    },
    {
      id: 'coverage',
      label: 'Coverage applies to the incident',
      status: coverageOk ? 'passed' : 'failed',
    },
    {
      id: 'amount_threshold',
      label: 'Amount within the automatic limit',
      status: numericAmount > threshold ? 'warning' : 'passed',
      detail: numericAmount > threshold
        ? `${numericAmount.toLocaleString('es-ES')} € exceeds the threshold of ${threshold.toLocaleString('es-ES')} €`
        : undefined,
    },
    {
      id: 'fraud_indicators',
      label: 'No fraud patterns detected',
      status: securityFlagged || fraudProb === 'high' || decision === 'reject' ? 'failed' : 'passed',
      detail: securityFlagged ? 'Manipulation attempt detected by the security guard.' : undefined,
    },
    {
      id: 'documentation',
      label: 'Complete documentation',
      status: reasoning.includes('missing') || reasoning.includes('incomplete') ? 'warning' : 'passed',
    },
  ];
}

function nextStageStatuses(previous: Record<Stage, StageStatus>, stage: Stage, status: StageStatus) {
  const order: Stage[] = ['intake', 'risk_assessment', 'compliance', 'decision'];
  const updated = { ...previous, [stage]: status };
  if (status === 'processing' || status === 'completed') {
    const stageIndex = order.indexOf(stage);
    order.slice(0, stageIndex).forEach((key) => {
      if (updated[key] === 'pending') updated[key] = 'completed';
    });
  }
  return updated;
}

async function evaluateClaimAbortable(req: ClaimRequest, signal: AbortSignal): Promise<ClaimResult> {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  const token = await acquireApiToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE}/api/claims/evaluate`, {
    method: 'POST',
    headers,
    body: JSON.stringify(req),
    signal,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    const error = new Error(typeof errorBody?.detail === 'string' ? errorBody.detail : 'Evaluation failed') as ApiError;
    error.status = response.status;
    throw error;
  }

  return response.json() as Promise<ClaimResult>;
}

function buildAgentSnapshot(
  stage: Stage,
  stageStatus: StageStatus,
  tokens: string,
  durationMs: number,
  result: ClaimResult | null,
  scenarioAmountFallback: number,
): AgentSnapshot {
  const base: AgentSnapshot = {
    status: stageStatus === 'failed' ? 'failed' : 'completed',
    durationMs: durationMs > 0 ? durationMs : 0,
    tokens,
    finalized: !!result,
  };
  if (stage === 'intake') {
    const extractedFields = getExtractedFields(result) ?? parseStreamingIntake(tokens);
    base.intake = { extractedFields };
  } else if (stage === 'risk_assessment') {
    const live = parseStreamingRisk(tokens);
    base.risk = {
      score: getRiskScore(result) ?? live.score,
      fraudProbability: getFraudProbabilityTyped(result) ?? live.fraud,
    };
  } else if (stage === 'compliance') {
    let rules: ComplianceRule[];
    if (result) {
      rules = buildComplianceRules(result, COMPLETED_STAGE_STATUSES);
    } else {
      // Provisional snapshot without result: instead of showing all rules as
      // 'pending' (which would look like "Completed" but empty), infer a
      // plausible state from the streamed JSON.
      const parsedCompliant = parseStreamingCompliance(tokens).compliant;
      const baseRules: ComplianceRule[] = [
        { id: 'policy_valid', label: 'Policy in force', status: 'passed' },
        { id: 'coverage', label: 'Coverage applies to the incident', status: 'passed' },
        { id: 'amount_threshold', label: 'Amount within the automatic limit', status: 'passed' },
        { id: 'fraud_indicators', label: 'No fraud patterns detected', status: parsedCompliant === false ? 'failed' : 'passed' },
        { id: 'documentation', label: 'Complete documentation', status: 'passed' },
      ];
      rules = baseRules;
    }
    base.compliance = { rules };
  } else if (stage === 'decision') {
    if (result) {
      const intake = result.intake_result as Record<string, unknown> | undefined;
      const data = (intake?.extracted_data ?? {}) as Record<string, unknown>;
      const amount = typeof data.estimated_amount === 'number' ? data.estimated_amount : scenarioAmountFallback;
      base.decision = {
        decision: result.decision,
        amount,
        reasoning: result.reasoning,
        riskScore: getRiskScore(result),
      };
      // Backend MAF does not emit a 'decision' stage over WebSocket: the final
      // decision is the consolidation of the 3 agents, and its real time is
      // result.total_duration_ms (measured end-to-end in the orchestrator). If
      // the locally measured duration is 0, we use that figure so the Decision
      // panel shows "AI time" instead of 0.0s.
      if (base.durationMs <= 0 && result.total_duration_ms > 0) {
        base.durationMs = result.total_duration_ms;
      }
    }
  }
  return base;
}

export default function AutoPlayDemo({ open, onClose }: Props) {
  const onCloseRef = useRef(onClose);
  const demoRunRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const pausedRef = useRef(false);
  const closeRequestedRef = useRef(false);
  const skipRequestedRef = useRef(false);
  const noticeTimersRef = useRef<number[]>([]);

  const [status, setStatus] = useState<DemoStatus>('idle');
  const [paused, setPaused] = useState(false);
  const [fatalError, setFatalError] = useState('');
  const [orderedScenarios, setOrderedScenarios] = useState<DemoScenario[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [currentScenarioKey, setCurrentScenarioKey] = useState<ScenarioKey | null>(null);
  const [currentClaimId, setCurrentClaimId] = useState('');
  const [stageStatuses, setStageStatuses] = useState<Record<Stage, StageStatus>>(() => ({ ...EMPTY_STAGE_STATUSES }));
  const [stageTokens, setStageTokens] = useState<Record<Stage, string>>(() => ({
    intake: '',
    risk_assessment: '',
    compliance: '',
    decision: '',
  }));
  const [feedItems, setFeedItems] = useState<DemoItem[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [finishedCount, setFinishedCount] = useState(0);
  const [currentResult, setCurrentResult] = useState<ClaimResult | null>(null);
  const [finaleVisible, setFinaleVisible] = useState(false);
  const [stageDurations, setStageDurations] = useState<Record<Stage, number>>(() => ({
    intake: 0,
    risk_assessment: 0,
    compliance: 0,
    decision: 0,
  }));
  // Visual phase shown on the Decision slide while the outputs of the 3
  // previous agents are consolidated before showing the final verdict.
  const [consolidationPhase, setConsolidationPhase] = useState<null | 0 | 1 | 2>(null);
  // State of the final "Voice call with Leo" step. 'awaiting' = showing the
  // intro and waiting for the user to launch the call; 'live' = the call is
  // in progress and the voice modal is open; 'closing' = the call ended and
  // we move to the wrap-up. The operator window is opened with window.open
  // and referenced here to focus / close it if needed.
  const [voicePhase, setVoicePhase] = useState<'awaiting' | 'live' | 'closing'>('awaiting');
  const [voiceSessionId, setVoiceSessionId] = useState<string | null>(null);
  const operatorWindowRef = useRef<Window | null>(null);
  const stageStartsRef = useRef<Record<Stage, number>>({
    intake: 0,
    risk_assessment: 0,
    compliance: 0,
    decision: 0,
  });

  // --- Slide state (agent navigation) ---------------------------------------
  const [slideState, dispatchSlide] = useReducer(slideReducer, INITIAL_SLIDE_STATE);
  const prevStageStatusesRef = useRef<Record<Stage, StageStatus>>({ ...EMPTY_STAGE_STATUSES });
  const viewingSlideRef = useRef<Stage>('intake');
  const userPinnedRef = useRef(false);
  const lastAutoChangeRef = useRef(0);
  const pendingToastStagesRef = useRef<Set<Stage>>(new Set());
  const toastTimerRef = useRef<number | null>(null);
  const snapshotsRef = useRef<Partial<Record<Stage, AgentSnapshot>>>({});
  const currentScenarioAmountRef = useRef<number>(0);
  const finalizedResultRef = useRef<ClaimResult | null>(null);
  // Minimum dwell (ms) during which the live slide does not auto-change:
  // avoids imperceptible jumps when an agent finishes extremely fast.
  const MIN_DWELL_MS = 1800;

  const clearNoticeTimers = useCallback(() => {
    noticeTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    noticeTimersRef.current = [];
    if (toastTimerRef.current !== null) {
      window.clearTimeout(toastTimerRef.current);
      toastTimerRef.current = null;
    }
    pendingToastStagesRef.current.clear();
  }, []);

  const stopPing = useCallback(() => {
    if (pingIntervalRef.current !== null) {
      window.clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const cleanupActiveCase = useCallback((abortRequest: boolean, clearFinale = abortRequest) => {
    stopPing();
    if (clearFinale) setFinaleVisible(false);
    if (abortRequest) controllerRef.current?.abort();
    controllerRef.current = null;
    wsRef.current?.close();
    wsRef.current = null;
  }, [stopPing]);

  const pushNotice = useCallback(
    (text: string, kind: NoticeKind = 'error', options?: { actionLabel?: string; onAction?: () => void }) => {
      const id = crypto.randomUUID();
      setNotices((previous) => [
        ...previous,
        { id, text, kind, actionLabel: options?.actionLabel, onAction: options?.onAction },
      ]);
      const timer = window.setTimeout(() => {
        setNotices((previous) => previous.filter((notice) => notice.id !== id));
        noticeTimersRef.current = noticeTimersRef.current.filter((item) => item !== timer);
      }, 5200);
      noticeTimersRef.current.push(timer);
    },
    [],
  );

  const dismissNotice = useCallback((id: string) => {
    setNotices((previous) => previous.filter((notice) => notice.id !== id));
  }, []);

  const closeDemo = useCallback(() => {
    closeRequestedRef.current = true;
    skipRequestedRef.current = false;
    setPaused(false);
    cleanupActiveCase(true);
    if (operatorWindowRef.current && !operatorWindowRef.current.closed) {
      try { operatorWindowRef.current.close(); } catch { /* noop */ }
    }
    operatorWindowRef.current = null;
    onCloseRef.current();
  }, [cleanupActiveCase]);

  const startVoiceCall = useCallback(() => {
    const sid = `voice-${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
    // We open the operator window BEFORE the customer modal so the observer
    // can hook into the session even if the bridge creation runs ahead. The
    // backend buffers the events and retries the attach for a few seconds if
    // the session does not exist yet.
    let openedWindow: Window | null = null;
    try {
      const url = `${window.location.origin}/?view=voice-operator&session=${encodeURIComponent(sid)}`;
      openedWindow = window.open(url, `operator-${sid}`, 'width=1280,height=820');
    } catch (err) {
      pushNotice(`The operator window could not be opened: ${getErrorMessage(err)}`, 'error');
      return;
    }
    if (!openedWindow) {
      // Popup blocked → we don't advance to 'live': we keep the user on the
      // intro so they can allow pop-ups and retry. Starting the call anyway
      // would lose the parallel view, which is the whole point.
      pushNotice(
        'The browser blocked the operator window. Allow pop-ups on this site and press again.',
        'error',
      );
      return;
    }
    operatorWindowRef.current = openedWindow;
    setVoiceSessionId(sid);
    setVoicePhase('live');
  }, [pushNotice]);

  const handleVoiceModalClose = useCallback(() => {
    setVoicePhase('closing');
    setStatus('finished');
    // We don't automatically close the operator window: let the user review
    // it. It will close when the demo modal is closed.
  }, []);

  const skipVoiceStep = useCallback(() => {
    setVoicePhase('closing');
    setStatus('finished');
  }, []);

  const expireSession = useCallback(() => {
    if (closeRequestedRef.current) return;
    closeRequestedRef.current = true;
    skipRequestedRef.current = false;
    setPaused(false);
    setStatus('error');
    setFatalError('Session expired, please sign in again');
    cleanupActiveCase(true);
    const timer = window.setTimeout(() => onCloseRef.current(), 1400);
    noticeTimersRef.current.push(timer);
  }, [cleanupActiveCase]);

  const waitForNextStep = useCallback(async (delayMs: number, runId: number) => {
    let remaining = delayMs;
    while (demoRunRef.current === runId && !closeRequestedRef.current) {
      if (skipRequestedRef.current) {
        skipRequestedRef.current = false;
        return 'skip' as const;
      }
      if (pausedRef.current || userPinnedRef.current) {
        await sleep(150);
        continue;
      }
      if (remaining <= 0) return 'resume' as const;
      const slice = Math.min(remaining, 150);
      await sleep(slice);
      remaining -= slice;
    }
    return 'close' as const;
  }, []);

  const waitForFinaleDelay = useCallback(async (delayMs: number, runId: number) => {
    let remaining = delayMs;
    while (remaining > 0) {
      if (demoRunRef.current !== runId || closeRequestedRef.current) return 'close' as const;
      if (skipRequestedRef.current) {
        skipRequestedRef.current = false;
        return 'skip' as const;
      }
      const slice = Math.min(remaining, 100);
      await sleep(slice);
      remaining -= slice;
    }
    return demoRunRef.current !== runId || closeRequestedRef.current ? 'close' as const : 'resume' as const;
  }, []);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open || paused || status !== 'running') return;
    const timer = window.setInterval(() => setElapsedSeconds((seconds) => seconds + 1), 1000);
    return () => window.clearInterval(timer);
  }, [open, paused, status]);

  useEffect(() => {
    if (!open) return;

    const runId = demoRunRef.current + 1;
    demoRunRef.current = runId;
    closeRequestedRef.current = false;
    skipRequestedRef.current = false;
    clearNoticeTimers();

    setStatus('loading');
    setPaused(false);
    setFatalError('');
    setOrderedScenarios([]);
    setCurrentIndex(0);
    setCurrentScenarioKey(null);
    setCurrentClaimId('');
    setStageStatuses({ ...EMPTY_STAGE_STATUSES });
    setFinaleVisible(false);
    setFeedItems([]);
    setNotices([]);
    setElapsedSeconds(0);
    setFinishedCount(0);
    setVoicePhase('awaiting');
    setVoiceSessionId(null);
    dispatchSlide({ type: 'CASE_STARTED' });
    snapshotsRef.current = {};
    prevStageStatusesRef.current = { ...EMPTY_STAGE_STATUSES };

    const runDemo = async () => {
      // Best-effort: pre-cache the token. We DON'T abort if it fails — many
      // demo setups run with backend AUTH_ENABLED=false where no token is
      // needed. If the backend actually requires auth we'll get a 401 from
      // the first request and handle it there.
      if (AUTH_ENABLED) {
        try {
          await acquireApiToken();
        } catch {
          /* ignore — let the request fail naturally if auth is required */
        }
      }

      let scenariosResponse: Record<string, Scenario>;
      try {
        scenariosResponse = await getScenarios();
      } catch (error) {
        if (demoRunRef.current !== runId || closeRequestedRef.current) return;
        const apiError = error as ApiError;
        if (apiError.status === 401) {
          expireSession();
          return;
        }
        setStatus('error');
        setFatalError(getErrorMessage(error) || 'The scenarios could not be loaded.');
        return;
      }

      if (demoRunRef.current !== runId || closeRequestedRef.current) return;

      const ordered = DEMO_ORDER.flatMap((key) => (scenariosResponse[key] ? [{ key, scenario: scenariosResponse[key] }] : []));
      if (ordered.length === 0) {
        setStatus('error');
        setFatalError('No prepared scenarios were found for the demo.');
        return;
      }

      setOrderedScenarios(ordered);
      setStatus('running');

      for (let index = 0; index < ordered.length; index += 1) {
        if (demoRunRef.current !== runId || closeRequestedRef.current) return;

        const demoScenario = ordered[index];
        const claimId = `CLM-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
        const startedAt = Date.now();

        cleanupActiveCase(false, true);
        skipRequestedRef.current = false;
        setCurrentIndex(index);
        setCurrentScenarioKey(demoScenario.key);
        setCurrentClaimId(claimId);
        setStageStatuses({ ...EMPTY_STAGE_STATUSES });
        setStageTokens({ intake: '', risk_assessment: '', compliance: '', decision: '' });
        setCurrentResult(null);
        setStageDurations({ intake: 0, risk_assessment: 0, compliance: 0, decision: 0 });
        stageStartsRef.current = { intake: 0, risk_assessment: 0, compliance: 0, decision: 0 };
        // Reset slide state when starting each case. Clears snapshots, the
        // user pin, pending notifications and visible toasts so the next case
        // starts fully "live" from intake.
        dispatchSlide({ type: 'CASE_STARTED' });
        snapshotsRef.current = {};
        prevStageStatusesRef.current = { ...EMPTY_STAGE_STATUSES };
        pendingToastStagesRef.current.clear();
        if (toastTimerRef.current !== null) {
          window.clearTimeout(toastTimerRef.current);
          toastTimerRef.current = null;
        }
        finalizedResultRef.current = null;
        setNotices([]);
        lastAutoChangeRef.current = Date.now();
        currentScenarioAmountRef.current = demoScenario.scenario.estimated_amount;
        setConsolidationPhase(null);

        const { ws, ready } = connectWebSocket(claimId, (update: PipelineUpdate) => {
          if (demoRunRef.current !== runId) return;
          if (update.type === 'progress') {
            const stage = update.stage as Stage;
            if (!(stage in EMPTY_STAGE_STATUSES)) return;
            const nextStatus: StageStatus = update.status === 'completed'
              ? 'completed'
              : update.status === 'processing'
                ? 'processing'
                : 'failed';
            if (nextStatus === 'processing') {
              stageStartsRef.current[stage] = Date.now();
            } else if (nextStatus === 'completed' && stageStartsRef.current[stage] > 0) {
              const dur = Date.now() - stageStartsRef.current[stage];
              setStageDurations((prev) => ({ ...prev, [stage]: dur }));
            }
            setStageStatuses((previous) => nextStageStatuses(previous, stage, nextStatus));
          } else if (update.type === 'token') {
            const agent = update.agent;
            // Backend MAF emits tokens with agent="risk_assessment" (not
            // "risk"). We accept both for compatibility and discard unknown
            // agents instead of mixing them with intake (previous bug).
            let stage: Stage | null = null;
            if (agent === 'risk' || agent === 'risk_assessment') stage = 'risk_assessment';
            else if (agent === 'intake' || agent === 'compliance' || agent === 'decision') stage = agent;
            if (stage === null) return;
            setStageTokens((previous) => ({ ...previous, [stage as Stage]: previous[stage as Stage] + update.text }));
          }
        });

        wsRef.current = ws;
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, 10000);

        const controller = new AbortController();
        controllerRef.current = controller;
        let skippedCurrent = false;

        try {
          await Promise.race([
            ready,
            sleep(1500),
            new Promise<never>((_, reject) => {
              controller.signal.addEventListener('abort', () => reject(createAbortError()), { once: true });
            }),
          ]);

          const result = await evaluateClaimAbortable({ ...demoScenario.scenario, claim_id: claimId }, controller.signal);
          if (demoRunRef.current !== runId || closeRequestedRef.current) return;

          if (stageStartsRef.current.decision > 0) {
            const decisionDuration = Date.now() - stageStartsRef.current.decision;
            setStageDurations((previous) => (previous.decision > 0
              ? previous
              : { ...previous, decision: decisionDuration }));
          }
          setStageStatuses({ ...COMPLETED_STAGE_STATUSES });
          setCurrentResult(result);
          const item: DemoItem = {
            scenarioKey: demoScenario.key,
            scenario: demoScenario.scenario,
            result,
            durationMs: result.total_duration_ms || Date.now() - startedAt,
          };
          setFeedItems((previous) => [...previous, item]);

          // Consolidation mini-sequence: 3 visible steps inside the Decision
          // slide. Turns an instant transition into a mini "final work"
          // experience before showing the verdict.
          const CONSOLIDATION_STEP_MS = 850;
          for (const phase of [0, 1, 2] as const) {
            setConsolidationPhase(phase);
            const action = await waitForFinaleDelay(CONSOLIDATION_STEP_MS, runId);
            if (action === 'close') {
              setConsolidationPhase(null);
              return;
            }
            if (action === 'skip') {
              skippedCurrent = true;
              break;
            }
          }
          setConsolidationPhase(null);
          // NOTE: DecisionFinale is no longer triggered automatically. The
          // Decision slide shows the verdict in the panel and the user can
          // open the celebratory final screen with the "View final screen" button.
        } catch (error) {
          if (demoRunRef.current !== runId || closeRequestedRef.current) return;

          const apiError = error as ApiError;
          skippedCurrent = skipRequestedRef.current && isAbortError(error);

          if (apiError.status === 401) {
            expireSession();
            return;
          }

          if (!skippedCurrent) {
            setStageStatuses((previous) => ({ ...previous, decision: 'failed' }));
            pushNotice(`Case ${index + 1} failed: ${getErrorMessage(error)}`, 'error');
          }
        } finally {
          cleanupActiveCase(false);
        }

        if (demoRunRef.current !== runId || closeRequestedRef.current) return;

        if (skipRequestedRef.current) {
          skippedCurrent = true;
          skipRequestedRef.current = false;
        }

        setFinishedCount((count) => count + 1);

        if (index < ordered.length - 1) {
          const nextAction = await waitForNextStep(skippedCurrent ? 0 : 2000, runId);
          if (nextAction === 'close') return;
        }
      }

      if (demoRunRef.current !== runId || closeRequestedRef.current) return;

      setCurrentScenarioKey(null);
      setCurrentClaimId('');
      setStageStatuses({ ...EMPTY_STAGE_STATUSES });
      // We move to the voice phase: the user decides whether to launch the
      // call with Leo (and the operator window) or skip straight to the
      // wrap-up. The transition to 'finished' is triggered by that flow.
      setStatus('voice');
    };

    void runDemo();

    return () => {
      closeRequestedRef.current = true;
      skipRequestedRef.current = false;
      if (demoRunRef.current === runId) demoRunRef.current = runId + 1;
      cleanupActiveCase(true);
      clearNoticeTimers();
    };
  }, [cleanupActiveCase, clearNoticeTimers, expireSession, open, pushNotice, waitForFinaleDelay, waitForNextStep]);

  const totalScenarios = orderedScenarios.length || DEMO_ORDER.length;
  const currentScenario = currentScenarioKey ? orderedScenarios[currentIndex]?.scenario ?? null : null;
  const currentScenarioMeta = currentScenarioKey ? SCENARIO_META[currentScenarioKey] : null;

  const totalAmount = useMemo(
    () => feedItems.reduce((sum, item) => sum + item.scenario.estimated_amount, 0),
    [feedItems],
  );
  const automaticDecisionCount = useMemo(
    () => feedItems.filter((item) => item.result.decision !== 'human_review').length,
    [feedItems],
  );
  const approveCount = useMemo(
    () => feedItems.filter((item) => item.result.decision === 'approve').length,
    [feedItems],
  );
  const fraudDetectedCount = useMemo(
    () => feedItems.filter(({ scenarioKey, result }) => (
      scenarioKey === 'prompt_injection'
      || scenarioKey === 'fraudulent'
      || result.decision === 'reject'
      || getFraudProbability(result) === 'high'
      || isSecurityFlagged(result)
    )).length,
    [feedItems],
  );
  const approvalRate = Math.round((approveCount / Math.max(finishedCount, 1)) * 100);
  const automationRateLive = Math.round((automaticDecisionCount / Math.max(finishedCount, 1)) * 100);
  const averageCaseSeconds = feedItems.length > 0
    ? feedItems.reduce((sum, item) => sum + Math.max(item.durationMs / 1000, 1), 0) / feedItems.length
    : 28;
  const remainingSeconds = status === 'finished'
    ? 0
    : Math.max(0, Math.round((totalScenarios - finishedCount) * averageCaseSeconds + Math.max(totalScenarios - finishedCount - 1, 0) * 2));

  // backendActiveStage: real state in the backend. It's the stage the
  // pipeline is currently processing (or the last completed one if all are
  // idle). This is independent of which slide the user is viewing.
  const backendActiveStage: Stage = useMemo(() => {
    const order: Stage[] = ['intake', 'risk_assessment', 'compliance', 'decision'];
    const processing = order.find((s) => stageStatuses[s] === 'processing');
    if (processing) return processing;
    if (consolidationPhase !== null) return 'decision';
    if (currentResult) return 'decision';
    const reversed = [...order].reverse();
    const lastCompleted = reversed.find((s) => stageStatuses[s] === 'completed');
    if (lastCompleted) return lastCompleted;
    return 'intake';
  }, [stageStatuses, consolidationPhase, currentResult]);

  const viewingSlide = slideState.viewingSlide;
  const viewingSnapshot = slideState.snapshots[viewingSlide];

  // Keep refs in sync for closures (effects without re-subscription).
  useEffect(() => { viewingSlideRef.current = slideState.viewingSlide; }, [slideState.viewingSlide]);
  useEffect(() => { userPinnedRef.current = slideState.userPinnedSlide; }, [slideState.userPinnedSlide]);
  useEffect(() => { snapshotsRef.current = slideState.snapshots; }, [slideState.snapshots]);

  // --- Auto-follow of the live agent ----------------------------------------
  // If the user hasn't pinned a slide, viewingSlide should follow the agent
  // currently processing in the backend. We respect a minimum dwell so we
  // don't jump between slides imperceptibly when an agent finishes very fast.
  useEffect(() => {
    if (status !== 'running') return;
    if (slideState.userPinnedSlide) return;
    if (slideState.viewingSlide === backendActiveStage) return;
    const elapsed = Date.now() - lastAutoChangeRef.current;
    const wait = Math.max(0, MIN_DWELL_MS - elapsed);
    const timer = window.setTimeout(() => {
      dispatchSlide({ type: 'AUTO_FOLLOW_LIVE', liveSlide: backendActiveStage });
      lastAutoChangeRef.current = Date.now();
    }, wait);
    return () => window.clearTimeout(timer);
  }, [backendActiveStage, slideState.userPinnedSlide, slideState.viewingSlide, status]);

  // --- Snapshot capture (provisional) ---------------------------------------
  // When a stage transitions from processing/pending → completed/failed, freeze
  // its current state as a snapshot. If the user isn't viewing that slide,
  // queue an aggregated notification (450ms debounce).
  //
  // NOTE: the decision slide is intentionally skipped for the 'completed'
  // case — its snapshot is built in SNAPSHOT_FINAL when currentResult arrives
  // (avoids showing "completed" without a verdict during the ms between the
  // WS event and the HTTP resolution). We do capture 'failed' here.
  useEffect(() => {
    if (status !== 'running') return;
    const prev = prevStageStatusesRef.current;
    const order: Stage[] = ['intake', 'risk_assessment', 'compliance', 'decision'];
    const newlyCompleted: Stage[] = [];
    order.forEach((stage) => {
      const prevStatus = prev[stage];
      const currStatus = stageStatuses[stage];
      if (stage === 'decision' && currStatus === 'completed') return;
      const transitioned = (prevStatus === 'processing' || prevStatus === 'pending')
        && (currStatus === 'completed' || currStatus === 'failed');
      if (!transitioned) return;
      const snapshot = buildAgentSnapshot(
        stage,
        currStatus,
        stageTokens[stage],
        stageDurations[stage],
        currentResult,
        currentScenarioAmountRef.current,
      );
      dispatchSlide({ type: 'SNAPSHOT_PROVISIONAL', stage, snapshot });
      if (currStatus === 'completed' && viewingSlideRef.current !== stage) {
        newlyCompleted.push(stage);
      }
    });
    if (newlyCompleted.length > 0) {
      newlyCompleted.forEach((s) => pendingToastStagesRef.current.add(s));
      if (toastTimerRef.current === null) {
        toastTimerRef.current = window.setTimeout(() => {
          const stages = Array.from(pendingToastStagesRef.current);
          pendingToastStagesRef.current.clear();
          toastTimerRef.current = null;
          const currentViewing = viewingSlideRef.current;
          const filtered = stages.filter((s) => s !== currentViewing);
          if (filtered.length === 0) return;
          const names = filtered.map((s) => STAGE_DISPLAY_NAMES[s]);
          const text = filtered.length === 1
            ? `${names[0]} completed its analysis`
            : `${filtered.length} agents completed · ${names.join(' · ')}`;
          const jumpTo = filtered[filtered.length - 1];
          pushNotice(text, 'info', {
            actionLabel: 'View slide',
            onAction: () => dispatchSlide({ type: 'USER_SELECTED_SLIDE', slide: jumpTo }),
          });
        }, 450);
      }
    }
    prevStageStatusesRef.current = { ...stageStatuses };
  }, [stageStatuses, stageTokens, stageDurations, currentResult, status, pushNotice]);

  // --- Snapshot finalization (when the full result arrives) -----------------
  // Reconciles all snapshots with the final data and, specifically, creates
  // the 'decision' snapshot for the first time (which is skipped in the
  // provisional capture effect to avoid showing "completed" without a verdict).
  useEffect(() => {
    if (!currentResult) return;
    if (finalizedResultRef.current === currentResult) return;
    finalizedResultRef.current = currentResult;
    if (status !== 'running') return;
    const order: Stage[] = ['intake', 'risk_assessment', 'compliance', 'decision'];
    const reconciled: Partial<Record<Stage, AgentSnapshot>> = {};
    order.forEach((stage) => {
      reconciled[stage] = buildAgentSnapshot(
        stage,
        'completed',
        stageTokens[stage],
        stageDurations[stage],
        currentResult,
        currentScenarioAmountRef.current,
      );
    });
    dispatchSlide({ type: 'SNAPSHOT_FINAL', reconciled });
    // If the user isn't viewing the decision slide, queue a specific
    // notification (the decision has just "truly completed").
    if (viewingSlideRef.current !== 'decision') {
      pendingToastStagesRef.current.add('decision');
      if (toastTimerRef.current === null) {
        toastTimerRef.current = window.setTimeout(() => {
          const stages = Array.from(pendingToastStagesRef.current);
          pendingToastStagesRef.current.clear();
          toastTimerRef.current = null;
          const currentViewing = viewingSlideRef.current;
          const filtered = stages.filter((s) => s !== currentViewing);
          if (filtered.length === 0) return;
          const names = filtered.map((s) => STAGE_DISPLAY_NAMES[s]);
          const text = filtered.length === 1
            ? `${names[0]} completed its analysis`
            : `${filtered.length} agents completed · ${names.join(' · ')}`;
          const jumpTo = filtered[filtered.length - 1];
          pushNotice(text, 'info', {
            actionLabel: 'View slide',
            onAction: () => dispatchSlide({ type: 'USER_SELECTED_SLIDE', slide: jumpTo }),
          });
        }, 450);
      }
    }
  }, [currentResult, status, stageTokens, stageDurations, pushNotice]);

  // --- Slides descriptor for SlideNavigator ---------------------------------
  const slideDescriptors: SlideDescriptor[] = useMemo(() => {
    const order: Stage[] = ['intake', 'risk_assessment', 'compliance', 'decision'];
    return order.map((stage) => {
      const snapshot = slideState.snapshots[stage];
      let slideStatusValue: SlideStatus;
      // Special decision case: keep 'live' until the final verdict arrives,
      // even if a provisional snapshot generated by the WS already exists.
      const decisionLackingFinal = stage === 'decision'
        && (consolidationPhase !== null || (currentResult === null && stageStatuses.decision === 'processing'));
      if (snapshot && !decisionLackingFinal) {
        slideStatusValue = snapshot.status === 'failed' ? 'failed' : 'completed';
      } else if (
        stage === backendActiveStage
        && (
          stageStatuses[stage] === 'processing'
          || (stage === 'decision' && (consolidationPhase !== null || currentResult !== null))
        )
      ) {
        slideStatusValue = 'live';
      } else if (decisionLackingFinal) {
        slideStatusValue = 'live';
      } else {
        slideStatusValue = 'pending';
      }
      return {
        key: stage,
        status: slideStatusValue,
        hasSnapshot: !!snapshot,
        unseen: !!slideState.unseenCompletedSlides[stage],
      };
    });
  }, [
    slideState.snapshots,
    slideState.unseenCompletedSlides,
    backendActiveStage,
    stageStatuses,
    consolidationPhase,
    currentResult,
  ]);

  // --- Panel data for the visible slide -------------------------------------
  // AgentThinkingPanel binds to the visible slide (not the live agent):
  // if the user reviews Intake, they see Intake's frozen thoughts.
  const viewingAgentStatus: AgentStatus = useMemo(() => {
    if (viewingSnapshot) return viewingSnapshot.status === 'failed' ? 'failed' : 'completed';
    const s = stageStatuses[viewingSlide];
    if (s === 'processing') return 'thinking';
    if (s === 'completed') return 'completed';
    if (s === 'failed') return 'failed';
    if (viewingSlide === 'decision' && consolidationPhase !== null) return 'thinking';
    return 'idle';
  }, [viewingSnapshot, viewingSlide, stageStatuses, consolidationPhase]);

  const viewingThoughtTokens = viewingSnapshot?.tokens ?? stageTokens[viewingSlide];
  const viewingDurationSeconds = (() => {
    const ms = viewingSnapshot?.durationMs ?? stageDurations[viewingSlide];
    return ms > 0 ? ms / 1000 : undefined;
  })();

  const liveExtractedFields = useMemo<ExtractedFieldsView | undefined>(() => {
    const fromResult = getExtractedFields(currentResult);
    if (fromResult) return fromResult;
    return parseStreamingIntake(stageTokens.intake);
  }, [currentResult, stageTokens.intake]);

  const liveRiskScore = useMemo<number | null>(() => {
    const fromResult = getRiskScore(currentResult);
    if (fromResult !== null) return fromResult;
    return parseStreamingRisk(stageTokens.risk_assessment).score;
  }, [currentResult, stageTokens.risk_assessment]);

  const liveFraudProbability = useMemo<FraudProbability | null>(() => {
    const fromResult = getFraudProbabilityTyped(currentResult);
    if (fromResult !== null) return fromResult;
    return parseStreamingRisk(stageTokens.risk_assessment).fraud;
  }, [currentResult, stageTokens.risk_assessment]);

  const liveComplianceRules = useMemo<ComplianceRule[]>(() => {
    if (currentResult || stageStatuses.compliance === 'pending') {
      return buildComplianceRules(currentResult, stageStatuses);
    }
    const tokens = stageTokens.compliance;
    const parsedCompliant = parseStreamingCompliance(tokens).compliant;
    const baseRules: ComplianceRule[] = [
      { id: 'policy_valid', label: 'Policy in force', status: 'pending' },
      { id: 'coverage', label: 'Coverage applies to the incident', status: 'pending' },
      { id: 'amount_threshold', label: 'Amount within the automatic limit', status: 'pending' },
      { id: 'fraud_indicators', label: 'No fraud patterns detected', status: 'pending' },
      { id: 'documentation', label: 'Complete documentation', status: 'pending' },
    ];
    if (stageStatuses.compliance !== 'processing') return baseRules;
    const charsPerRule = 150;
    const advanced = Math.min(baseRules.length, Math.floor(tokens.length / charsPerRule));
    const result = baseRules.map((rule, idx) => {
      if (idx < advanced) return { ...rule, status: 'passed' as RuleStatus };
      if (idx === advanced) return { ...rule, status: 'checking' as RuleStatus };
      return rule;
    });
    if (parsedCompliant === false && advanced >= 3) {
      result[3] = { ...result[3], status: 'failed' };
    }
    return result;
  }, [currentResult, stageStatuses, stageTokens.compliance]);

  const subtitle = useMemo(() => {
    if (status === 'loading') return 'Preparing scenarios, agents and real-time telemetry…';
    if (fatalError) return fatalError;
    if (status === 'finished') return `Demo completed · ${finishedCount} of ${totalScenarios} cases executed`;
    if (status === 'voice') return `Final step · voice call with ${BRAND.voiceAssistantName} (customer view + operator view)`;
    if (currentScenarioKey) {
      const base = `Processing case ${Math.min(currentIndex + 1, totalScenarios)} of ${totalScenarios} · ~${remainingSeconds} seconds left`;
      if (slideState.userPinnedSlide) return `${base} · Demo paused while you review slides`;
      return paused ? `${base} · pause active after this case` : base;
    }
    return 'Initializing the automatic demo…';
  }, [
    currentIndex,
    currentScenarioKey,
    fatalError,
    finishedCount,
    paused,
    remainingSeconds,
    slideState.userPinnedSlide,
    status,
    totalScenarios,
  ]);

  const handleSkip = useCallback(() => {
    if (status !== 'running') return;
    skipRequestedRef.current = true;
    setPaused(false);
    cleanupActiveCase(true);
  }, [cleanupActiveCase, status]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[140] bg-gray-900/40 backdrop-blur-sm" role="dialog" aria-modal="true">
      <div className="flex h-full flex-col bg-white">
        <header className="border-b border-gray-200 bg-white px-6 py-5 xl:px-10">
          <div className="mx-auto flex w-full max-w-[1600px] items-start justify-between gap-6">
            <div className="flex items-start gap-3">
              <div className="inline-flex shrink-0 items-center justify-center rounded-lg bg-white px-3 py-1.5 shadow-md ring-1 ring-gray-200">
                <img src={BRAND.logoUrl} alt={BRAND.logoAlt} className="h-6 w-auto" />
              </div>
              <div>
                <h2 className="text-2xl font-semibold tracking-tight text-gray-900">Automatic demo · 5 real cases</h2>
                <p className="mt-1 text-sm text-gray-600">{subtitle}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setPaused((value) => !value)}
                disabled={status !== 'running'}
                className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                {paused ? 'Resume' : 'Pause'}
              </button>
              <button
                type="button"
                onClick={handleSkip}
                disabled={status !== 'running'}
                className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <SkipForward className="h-4 w-4" />
                Skip to next
              </button>
              <button
                type="button"
                onClick={closeDemo}
                className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
              >
                <X className="h-4 w-4" />
                Close
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto bg-gray-50 px-6 py-6 xl:px-10 xl:py-8">
          <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6">
            {status === 'loading' && (
              <div className="flex min-h-[60vh] items-center justify-center">
                <div className="w-full max-w-xl rounded-[28px] border border-gray-200 bg-white p-10 text-center shadow-xl shadow-gray-200/60">
                  <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary-600" />
                  <h3 className="mt-5 text-2xl font-semibold text-gray-900">Preparing the automatic demo</h3>
                  <p className="mt-2 text-sm leading-7 text-gray-600">
                    Loading the 5 scenarios, connecting the pipeline and preparing the real-time feed.
                  </p>
                </div>
              </div>
            )}

            {status === 'error' && (
              <div className="flex min-h-[60vh] items-center justify-center">
                <div className="w-full max-w-2xl rounded-[28px] border border-red-200 bg-red-50 p-10 text-center shadow-xl shadow-red-100/50">
                  <AlertTriangle className="mx-auto h-12 w-12 text-red-600" />
                  <h3 className="mt-5 text-2xl font-semibold text-gray-900">The demo could not be launched</h3>
                  <p className="mt-3 text-sm leading-7 text-red-700">{fatalError || 'An unexpected error occurred while initializing the demo.'}</p>
                  <button
                    type="button"
                    onClick={closeDemo}
                    className="mt-8 inline-flex items-center gap-2 rounded-xl bg-primary-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-primary-700"
                  >
                    Back to the dashboard
                  </button>
                </div>
              </div>
            )}

            {status === 'voice' && (
              <div className="flex min-h-[70vh] items-center justify-center">
                <div className="w-full max-w-4xl rounded-[32px] border border-gray-200 bg-gradient-to-br from-white via-primary-50/40 to-primary-100/30 p-10 text-center shadow-xl shadow-gray-200/60 xl:p-14">
                  <div className="mx-auto inline-flex items-center gap-2 rounded-full bg-primary-100 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.3em] text-primary-700">
                    <Mic className="h-3.5 w-3.5" />
                    Final step · Voice call
                  </div>
                  <h3 className="mt-5 text-3xl font-semibold tracking-tight text-gray-900 xl:text-4xl">
                    Talk to {BRAND.voiceAssistantName}, the {BRAND.shortName} voice assistant
                  </h3>
                  <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-gray-700">
                    To close the demo, you'll experience the same pipeline from the other end of the phone.
                    Pressing the button opens two windows:
                  </p>

                  <div className="mt-8 grid gap-4 text-left md:grid-cols-2">
                    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                      <div className="flex items-center gap-3">
                        <span className="grid h-10 w-10 place-items-center rounded-full bg-primary-100 text-primary-700">
                          <Phone className="h-5 w-5" />
                        </span>
                        <h4 className="text-sm font-semibold text-gray-900">Customer view</h4>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-gray-600">
                        The call modal with {BRAND.voiceAssistantName}. Speak normally: identify yourself with your ID,
                        describe the claim and receive the final decision by voice.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                      <div className="flex items-center gap-3">
                        <span className="grid h-10 w-10 place-items-center rounded-full bg-emerald-100 text-emerald-700">
                          <Headphones className="h-5 w-5" />
                        </span>
                        <h4 className="text-sm font-semibold text-gray-900">Operator view</h4>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-gray-600">
                        Standalone window with the live transcript, the identified
                        customer's data and the multi-agent pipeline running live.
                      </p>
                    </div>
                  </div>

                  <div className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-left text-xs leading-6 text-amber-800">
                    <strong>Tip:</strong> place both windows side by side (customer on the left,
                    operator on the right) to see how each turn is reflected simultaneously in both.
                    If your browser blocks pop-ups, allow them on this site before pressing.
                  </div>

                  <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                    <button
                      type="button"
                      onClick={startVoiceCall}
                      className="inline-flex items-center gap-2 rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-primary-600/30 transition hover:bg-primary-700"
                    >
                      <Phone className="h-4 w-4" />
                      Start call with {BRAND.voiceAssistantName} + operator view
                      <ExternalLink className="h-3.5 w-3.5 opacity-70" />
                    </button>
                    <button
                      type="button"
                      onClick={skipVoiceStep}
                      className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                    >
                      <SkipForward className="h-4 w-4" />
                      Skip to the end
                    </button>
                  </div>
                </div>
              </div>
            )}

            {status === 'finished' && (
              <div className="flex min-h-[70vh] items-center justify-center">
                <div className="w-full max-w-5xl rounded-[32px] border border-gray-200 bg-gradient-to-br from-white via-gray-50 to-primary-50/40 p-10 text-center shadow-xl shadow-gray-200/60 xl:p-14">
                  <div className="mx-auto max-w-3xl">
                    <p className="text-sm font-semibold uppercase tracking-[0.35em] text-primary-700">Demo wrap-up</p>
                    <h3 className="mt-4 text-4xl font-semibold tracking-tight text-gray-900 xl:text-5xl">
                      ✨ {finishedCount} cases processed in {formatElapsed(elapsedSeconds)}
                    </h3>
                    <p className="mt-4 text-lg text-gray-700">
                      With manual analysis it would have taken <strong className="text-gray-900">3 hours 45 minutes</strong>
                    </p>
                  </div>

                  <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-2xl border border-gray-200 bg-white p-5">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">Automatic approval</p>
                      <p className="mt-3 text-3xl font-semibold text-emerald-700">{approvalRate}%</p>
                    </div>
                    <div className="rounded-2xl border border-gray-200 bg-white p-5">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">Frauds detected</p>
                      <p className="mt-3 text-3xl font-semibold text-red-700">{fraudDetectedCount}</p>
                    </div>
                    <div className="rounded-2xl border border-gray-200 bg-white p-5">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">Automatic decision</p>
                      <p className="mt-3 text-3xl font-semibold text-primary-700">{automaticDecisionCount}</p>
                    </div>
                    <div className="rounded-2xl border border-gray-200 bg-white p-5">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">Total processed</p>
                      <p className="mt-3 text-3xl font-semibold text-gray-900">{currencyFormatter.format(totalAmount)}</p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={closeDemo}
                    className="mt-10 inline-flex items-center gap-2 rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-primary-700"
                  >
                    Back to the dashboard
                  </button>
                </div>
              </div>
            )}

            {status === 'running' && (
              <>
                <LiveStatsTicker
                  totalProcessed={totalAmount}
                  casesCompleted={finishedCount}
                  totalCases={totalScenarios}
                  automationRate={automationRateLive}
                  fraudsDetected={fraudDetectedCount}
                  elapsedSeconds={elapsedSeconds}
                />

                {/* Scenario header */}
                <section className={`rounded-[28px] border border-gray-200 bg-gradient-to-br from-white via-gray-50 to-primary-50/30 p-5 xl:p-6 ${currentScenarioMeta?.glow ?? ''}`}>
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`inline-flex items-center rounded-full border px-4 py-1.5 text-sm font-medium ${currentScenarioMeta?.badge ?? 'border-gray-200 bg-gray-50 text-gray-700'}`}>
                        {currentScenarioMeta?.label ?? 'Preparing scenarios…'}
                      </div>
                      <div className="text-sm text-gray-600">
                        <span className="font-mono text-xs text-gray-500">{currentClaimId || '—'}</span>
                        <span className="mx-2 text-gray-300">·</span>
                        <span className="text-gray-900 font-semibold">{currencyFormatter.format(currentScenario?.estimated_amount ?? 0)}</span>
                      </div>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 xl:min-w-[360px]">
                      <div className="rounded-xl border border-gray-200 bg-white px-3 py-2">
                        <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500">Customer</p>
                        <p className="mt-0.5 text-sm font-medium text-gray-900">{currentScenario?.customer_id ?? '—'}</p>
                      </div>
                      <div className="rounded-xl border border-gray-200 bg-white px-3 py-2">
                        <p className="text-[10px] uppercase tracking-[0.2em] text-gray-500">Policy</p>
                        <p className="mt-0.5 text-sm font-medium text-gray-900">{currentScenario?.policy_id ?? '—'}</p>
                      </div>
                    </div>
                  </div>
                </section>

                {/* Slide navigator: per-agent tabs, free navigation */}
                <SlideNavigator
                  slides={slideDescriptors}
                  viewingSlide={viewingSlide}
                  liveSlide={backendActiveStage}
                  isPinned={slideState.userPinnedSlide}
                  onSelect={(slide) => dispatchSlide({ type: 'USER_SELECTED_SLIDE', slide })}
                  onReturnToLive={() => dispatchSlide({ type: 'RETURN_TO_LIVE', liveSlide: backendActiveStage })}
                />

                {/* Main two-column area: agent thinking + per-agent viz */}
                <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
                  <AgentThinkingPanel
                    agent={STAGE_TO_AGENT[viewingSlide]}
                    status={viewingAgentStatus}
                    thoughtTokens={viewingThoughtTokens}
                    durationSeconds={viewingDurationSeconds}
                  />

                  <div className="rounded-[28px] border border-gray-200 bg-gradient-to-br from-white via-gray-50 to-primary-50/30 p-5 xl:p-6">
                    {viewingSlide === 'intake' && (
                      <IntakeExtractionPanel
                        scenarioText={currentScenario?.description ?? ''}
                        active={viewingSnapshot ? true : stageStatuses.intake === 'processing' || stageStatuses.intake === 'completed'}
                        extractedFields={viewingSnapshot?.intake?.extractedFields ?? liveExtractedFields}
                        phaseLabel={
                          viewingSnapshot
                            ? 'Extracted data'
                            : stageStatuses.intake === 'completed'
                              ? 'Extracted data'
                              : 'Reading the claim report'
                        }
                      />
                    )}
                    {viewingSlide === 'risk_assessment' && (
                      <RiskGaugePanel
                        active={viewingSnapshot ? true : stageStatuses.risk_assessment !== 'pending'}
                        targetScore={viewingSnapshot?.risk?.score ?? liveRiskScore}
                        fraudProbability={viewingSnapshot?.risk?.fraudProbability ?? liveFraudProbability}
                        phaseLabel={
                          viewingSnapshot
                            ? 'Risk assessment'
                            : stageStatuses.risk_assessment === 'completed'
                              ? 'Risk assessment'
                              : 'Calculating score and fraud patterns'
                        }
                      />
                    )}
                    {viewingSlide === 'compliance' && (
                      <ComplianceChecklistPanel
                        active={viewingSnapshot ? true : stageStatuses.compliance !== 'pending'}
                        rules={viewingSnapshot?.compliance?.rules ?? liveComplianceRules}
                        phaseLabel={
                          viewingSnapshot
                            ? 'Regulatory validation'
                            : stageStatuses.compliance === 'completed'
                              ? 'Regulatory validation'
                              : 'Applying rules and thresholds'
                        }
                      />
                    )}
                    {viewingSlide === 'decision' && (
                      <DecisionSlidePanel
                        decision={
                          viewingSnapshot?.decision?.decision
                          ?? (currentResult ? currentResult.decision : null)
                        }
                        amount={
                          viewingSnapshot?.decision?.amount
                          ?? currentScenario?.estimated_amount
                          ?? 0
                        }
                        scenarioLabel={currentScenarioMeta?.shortLabel ?? '—'}
                        reasoning={viewingSnapshot?.decision?.reasoning ?? currentResult?.reasoning}
                        riskScore={viewingSnapshot?.decision?.riskScore ?? liveRiskScore}
                        durationMs={viewingSnapshot?.durationMs ?? stageDurations.decision}
                        status={
                          viewingSnapshot?.status === 'failed'
                            ? 'failed'
                            : consolidationPhase !== null
                              ? 'processing'
                              : (viewingSnapshot?.decision?.decision || currentResult)
                                ? 'completed'
                                : 'processing'
                        }
                        consolidationPhase={consolidationPhase}
                        onShowOverlay={
                          (viewingSnapshot?.decision?.decision || currentResult)
                            ? () => setFinaleVisible(true)
                            : undefined
                        }
                      />
                    )}
                  </div>
                </section>

                {/* Compact feed at the bottom */}
                <section className="rounded-[24px] border border-gray-200 bg-white p-5 shadow-md shadow-gray-200/50">
                  <div className="flex items-center justify-between border-b border-gray-200 pb-3">
                    <div className="flex items-center gap-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-gray-500">Feed</p>
                      <p className="text-sm text-gray-600">{feedItems.length} decision(s)</p>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                    {orderedScenarios.map((demo, idx) => {
                      const item = feedItems.find((f) => f.scenarioKey === demo.key);
                      const meta = SCENARIO_META[demo.key];
                      const isActive = idx === currentIndex && status === 'running' && !item;
                      const isPending = !item && !isActive;
                      const decisionMeta = item ? DECISION_META[item.result.decision] : null;
                      return (
                        <div
                          key={demo.key}
                          className={`rounded-xl border px-3 py-2.5 text-xs transition ${isActive
                              ? 'border-primary-300 bg-primary-50 animate-pulse-glow'
                              : isPending
                                ? 'border-gray-200 bg-gray-50 opacity-70'
                                : 'border-gray-200 bg-white'
                            }`}
                        >
                          <div className="flex items-center justify-between">
                            {decisionMeta ? (
                              <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-medium ${decisionMeta.badge}`}>
                                {decisionMeta.label}
                              </span>
                            ) : (
                              <span className="text-[10px] uppercase tracking-wider text-gray-500">
                                {isActive ? 'In progress' : isPending ? 'Pending' : '—'}
                              </span>
                            )}
                          </div>
                          <p className="mt-1.5 text-sm font-semibold text-gray-900 truncate">{meta.shortLabel}</p>
                          <p className="text-[10px] text-gray-500 truncate">
                            {currencyFormatter.format(demo.scenario.estimated_amount)}
                            {item ? ` · ${formatCaseDuration(item.durationMs)}` : ''}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </section>
              </>
            )}
          </div>
        </main>

        {finaleVisible && currentResult && currentScenarioKey && (
          <DecisionFinale
            key={`${currentScenarioKey}-finale`}
            decision={currentResult.decision}
            amount={currentScenario?.estimated_amount ?? 0}
            scenarioLabel={SCENARIO_META[currentScenarioKey].shortLabel}
            onDone={() => setFinaleVisible(false)}
          />
        )}

        {/* Voice modal: only during the final phase. It renders on top of
            the demo modal (z-[150] > z-[140]) and shares session_id with the
            operator window so both see the same conversation. */}
        <VoiceCallModal
          open={voicePhase === 'live' && !!voiceSessionId}
          onClose={handleVoiceModalClose}
          sessionId={voiceSessionId ?? undefined}
          zClassName="z-[150]"
        />

        {/* Toast stack: floating notifications at the bottom right */}
        {notices.length > 0 && (
          <div
            className="pointer-events-none fixed bottom-6 right-6 z-[170] flex w-[360px] max-w-[calc(100vw-3rem)] flex-col gap-3"
            aria-live="polite"
            aria-atomic="false"
          >
            {notices.map((notice) => {
              const isError = notice.kind === 'error';
              return (
                <div
                  key={notice.id}
                  className={`pointer-events-auto animate-slide-in-right overflow-hidden rounded-2xl border bg-white/95 shadow-xl shadow-gray-900/10 backdrop-blur-sm ring-1 ring-black/5 ${isError ? 'border-red-100' : 'border-gray-100'
                    }`}
                >
                  <div className="flex items-start gap-3 p-4">
                    <div
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${isError
                          ? 'bg-red-50 text-red-600 ring-1 ring-red-100'
                          : 'bg-primary-50 text-primary-600 ring-1 ring-primary-100'
                        }`}
                    >
                      {isError ? <AlertTriangle className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className={`text-[10px] font-semibold uppercase tracking-[0.22em] ${isError ? 'text-red-600' : 'text-primary-600'
                        }`}>
                        {isError ? 'Notice' : 'Notification'}
                      </p>
                      <p className="mt-1 break-words text-sm leading-snug text-gray-900">{notice.text}</p>
                      {notice.actionLabel && notice.onAction && (
                        <button
                          type="button"
                          onClick={() => {
                            notice.onAction?.();
                            dismissNotice(notice.id);
                          }}
                          className={`mt-2 inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition ${isError
                              ? 'bg-red-50 text-red-700 hover:bg-red-100'
                              : 'bg-primary-50 text-primary-700 hover:bg-primary-100'
                            }`}
                        >
                          {notice.actionLabel}
                        </button>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => dismissNotice(notice.id)}
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-gray-400 transition hover:bg-gray-100 hover:text-gray-700"
                      aria-label="Close notification"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div
                    className={`h-0.5 w-full origin-left ${isError ? 'bg-red-500/70' : 'bg-primary-500/70'
                      } animate-toast-countdown`}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
