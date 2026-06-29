import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import type { LucideIcon } from 'lucide-react';
import { AlertTriangle, CheckCircle2, Maximize2, Users, XCircle, Loader2, Sparkles } from 'lucide-react';

type DecisionKind = 'approve' | 'human_review' | 'reject';

export interface DecisionSlidePanelProps {
  decision: DecisionKind | null;
  amount: number;
  scenarioLabel: string;
  reasoning?: string;
  riskScore?: number | null;
  durationMs?: number;
  status: 'processing' | 'completed' | 'failed';
  consolidationPhase: 0 | 1 | 2 | null;
  onShowOverlay?: () => void;
}

interface DecisionMeta {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  cardClass: string;
  badgeClass: string;
  iconShellClass: string;
  accentText: string;
}

const DECISION_META: Record<DecisionKind, DecisionMeta> = {
  approve: {
    icon: CheckCircle2,
    title: 'APROBADO',
    subtitle: 'Resolución automática emitida correctamente.',
    cardClass: 'border-emerald-200 bg-gradient-to-br from-white via-emerald-50/60 to-white shadow-md shadow-emerald-100/60',
    badgeClass: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    iconShellClass: 'border-emerald-200 bg-emerald-50 text-emerald-600',
    accentText: 'text-emerald-700',
  },
  human_review: {
    icon: Users,
    title: 'REVISIÓN HUMANA',
    subtitle: 'Supera umbral de aprobación automática.',
    cardClass: 'border-amber-200 bg-gradient-to-br from-white via-amber-50/60 to-white shadow-md shadow-amber-100/60',
    badgeClass: 'border-amber-200 bg-amber-50 text-amber-800',
    iconShellClass: 'border-amber-200 bg-amber-50 text-amber-600',
    accentText: 'text-amber-700',
  },
  reject: {
    icon: XCircle,
    title: 'RECHAZADO',
    subtitle: 'Posible fraude detectado.',
    cardClass: 'border-red-200 bg-gradient-to-br from-white via-red-50/60 to-white shadow-md shadow-red-100/60',
    badgeClass: 'border-red-200 bg-red-50 text-red-700',
    iconShellClass: 'border-red-200 bg-red-50 text-red-600',
    accentText: 'text-red-700',
  },
};

interface ConfettiParticle {
  id: number;
  left: number;
  size: number;
  delay: number;
  duration: number;
  drift: number;
  colorClass: string;
}

const CONFETTI_COLORS = ['bg-emerald-400', 'bg-primary-400', 'bg-amber-400', 'bg-emerald-300', 'bg-primary-300'] as const;

function buildParticleStyle(particle: ConfettiParticle): CSSProperties {
  return {
    left: `${particle.left}%`,
    top: '-12%',
    width: `${particle.size}px`,
    height: `${particle.size * 1.7}px`,
    animationDelay: `${particle.delay}s`,
    animationDuration: `${particle.duration}s`,
    '--confetti-drift': `${particle.drift}px`,
  } as CSSProperties;
}

const CONSOLIDATION_STEPS = [
  { label: 'Reconciliando outputs', detail: 'Cruzando salidas de Intake, Risk y Compliance' },
  { label: 'Calculando confianza', detail: 'Ponderando señales de los 3 agentes' },
  { label: 'Emitiendo decisión final', detail: 'Generando justificación y audit trail' },
] as const;

function formatAmount(amount: number) {
  return `${Math.max(0, Math.round(amount)).toLocaleString('es-ES')} €`;
}

function formatDuration(durationMs?: number) {
  if (!durationMs || durationMs <= 0) return null;
  return `${(durationMs / 1000).toFixed(1)} s`;
}

export default function DecisionSlidePanel({
  decision,
  amount,
  scenarioLabel,
  reasoning,
  riskScore,
  durationMs,
  status,
  consolidationPhase,
  onShowOverlay,
}: DecisionSlidePanelProps) {
  const [confettiSeed, setConfettiSeed] = useState<number | null>(null);
  const lastSeedRef = useRef<string | null>(null);

  useEffect(() => {
    if (status !== 'completed' || !decision) return;
    const key = `${scenarioLabel}-${decision}`;
    if (lastSeedRef.current === key) return;
    lastSeedRef.current = key;
    if (decision === 'approve') setConfettiSeed(Date.now());
  }, [decision, scenarioLabel, status]);

  const particles = useMemo<ConfettiParticle[]>(() => {
    if (confettiSeed === null) return [];
    return Array.from({ length: 32 }, (_, idx) => ({
      id: idx,
      left: Math.random() * 100,
      size: 5 + Math.random() * 6,
      delay: Math.random() * 0.4,
      duration: 2.2 + Math.random() * 1.6,
      drift: (Math.random() - 0.5) * 60,
      colorClass: CONFETTI_COLORS[idx % CONFETTI_COLORS.length],
    }));
  }, [confettiSeed]);

  if (status === 'failed') {
    return (
      <div className="relative flex h-full min-h-[420px] flex-col items-center justify-center gap-4 rounded-2xl border border-red-200 bg-red-50/50 px-6 py-10 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-full border border-red-200 bg-white text-red-600">
          <AlertTriangle className="h-7 w-7" />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-red-700">Error en consolidación</p>
          <h3 className="mt-2 text-xl font-semibold tracking-tight text-gray-900 xl:text-2xl">
            No se pudo emitir la decisión
          </h3>
          <p className="mt-2 text-sm text-gray-700">{scenarioLabel}</p>
          <p className="mt-3 text-xs text-gray-500">
            El agente de decisión no pudo finalizar el análisis para este caso.
          </p>
        </div>
      </div>
    );
  }

  if (status === 'processing' || !decision) {
    const activePhase: 0 | 1 | 2 = consolidationPhase ?? 0;
    return (
      <div className="relative flex h-full min-h-[420px] flex-col gap-4 px-1 py-4">
        <div className="text-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-gray-500">Consolidación</p>
          <h3 className="mt-2 text-2xl font-semibold tracking-tight text-gray-900 xl:text-3xl">
            Preparando la decisión final
          </h3>
          <p className="mt-2 text-sm text-gray-600">{scenarioLabel}</p>
        </div>
        <ul className="mx-auto mt-2 w-full max-w-md space-y-3">
          {CONSOLIDATION_STEPS.map((step, idx) => {
            const isActive = idx === activePhase;
            const isDone = idx < activePhase;
            return (
              <li
                key={step.label}
                className={`flex items-start gap-3 rounded-2xl border px-4 py-3 transition-all duration-300 ${
                  isDone
                    ? 'border-emerald-200 bg-emerald-50'
                    : isActive
                      ? 'border-primary-200 bg-primary-50'
                      : 'border-gray-200 bg-gray-50 opacity-70'
                }`}
              >
                <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  isDone
                    ? 'bg-emerald-500 text-white'
                    : isActive
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 text-gray-500'
                }`}>
                  {isDone ? '✓' : isActive ? '•' : idx + 1}
                </span>
                <div className="flex-1">
                  <p className={`text-sm font-semibold ${isActive ? 'text-primary-700' : isDone ? 'text-emerald-700' : 'text-gray-700'}`}>
                    {step.label}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">{step.detail}</p>
                </div>
                {isActive ? (
                  <Loader2 className="mt-1 h-4 w-4 animate-spin text-primary-500" />
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  const meta = DECISION_META[decision];
  const Icon = meta.icon;
  const duration = formatDuration(durationMs);

  return (
    <div className="relative h-full min-h-[420px] overflow-hidden">
      {particles.length > 0 && (
        <div className="pointer-events-none absolute inset-0 z-10 overflow-hidden">
          {particles.map((particle) => (
            <span
              key={particle.id}
              className={`absolute block rounded-sm ${particle.colorClass} animate-confetti-fall`}
              style={buildParticleStyle(particle)}
            />
          ))}
        </div>
      )}

      <div className={`relative z-0 flex h-full flex-col gap-4 rounded-2xl border px-5 py-6 ${meta.cardClass}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className={`flex h-12 w-12 items-center justify-center rounded-xl border ${meta.iconShellClass}`}>
              <Icon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-500">Decisión final</p>
              <h3 className={`text-2xl font-bold tracking-tight ${meta.accentText}`}>{meta.title}</h3>
            </div>
          </div>
          {onShowOverlay && (
            <button
              type="button"
              onClick={onShowOverlay}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
              title="Mostrar el cierre celebratorio a pantalla completa"
            >
              <Maximize2 className="h-3.5 w-3.5" />
              Ver pantalla final
            </button>
          )}
        </div>

        <p className="text-sm text-gray-700">{meta.subtitle}</p>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-xl border border-gray-200 bg-white px-3 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">Escenario</p>
            <p className="mt-1 truncate text-sm font-semibold text-gray-900">{scenarioLabel}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white px-3 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">Importe</p>
            <p className={`mt-1 text-sm font-semibold ${meta.accentText}`}>{formatAmount(amount)}</p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white px-3 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">
              {duration ? 'Tiempo IA' : 'Risk score'}
            </p>
            <p className="mt-1 text-sm font-semibold text-gray-900">
              {duration ?? (typeof riskScore === 'number' ? `${riskScore}/100` : '—')}
            </p>
          </div>
        </div>

        {reasoning && (
          <div className="flex-1 overflow-hidden rounded-xl border border-gray-200 bg-white px-4 py-3">
            <div className="mb-2 flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-primary-600" />
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">Razonamiento del orquestador</p>
            </div>
            <p className="line-clamp-6 text-sm leading-6 text-gray-800">{reasoning}</p>
          </div>
        )}

        <div className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${meta.badgeClass}`}>
          <CheckCircle2 className="h-3 w-3" />
          Audit trail completo
        </div>
      </div>
    </div>
  );
}
