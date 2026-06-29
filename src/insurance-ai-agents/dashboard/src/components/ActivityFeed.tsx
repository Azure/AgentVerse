import { useEffect, useRef } from 'react';
import { Bot, Brain, CheckCircle2, Loader2, AlertTriangle, Search, ShieldAlert, Scale, Gavel } from 'lucide-react';

export interface ActivityEvent {
  stage: string;
  status: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

interface Props {
  events: ActivityEvent[];
}

const stageConfig: Record<string, { label: string; icon: typeof Bot; thinkingMsg: string }> = {
  intake: {
    label: 'Claims Intake Agent',
    icon: Search,
    thinkingMsg: 'Leyendo la descripción del siniestro, verificando la póliza en el sistema, extrayendo datos clave y clasificando la severidad...',
  },
  risk_assessment: {
    label: 'Risk & Fraud Agent',
    icon: ShieldAlert,
    thinkingMsg: 'Consultando el historial de reclamaciones del cliente, comparando con patrones de fraude conocidos, calculando el score de riesgo...',
  },
  compliance: {
    label: 'Compliance Agent',
    icon: Scale,
    thinkingMsg: 'Verificando contra la normativa vigente (EU Insurance Directive, DGS, EU AI Act), validando umbrales regulatorios...',
  },
  decision: {
    label: 'Decisión Final',
    icon: Gavel,
    thinkingMsg: 'Agregando el análisis de los tres agentes especializados y aplicando las reglas de negocio...',
  },
};

function formatTime(ts: string) {
  try {
    return new Date(ts).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

function extractInsight(stage: string, data: Record<string, unknown>): { summary: string; details: string[] } | null {
  if (!data || Object.keys(data).length === 0) return null;

  if (stage === 'intake') {
    const details: string[] = [];
    if (data.policy_valid !== undefined) details.push(data.policy_valid ? '✓ Póliza verificada y activa' : '✗ Póliza no válida');
    if (data.severity) details.push(`Severidad: ${data.severity === 'high' ? 'alta' : data.severity === 'medium' ? 'media' : 'baja'}`);
    const extracted = data.extracted_data as Record<string, unknown> | undefined;
    if (extracted?.incident_type) details.push(`Tipo: ${extracted.incident_type}`);
    if (extracted?.estimated_amount) details.push(`Monto: ${Number(extracted.estimated_amount).toLocaleString('es-ES')}€`);
    const summary = (data.summary as string) || '';
    return { summary, details };
  }

  if (stage === 'risk_assessment') {
    const details: string[] = [];
    const score = data.risk_score as number;
    const fraud = data.fraud_probability as string;
    if (score !== undefined) details.push(`Risk score: ${score}/10 ${score <= 4 ? '(bajo)' : score <= 7 ? '(medio)' : '(alto)'}`);
    if (fraud) {
      const label = { low: 'baja', medium: 'media', high: 'alta' }[fraud] || fraud;
      details.push(`Probabilidad de fraude: ${label}`);
    }
    const factors = data.risk_factors as Array<Record<string, unknown>> | undefined;
    if (factors?.length) {
      const negatives = factors.filter((f) => f.impact === 'negative').map((f) => f.factor as string);
      const positives = factors.filter((f) => f.impact === 'positive').map((f) => f.factor as string);
      if (positives.length) details.push(`Factores positivos: ${positives.join(', ')}`);
      if (negatives.length) details.push(`Factores de riesgo: ${negatives.join(', ')}`);
    }
    const reasoning = (data.reasoning as string) || '';
    return { summary: reasoning, details };
  }

  if (stage === 'compliance') {
    const details: string[] = [];
    const decision = data.decision as string;
    if (decision) {
      const label = { approve: 'Aprobación automática', human_review: 'Revisión humana requerida', reject: 'Rechazo' }[decision] || decision;
      details.push(`Recomendación: ${label}`);
    }
    const regs = data.regulations_checked as string[] | undefined;
    if (regs?.length) details.push(`Regulaciones verificadas: ${regs.join(', ')}`);
    const reasoning = (data.reasoning as string) || '';
    return { summary: reasoning, details };
  }

  if (stage === 'decision') {
    const decision = data.decision as string;
    const confidence = data.confidence as number;
    const reasoning = (data.reasoning as string) || '';
    const details: string[] = [];
    if (decision) {
      const label = { approve: '✅ APROBADO', human_review: '⚠️ REVISIÓN HUMANA', reject: '❌ RECHAZADO' }[decision] || decision;
      details.push(`${label} · ${((confidence || 0) * 100).toFixed(0)}% confianza`);
    }
    return { summary: reasoning, details };
  }

  return null;
}

export default function ActivityFeed({ events }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  if (events.length === 0) return null;

  return (
    <div className="animate-slide-in rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <Brain className="h-4 w-4 text-primary-600" />
        <h3 className="text-sm font-medium uppercase tracking-wider text-gray-700">Razonamiento de los Agentes</h3>
      </div>
      <div className="max-h-[500px] space-y-3 overflow-y-auto pr-1">
        {events.map((ev, i) => {
          const config = stageConfig[ev.stage] || { label: ev.stage, icon: Bot, thinkingMsg: 'Procesando...' };
          const StageIcon = config.icon;
          const isProcessing = ev.status === 'processing';
          const isCompleted = ev.status === 'completed';
          const StatusIcon = isProcessing ? Loader2 : isCompleted ? CheckCircle2 : AlertTriangle;
          const statusIconClass = isProcessing
            ? 'text-primary-600 animate-spin'
            : isCompleted
              ? 'text-emerald-600'
              : 'text-red-600';
          const insight = isCompleted && ev.data ? extractInsight(ev.stage, ev.data) : null;

          return (
            <div key={i} className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
              <div className="flex items-center gap-2">
                <StatusIcon className={`h-4 w-4 ${statusIconClass}`} />
                <div className="flex h-7 w-7 items-center justify-center rounded-md border border-gray-200 bg-gray-50">
                  <StageIcon className="h-3.5 w-3.5 text-gray-400" />
                </div>
                <span className="text-sm font-semibold text-gray-800">{config.label}</span>
                <span className="ml-auto text-xs text-gray-500">{formatTime(ev.timestamp)}</span>
              </div>

              <div className="pt-3">
                {isProcessing && <p className="text-sm italic text-gray-600">{config.thinkingMsg}</p>}

                {isCompleted && insight && (
                  <div className="space-y-2">
                    {insight.details.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {insight.details.map((detail, j) => (
                          <span
                            key={j}
                            className="inline-flex items-center rounded-md border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] text-gray-700"
                          >
                            {detail}
                          </span>
                        ))}
                      </div>
                    )}
                    {insight.summary && (
                      <p className="mt-1 border-l-2 border-primary-200 pl-3 text-sm leading-relaxed text-gray-600">
                        {insight.summary}
                      </p>
                    )}
                  </div>
                )}

                {!isProcessing && !isCompleted && <p className="text-sm text-red-700">Error en el procesamiento del agente</p>}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
