import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  CheckCircle2,
  Clock,
  FileSearch,
  Gauge,
  Headphones,
  Loader2,
  Phone,
  PhoneOff,
  Shield,
  User,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { BRAND } from '../brand';

/**
 * Operator dashboard for a live voice call. Connects to the backend as an
 * "observer" (no audio I/O) and renders the same call state the customer
 * sees plus a pipeline visualization so the operator can supervise the
 * conversation and the agent decision in real time.
 */

type Line = {
  who: 'user' | 'assistant' | 'system';
  text: string;
  ts: number; // wall clock ms when the bubble was added
};

type CustomerInfo = {
  customer_id?: string;
  name?: string;
  policy_id?: string;
  vehicle?: { make?: string; model?: string; year?: number } | string | null;
  coverage_type?: string;
};

type DecisionInfo = {
  decision?: string;
  claim_id?: string;
  reasoning?: string;
};

type Stage = 'intake' | 'risk' | 'compliance' | 'decision';
type StageStatus = 'pending' | 'running' | 'done';

const STAGE_ORDER: Stage[] = ['intake', 'risk', 'compliance', 'decision'];
const STAGE_LABEL: Record<Stage, string> = {
  intake: 'Extracción de datos',
  risk: 'Análisis de riesgo',
  compliance: 'Compliance',
  decision: 'Decisión',
};
const STAGE_ICON: Record<Stage, JSX.Element> = {
  intake: <FileSearch className="h-4 w-4" />,
  risk: <Gauge className="h-4 w-4" />,
  compliance: <Shield className="h-4 w-4" />,
  decision: <CheckCircle2 className="h-4 w-4" />,
};

function buildWsBase(): string {
  const apiBase = import.meta.env.VITE_API_URL || '';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = apiBase ? new URL(apiBase).host : window.location.host;
  return `${proto}//${host}`;
}

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

function formatVehicle(v: CustomerInfo['vehicle']): string {
  if (!v) return '—';
  if (typeof v === 'string') return v;
  const parts = [v.make, v.model, v.year ? String(v.year) : ''].filter(Boolean);
  return parts.join(' ') || '—';
}

function decisionBadge(decision: string | undefined): { label: string; cls: string; icon: JSX.Element } {
  const norm = (decision || '').toLowerCase();
  if (norm === 'approve' || norm === 'approved') {
    return {
      label: 'Aprobado automáticamente',
      cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
      icon: <CheckCircle2 className="h-4 w-4" />,
    };
  }
  if (norm === 'reject' || norm === 'rejected') {
    return {
      label: 'Rechazado',
      cls: 'bg-red-50 text-red-700 ring-red-200',
      icon: <XCircle className="h-4 w-4" />,
    };
  }
  if (norm === 'human_review' || norm === 'review') {
    return {
      label: 'Revisión humana requerida',
      cls: 'bg-amber-50 text-amber-700 ring-amber-200',
      icon: <AlertTriangle className="h-4 w-4" />,
    };
  }
  return {
    label: decision || 'Sin decisión',
    cls: 'bg-gray-100 text-gray-700 ring-gray-200',
    icon: <Activity className="h-4 w-4" />,
  };
}

export default function VoiceOperatorView({ sessionId }: { sessionId: string }) {
  const [status, setStatus] = useState<'connecting' | 'live' | 'ended' | 'error'>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [customer, setCustomer] = useState<CustomerInfo | null>(null);
  const [decision, setDecision] = useState<DecisionInfo | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [stageStatuses, setStageStatuses] = useState<Record<Stage, StageStatus>>({
    intake: 'pending',
    risk: 'pending',
    compliance: 'pending',
    decision: 'pending',
  });
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const assistantBufferRef = useRef('');
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const stageTimersRef = useRef<number[]>([]);
  const everOpenedRef = useRef(false);

  // Drive elapsed timer
  useEffect(() => {
    if (startedAt === null) return;
    const tick = () => setElapsedSec(Math.round((Date.now() - startedAt) / 1000));
    tick();
    const id = window.setInterval(tick, 500);
    return () => window.clearInterval(id);
  }, [startedAt]);

  // Auto-scroll transcript
  useEffect(() => {
    if (scrollerRef.current) scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
  }, [lines.length]);

  // Animate pipeline stages while submit_claim runs. We don't have stage
  // events from the backend in the voice flow (the multi-agent pipeline
  // executes synchronously inside submit_claim, then returns a single
  // result), so we drive a deterministic visual sequence between
  // hold_music_start and the tool.result that lets the operator follow
  // what's happening.
  useEffect(() => {
    if (!pipelineRunning) {
      stageTimersRef.current.forEach((t) => window.clearTimeout(t));
      stageTimersRef.current = [];
      return;
    }
    // Reset and animate sequentially.
    setStageStatuses({ intake: 'running', risk: 'pending', compliance: 'pending', decision: 'pending' });
    const t1 = window.setTimeout(() => {
      setStageStatuses({ intake: 'done', risk: 'running', compliance: 'pending', decision: 'pending' });
    }, 1500);
    const t2 = window.setTimeout(() => {
      setStageStatuses({ intake: 'done', risk: 'done', compliance: 'running', decision: 'pending' });
    }, 3500);
    const t3 = window.setTimeout(() => {
      setStageStatuses({ intake: 'done', risk: 'done', compliance: 'done', decision: 'running' });
    }, 5500);
    stageTimersRef.current = [t1, t2, t3];
    return () => {
      [t1, t2, t3].forEach((t) => window.clearTimeout(t));
      stageTimersRef.current = [];
    };
  }, [pipelineRunning]);

  // Open observer WebSocket
  useEffect(() => {
    if (!sessionId) return;
    const wsBase = buildWsBase();
    const url = `${wsBase}/ws/voice/${sessionId}/observe`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    setStatus('connecting');
    setError(null);
    setStartedAt(Date.now());

    ws.onopen = () => {
      everOpenedRef.current = true;
      setStatus('live');
      setError(null);
    };
    ws.onclose = () => {
      setStatus((prev) => (prev === 'error' ? prev : 'ended'));
    };
    ws.onerror = () => {
      // ws.onerror también se dispara en cierres "anormales" del servidor
      // (close 1006) al final de una llamada exitosa. Sólo marcamos error
      // real cuando NUNCA llegamos a abrir la conexión.
      if (!everOpenedRef.current) {
        setStatus('error');
        setError('No se pudo conectar al canal de observación.');
      }
    };
    ws.onmessage = (msg) => {
      // Cualquier mensaje recibido implica que el canal funciona. Si
      // teníamos un error transitorio, lo limpiamos.
      setError(null);
      let event: { type: string; [key: string]: unknown };
      try {
        event = JSON.parse(msg.data as string);
      } catch {
        return;
      }
      const t = event.type;
      // Skip noisy audio packets — the operator view doesn't play sound.
      if (t === 'audio.delta' || t === 'audio_chunk' || t === 'audio') return;

      if (t === 'observer.error') {
        setError(String(event.message || 'Observer error'));
        setStatus('error');
        return;
      }
      if (t === 'connected') {
        // not strictly necessary — observer attaches after upstream is up
        return;
      }
      if (t === 'transcript.user') {
        const text = String(event.text || '').trim();
        if (text) setLines((p) => [...p, { who: 'user', text, ts: Date.now() }]);
        return;
      }
      if (t === 'transcript.assistant.delta') {
        assistantBufferRef.current += String(event.text || '');
        return;
      }
      if (t === 'transcript.assistant.done') {
        const full = String(event.text || '') || assistantBufferRef.current;
        assistantBufferRef.current = '';
        if (full.trim()) setLines((p) => [...p, { who: 'assistant', text: full.trim(), ts: Date.now() }]);
        return;
      }
      if (t === 'tool.result') {
        const name = String(event.name || '');
        const result = event.result as Record<string, unknown> | undefined;
        if (name === 'lookup_customer' && result && typeof result === 'object') {
          if ((result as { customer_id?: unknown }).customer_id) {
            setCustomer(result as CustomerInfo);
            setLines((p) => [...p, {
              who: 'system',
              text: `Cliente identificado: ${(result as CustomerInfo).name ?? '—'}`,
              ts: Date.now(),
            }]);
          } else {
            setLines((p) => [...p, { who: 'system', text: 'DNI no encontrado en la base de clientes', ts: Date.now() }]);
          }
        } else if (name === 'submit_claim' && result && typeof result === 'object') {
          setDecision(result as DecisionInfo);
          setStageStatuses({ intake: 'done', risk: 'done', compliance: 'done', decision: 'done' });
          setPipelineRunning(false);
          setLines((p) => [...p, {
            who: 'system',
            text: `Decisión del pipeline: ${(result as DecisionInfo).decision ?? '?'} (${(result as DecisionInfo).claim_id ?? '?'})`,
            ts: Date.now(),
          }]);
        } else if (name === 'end_call') {
          setLines((p) => [...p, { who: 'system', text: `${BRAND.voiceAssistantName} finalizando la llamada…`, ts: Date.now() }]);
        }
        return;
      }
      if (t === 'hold_music_start') {
        setPipelineRunning(true);
        setLines((p) => [...p, { who: 'system', text: `${BRAND.voiceAssistantName} ha lanzado el pipeline multiagente`, ts: Date.now() }]);
        return;
      }
      if (t === 'hold_music_stop') {
        setPipelineRunning(false);
        return;
      }
      if (t === 'hangup' || t === 'session.ended' || t === 'closed') {
        setStatus('ended');
        setLines((p) => [...p, { who: 'system', text: 'Llamada finalizada', ts: Date.now() }]);
        return;
      }
      if (t === 'error') {
        setError(String(event.message || 'Error en el canal'));
        return;
      }
    };

    return () => {
      try {
        ws.close();
      } catch {
        /* noop */
      }
      wsRef.current = null;
      assistantBufferRef.current = '';
    };
  }, [sessionId]);

  const statusBadge = useMemo(() => {
    if (status === 'connecting')
      return { label: 'Conectando al canal…', cls: 'bg-primary-50 text-primary-700 ring-primary-200', icon: <Loader2 className="h-4 w-4 animate-spin" /> };
    if (status === 'live')
      return { label: 'Llamada en directo', cls: 'bg-emerald-50 text-emerald-700 ring-emerald-200', icon: <Activity className="h-4 w-4 animate-pulse" /> };
    if (status === 'ended')
      return { label: 'Llamada finalizada', cls: 'bg-gray-100 text-gray-700 ring-gray-200', icon: <PhoneOff className="h-4 w-4" /> };
    return { label: 'Error', cls: 'bg-red-50 text-red-700 ring-red-200', icon: <XCircle className="h-4 w-4" /> };
  }, [status]);

  const decisionView = decision ? decisionBadge(decision.decision) : null;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-50">
      {/* Top bar */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-full bg-primary-600 text-white">
              <Headphones className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Vista operador · supervisión en vivo</p>
              <h1 className="text-lg font-semibold text-gray-900">Llamada de voz · {sessionId}</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${statusBadge.cls}`}>
              {statusBadge.icon}
              {statusBadge.label}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-700 ring-1 ring-inset ring-gray-200">
              <Clock className="h-3.5 w-3.5" />
              {formatDuration(elapsedSec)}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl min-h-0 flex-1 flex-col gap-6 overflow-hidden px-6 py-6 lg:flex-row">
        {/* Left column: transcript */}
        <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
          <header className="flex items-center justify-between border-b border-gray-200 px-5 py-3">
            <div className="flex items-center gap-2">
              <Phone className="h-4 w-4 text-primary-600" />
              <h2 className="text-sm font-semibold text-gray-900">Conversación</h2>
            </div>
            <span className="text-xs text-gray-500">{lines.length} eventos</span>
          </header>
          <div ref={scrollerRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-5">
            {lines.length === 0 && (
              <p className="py-12 text-center text-sm text-gray-500">
                A la espera del primer turno del asistente…
              </p>
            )}
            {lines.map((l, i) => (
              <Bubble key={`${l.ts}-${i}`} line={l} />
            ))}
            {error && (
              <div className="flex items-start gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>
        </section>

        {/* Right column: customer + pipeline + decision */}
        <aside className="flex w-full min-h-0 flex-col gap-4 overflow-y-auto lg:max-w-md">
          {/* Customer card */}
          <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
              <User className="h-4 w-4 text-primary-600" />
              Cliente
            </h2>
            {customer ? (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-500">Nombre</dt>
                  <dd className="font-medium text-gray-900">{customer.name ?? '—'}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-500">ID cliente</dt>
                  <dd className="font-mono text-xs text-gray-700">{customer.customer_id ?? '—'}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-500">Póliza</dt>
                  <dd className="font-mono text-xs text-gray-700">{customer.policy_id ?? '—'}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-500">Vehículo</dt>
                  <dd className="text-right text-gray-900">{formatVehicle(customer.vehicle)}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-gray-500">Cobertura</dt>
                  <dd className="text-right text-gray-900">{customer.coverage_type ?? '—'}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-gray-500">A la espera de identificación por DNI…</p>
            )}
          </div>

          {/* Pipeline */}
          <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-gray-200">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
              <Activity className="h-4 w-4 text-primary-600" />
              Pipeline multiagente
            </h2>
            <ol className="space-y-2">
              {STAGE_ORDER.map((stage) => {
                const s = stageStatuses[stage];
                return (
                  <li key={stage} className="flex items-center gap-3 rounded-xl bg-gray-50 px-3 py-2 ring-1 ring-inset ring-gray-100">
                    <span className={`grid h-7 w-7 place-items-center rounded-full ${
                      s === 'done'
                        ? 'bg-emerald-100 text-emerald-700'
                        : s === 'running'
                          ? 'bg-primary-100 text-primary-700'
                          : 'bg-gray-200 text-gray-500'
                    }`}>
                      {s === 'running' ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : STAGE_ICON[stage]}
                    </span>
                    <span className="flex-1 text-sm font-medium text-gray-800">{STAGE_LABEL[stage]}</span>
                    <span className={`text-[11px] font-semibold uppercase tracking-wide ${
                      s === 'done' ? 'text-emerald-700' : s === 'running' ? 'text-primary-700' : 'text-gray-400'
                    }`}>
                      {s === 'done' ? 'Listo' : s === 'running' ? 'En curso' : 'En espera'}
                    </span>
                  </li>
                );
              })}
            </ol>
            {pipelineRunning && (
              <p className="mt-3 text-xs text-gray-500">
                Los agentes están evaluando el caso. El cliente escucha música en espera.
              </p>
            )}
          </div>

          {/* Decision banner */}
          {decisionView && (
            <div className={`rounded-2xl p-5 shadow-sm ring-1 ring-inset ${decisionView.cls}`}>
              <div className="flex items-center gap-2 text-sm font-semibold">
                {decisionView.icon}
                <span>{decisionView.label}</span>
              </div>
              {decision?.claim_id && (
                <p className="mt-2 font-mono text-xs">Parte: {decision.claim_id}</p>
              )}
              {decision?.reasoning && (
                <p className="mt-2 text-xs leading-relaxed opacity-80">{decision.reasoning}</p>
              )}
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}

function Bubble({ line }: { line: Line }) {
  const time = new Date(line.ts).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  if (line.who === 'system') {
    return (
      <div className="mx-auto flex max-w-xl items-center justify-center gap-2 rounded-full bg-gray-100 px-3 py-1 text-center text-[11px] uppercase tracking-wide text-gray-600">
        <span className="font-mono text-[10px] text-gray-400">{time}</span>
        <span>{line.text}</span>
      </div>
    );
  }
  const isUser = line.who === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow-sm ${
          isUser ? 'bg-primary-600 text-white' : 'bg-white text-gray-800 ring-1 ring-gray-200'
        }`}
      >
        <p className={`mb-0.5 text-[10px] font-semibold uppercase tracking-wide ${
          isUser ? 'text-white/70' : 'text-primary-600'
        }`}>
          {isUser ? 'Cliente' : BRAND.voiceAssistantName} · {time}
        </p>
        {line.text}
      </div>
    </div>
  );
}
