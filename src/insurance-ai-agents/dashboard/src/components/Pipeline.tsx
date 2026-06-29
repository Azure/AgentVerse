import { Fragment, useEffect, useRef, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import { AlertTriangle, CheckCircle2, ChevronRight, FileSearch, Scale, ShieldAlert } from 'lucide-react';

type Stage = 'intake' | 'risk_assessment' | 'compliance' | 'decision';
type StageStatus = 'pending' | 'processing' | 'completed' | 'failed';
type StagePayloads = Partial<Record<Stage, Record<string, unknown>>>;
type StreamingStage = Exclude<Stage, 'decision'>;

interface Props {
  statuses: Record<Stage, StageStatus>;
  tokens: Record<Stage, string>;
  stageData?: StagePayloads;
}

interface StageDefinition {
  key: Stage;
  label: string;
  helper: string;
  icon: LucideIcon;
}

const stages: StageDefinition[] = [
  { key: 'intake', label: 'INTAKE', helper: 'Lectura de documentos y extracción', icon: FileSearch },
  { key: 'risk_assessment', label: 'RISK', helper: 'Scoring y señales de fraude', icon: ShieldAlert },
  { key: 'compliance', label: 'COMPLIANCE', helper: 'Reglas, cobertura y normativa', icon: Scale },
  { key: 'decision', label: 'DECISION', helper: 'Resolución final para el expediente', icon: CheckCircle2 },
];

const cannedMessages: Record<StreamingStage, string> = {
  intake: 'Leyendo descripción del siniestro... extrayendo policy_id, monto, tipo de incidente... validando estructura...',
  risk_assessment: 'Calculando score de riesgo... comprobando histórico del cliente... análisis de fraude...',
  compliance: 'Aplicando reglas de negocio... umbrales de revisión humana... validación regulatoria...',
};

const TEXT_TAIL_LIMIT = 220;

const statusStyles: Record<StageStatus, { card: string; icon: string; iconColor: string; pill: string; dot: string }> = {
  pending: {
    card: 'border-gray-200 bg-white shadow-sm',
    icon: 'border-gray-200 bg-gray-50',
    iconColor: 'text-gray-400',
    pill: 'border-gray-200 bg-gray-50 text-gray-500',
    dot: 'bg-gray-300',
  },
  processing: {
    card: 'border-primary-500 bg-white shadow-md shadow-primary-200/40',
    icon: 'border-primary-100 bg-primary-50',
    iconColor: 'text-primary-600',
    pill: 'border-primary-200 bg-primary-50 text-primary-700',
    dot: 'bg-primary-500 animate-pulse-soft',
  },
  completed: {
    card: 'border-emerald-300 bg-emerald-50/50 shadow-sm',
    icon: 'border-emerald-200 bg-emerald-50',
    iconColor: 'text-emerald-600',
    pill: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    dot: 'bg-emerald-500',
  },
  failed: {
    card: 'border-red-300 bg-red-50/50 shadow-sm',
    icon: 'border-red-200 bg-red-50',
    iconColor: 'text-red-600',
    pill: 'border-red-200 bg-red-50 text-red-700',
    dot: 'bg-red-500',
  },
};

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function formatDuration(durationMs: number | null): string | null {
  if (durationMs === null) return null;
  return `${(durationMs / 1000).toFixed(1)}s`;
}

function getVisibleTail(text: string, limit = TEXT_TAIL_LIMIT): string {
  if (text.length <= limit) return text;
  return `…${text.slice(-limit).trimStart()}`;
}

function readString(data: Record<string, unknown> | undefined, key: string): string | null {
  const value = data?.[key];
  return typeof value === 'string' ? value : null;
}

function readNumber(data: Record<string, unknown> | undefined, key: string): number | null {
  const value = data?.[key];
  return typeof value === 'number' ? value : null;
}

function formatConfidence(confidence: number | null): string | null {
  if (confidence === null || Number.isNaN(confidence)) return null;
  const value = confidence <= 1 ? confidence * 100 : confidence;
  return `${Math.round(value)}%`;
}

function formatDecisionLabel(decision: string | null): string {
  switch (decision) {
    case 'approve':
      return 'Aprobado';
    case 'human_review':
      return 'Revisión humana';
    case 'reject':
      return 'Rechazado';
    default:
      return 'Decisión generada';
  }
}

function getDecisionTone(decision: string | null): string {
  switch (decision) {
    case 'approve':
      return 'border-emerald-200 bg-emerald-50';
    case 'human_review':
      return 'border-amber-200 bg-amber-50';
    case 'reject':
      return 'border-red-200 bg-red-50';
    default:
      return 'border-gray-200 bg-gray-50';
  }
}

function StageCard({
  stage,
  status,
  tokenText,
  data,
}: {
  stage: StageDefinition;
  status: StageStatus;
  tokenText: string;
  data?: Record<string, unknown>;
}) {
  const [durationMs, setDurationMs] = useState<number | null>(null);
  const [syntheticLength, setSyntheticLength] = useState(0);
  const startedAtRef = useRef<number | null>(null);
  const previousStatusRef = useRef<StageStatus>(status);
  const stageStyle = statusStyles[status];
  const Icon = stage.icon;
  const isDecision = stage.key === 'decision';
  const streamingStage: StreamingStage | null = stage.key === 'decision' ? null : stage.key;
  const cannedMessage = streamingStage ? cannedMessages[streamingStage] : '';
  const hasRealTokens = tokenText.length > 0;
  const failureMessage = readString(data, 'error');
  const decision = readString(data, 'decision');
  const reasoning = readString(data, 'reasoning');
  const confidence = formatConfidence(readNumber(data, 'confidence'));

  useEffect(() => {
    if (status === 'pending') {
      startedAtRef.current = null;
      setDurationMs(null);
    }

    if (status === 'processing' && (previousStatusRef.current !== 'processing' || startedAtRef.current === null)) {
      startedAtRef.current = performance.now();
      setDurationMs(null);
    }

    if ((status === 'completed' || status === 'failed') && previousStatusRef.current === 'processing' && startedAtRef.current !== null) {
      setDurationMs(performance.now() - startedAtRef.current);
    }

    previousStatusRef.current = status;
  }, [status]);

  useEffect(() => {
    if (isDecision) return;

    if (status === 'pending') {
      setSyntheticLength(0);
      return;
    }

    if (status === 'completed' || status === 'failed') {
      if (!hasRealTokens) {
        setSyntheticLength(cannedMessage.length);
      }
      return;
    }

    if (status !== 'processing' || hasRealTokens) {
      return;
    }

    let intervalId: number | undefined;
    const timeoutId = window.setTimeout(() => {
      intervalId = window.setInterval(() => {
        setSyntheticLength((current) => {
          if (current >= cannedMessage.length) {
            if (intervalId !== undefined) window.clearInterval(intervalId);
            return cannedMessage.length;
          }
          return current + 1;
        });
      }, 30);
    }, 450);

    return () => {
      window.clearTimeout(timeoutId);
      if (intervalId !== undefined) window.clearInterval(intervalId);
    };
  }, [cannedMessage, hasRealTokens, isDecision, status]);

  const bubbleText = (() => {
    if (status === 'failed' && failureMessage) {
      return failureMessage;
    }

    if (isDecision) {
      const summary = formatDecisionLabel(decision);
      const headline = [summary, confidence].filter(Boolean).join(' · ');
      return reasoning ? `${headline}
${reasoning}` : headline;
    }

    if (hasRealTokens) {
      return getVisibleTail(tokenText);
    }

    return getVisibleTail(cannedMessage.slice(0, syntheticLength));
  })();

  const bubbleTitle = isDecision ? 'Resolución final' : 'El sistema está pensando';
  const bubbleTone = status === 'failed'
    ? 'border-red-200 bg-red-50'
    : isDecision
      ? getDecisionTone(decision)
      : 'border-gray-200 bg-gray-50';
  const shouldShowBubble = isDecision ? status === 'completed' || status === 'failed' : status !== 'pending';
  const showCursor = status === 'processing' && !isDecision;
  const durationLabel = formatDuration(durationMs);
  const pillText = status === 'processing'
    ? 'Procesando…'
    : status === 'completed'
      ? `Completado${durationLabel ? ` · ${durationLabel}` : ''}`
      : status === 'failed'
        ? 'Error'
        : 'Pendiente';
  const placeholderText = isDecision
    ? 'La resolución aparecerá aquí al final del flujo.'
    : 'El agente arrancará aquí cuando reciba el expediente.';

  return (
    <div
      className={cx(
        'relative flex min-h-[19rem] flex-1 overflow-hidden rounded-[28px] border p-5 transition-all duration-500 sm:p-6',
        stageStyle.card,
        status === 'processing' && 'animate-pulse-glow',
      )}
    >
      <div className="flex h-full w-full flex-col">
        <div className="flex items-start justify-between gap-4">
          <div
            className={cx(
              'flex h-16 w-16 items-center justify-center rounded-[22px] border shadow-sm sm:h-[4.5rem] sm:w-[4.5rem]',
              stageStyle.icon,
            )}
          >
            <Icon className={cx('h-8 w-8 sm:h-9 sm:w-9', stageStyle.iconColor)} />
          </div>

          {status === 'completed' ? (
            <div className="rounded-full border border-emerald-200 bg-emerald-50 p-1.5 text-emerald-600">
              <CheckCircle2 className="h-5 w-5 animate-pop-in" />
            </div>
          ) : status === 'failed' ? (
            <div className="rounded-full border border-red-200 bg-red-50 p-1.5 text-red-600">
              <AlertTriangle className="h-5 w-5" />
            </div>
          ) : null}
        </div>

        <div className="mt-5">
          <div className="text-[11px] font-semibold uppercase tracking-[0.34em] text-gray-500">{stage.label}</div>
          <p className="mt-2 text-sm leading-6 text-gray-600">{stage.helper}</p>
          <div
            className={cx(
              'mt-4 inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold tracking-[0.08em]',
              stageStyle.pill,
            )}
          >
            <span className={cx('h-2 w-2 rounded-full', stageStyle.dot)} />
            <span>{pillText}</span>
          </div>
        </div>

        <div className="mt-6 flex min-h-[8rem] flex-1 flex-col justify-end">
          {shouldShowBubble ? (
            <div className={cx('rounded-xl border p-3 shadow-sm transition-all duration-500', bubbleTone)}>
              <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-gray-500">
                <span className="h-1.5 w-1.5 rounded-full bg-primary-500" />
                {bubbleTitle}
              </div>
              <div className="flex h-[5.75rem] flex-col justify-end overflow-hidden">
                <p className="whitespace-pre-wrap break-words text-sm leading-6 text-gray-700">
                  {bubbleText || (isDecision ? 'La decisión aparecerá aquí al final del flujo.' : 'Esperando respuesta del agente…')}
                  {showCursor ? <span className="ml-0.5 inline-block animate-blink text-primary-500">▌</span> : null}
                </p>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm leading-6 text-gray-500">
              {placeholderText}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ArrowConnector({
  fromStatus,
  toStatus,
  orientation = 'horizontal',
}: {
  fromStatus: StageStatus;
  toStatus: StageStatus;
  orientation?: 'horizontal' | 'vertical';
}) {
  const isFlowing = (fromStatus === 'processing' || fromStatus === 'completed') && toStatus === 'pending';
  const isSolid = toStatus !== 'pending';
  const isFailed = fromStatus === 'failed' || toStatus === 'failed';

  return (
    <div
      className={cx(
        'relative flex items-center justify-center overflow-hidden',
        orientation === 'horizontal' ? 'h-10 w-full' : 'h-12 w-10 rotate-90',
      )}
    >
      <div
        className={cx(
          'absolute left-2 right-2 h-px rounded-full transition-colors duration-500',
          isFailed ? 'bg-red-200' : isSolid ? 'bg-primary-300' : 'bg-gray-200',
        )}
      />
      {isFlowing ? (
        <div className="pointer-events-none absolute left-2 top-1/2 h-[3px] w-16 -translate-y-1/2 rounded-full bg-gradient-to-r from-transparent via-primary-400 to-transparent shadow-[0_0_12px_rgba(236,0,0,0.35)] animate-light-slide" />
      ) : null}
      <div
        className={cx(
          'relative z-10 rounded-full border p-1.5 transition-colors duration-500',
          isFailed
            ? 'border-red-200 bg-red-50 text-red-600'
            : isSolid
              ? 'border-primary-200 bg-primary-50 text-primary-600'
              : 'border-gray-200 bg-white text-gray-300',
        )}
      >
        <ChevronRight className={cx('h-4 w-4', isFlowing && 'animate-pulse-soft')} />
      </div>
    </div>
  );
}

export default function Pipeline({ statuses, tokens, stageData = {} }: Props) {
  return (
    <div className="overflow-hidden rounded-[32px] border border-gray-200 bg-white p-6 shadow-sm lg:p-8">
      <div className="mb-6 flex flex-col gap-2 lg:mb-8">
        <h3 className="text-sm font-semibold uppercase tracking-[0.32em] text-primary-600">Pipeline multi-agente</h3>
        <p className="max-w-3xl text-sm leading-6 text-gray-600">
          Visualiza cada agente razonando en tiempo real, con señales de actividad, streaming y decisión final auditable.
        </p>
      </div>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-stretch lg:gap-3">
        {stages.map((stage, index) => (
          <Fragment key={stage.key}>
            <StageCard
              stage={stage}
              status={statuses[stage.key]}
              tokenText={tokens[stage.key]}
              data={stageData[stage.key]}
            />

            {index < stages.length - 1 ? (
              <>
                <div className="flex justify-center lg:hidden">
                  <ArrowConnector
                    orientation="vertical"
                    fromStatus={statuses[stage.key]}
                    toStatus={statuses[stages[index + 1].key]}
                  />
                </div>
                <div className="hidden w-20 shrink-0 items-center lg:flex">
                  <ArrowConnector
                    fromStatus={statuses[stage.key]}
                    toStatus={statuses[stages[index + 1].key]}
                  />
                </div>
              </>
            ) : null}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
