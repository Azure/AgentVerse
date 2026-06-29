import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ElementType, ReactNode } from 'react';
import {
  BarChart3,
  Bot,
  ChevronDown,
  Clock3,
  DollarSign,
  FileStack,
  Gauge,
  Info,
  RefreshCw,
  ShieldAlert,
  Zap,
} from 'lucide-react';
import type { ClaimSummary, SecurityIncident, StatsResponse } from '../api';
import { getClaims, getSecurityIncidents, getStats } from '../api';

const MANUAL_BASELINE_MINUTES = 45;
const ANALYST_COST_PER_HOUR = 35;
const DECISION_KEYS = ['approve', 'human_review', 'reject'] as const;

type DecisionKey = (typeof DECISION_KEYS)[number];

const DECISION_META: Record<DecisionKey, { label: string; color: string }> = {
  approve: { label: 'Aprobadas', color: '#10B981' },
  human_review: { label: 'Revisión humana', color: '#F59E0B' },
  reject: { label: 'Rechazadas', color: '#DC2626' },
};

interface DailyDecisionPoint {
  key: string;
  label: string;
  fullLabel: string;
  amount: number;
  total: number;
  counts: Record<DecisionKey, number>;
}

interface BusinessMetricCardProps {
  icon: ElementType;
  label: string;
  value: ReactNode;
  sub: string;
  tooltip: string;
  valueClass: string;
}

interface TechnicalMetricCardProps {
  icon: ElementType;
  label: string;
  value: string;
  sub?: string;
}

function emptyDecisionCounts(): Record<DecisionKey, number> {
  return { approve: 0, human_review: 0, reject: 0 };
}

function formatNumber(value: number, maximumFractionDigits = 1): string {
  const rounded = Number(value.toFixed(maximumFractionDigits));
  const hasDecimals = !Number.isInteger(rounded);

  return rounded.toLocaleString('es-ES', {
    minimumFractionDigits: hasDecimals ? Math.min(1, maximumFractionDigits) : 0,
    maximumFractionDigits,
  });
}

function formatCurrency(value: number): string {
  const prefix = value < 0 ? '-€' : '€';
  return `${prefix}${Math.abs(value).toLocaleString('es-ES', { maximumFractionDigits: 0 })}`;
}

function formatDuration(durationMs: number): string {
  const seconds = durationMs / 1000;
  if (seconds < 60) {
    return `${formatNumber(seconds, seconds < 10 ? 1 : 0)} s`;
  }

  return `${formatNumber(durationMs / 60_000, 1)} min`;
}

function getLocalDayKey(date: Date): string {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function normalizeDecision(decision: string): DecisionKey | null {
  const normalized = decision === 'approved'
    ? 'approve'
    : decision === 'rejected'
      ? 'reject'
      : decision;

  return DECISION_KEYS.includes(normalized as DecisionKey) ? (normalized as DecisionKey) : null;
}

function buildDailyDecisionPoints(claims: ClaimSummary[]): DailyDecisionPoint[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const points: DailyDecisionPoint[] = [];

  for (let offset = 6; offset >= 0; offset -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - offset);

    points.push({
      key: getLocalDayKey(date),
      label: date.toLocaleDateString('es-ES', { weekday: 'short' }).replace('.', ''),
      fullLabel: capitalize(date.toLocaleDateString('es-ES', { weekday: 'long' })),
      amount: 0,
      total: 0,
      counts: emptyDecisionCounts(),
    });
  }

  const lookup = new Map(points.map((point) => [point.key, point]));

  claims.forEach((claim) => {
    const date = new Date(claim.timestamp);
    if (Number.isNaN(date.getTime())) return;

    const point = lookup.get(getLocalDayKey(date));
    const decision = normalizeDecision(claim.decision);

    if (!point || !decision) return;

    point.counts[decision] += 1;
    point.total += 1;
    point.amount += claim.estimated_amount ?? 0;
  });

  return points;
}

function InfoTooltip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        title={text}
        aria-label={text}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 transition-colors hover:border-primary-300 hover:text-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500/30"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-2 w-64 -translate-x-1/2 rounded-lg border border-gray-800 bg-gray-900 px-3 py-2 text-[11px] leading-relaxed text-white opacity-0 shadow-md transition duration-150 group-hover:opacity-100 group-focus-within:opacity-100">
        {text}
      </span>
    </span>
  );
}

function BusinessMetricCard({
  icon: Icon,
  label,
  value,
  sub,
  tooltip,
  valueClass,
}: BusinessMetricCardProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <Icon className="pointer-events-none absolute right-4 top-4 h-16 w-16 text-primary-200" />
      <div className="relative">
        <div className="mb-3 flex items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-[0.24em] text-gray-500">
            {label}
          </span>
          <InfoTooltip text={tooltip} />
        </div>
        <div className={`text-4xl font-bold leading-tight ${valueClass}`}>
          {value}
        </div>
        <p className="mt-3 max-w-[18rem] text-sm text-gray-600">{sub}</p>
      </div>
    </div>
  );
}

function TechnicalMetricCard({ icon: Icon, label, value, sub }: TechnicalMetricCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <div className="rounded-md bg-primary-50 p-2 text-primary-600">
          <Icon className="h-4 w-4" />
        </div>
        <span className="text-xs uppercase tracking-[0.2em] text-gray-500">{label}</span>
      </div>
      <div className="text-2xl font-semibold text-gray-900">{value}</div>
      {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
    </div>
  );
}

function DecisionDistribution({ counts }: { counts: Record<DecisionKey, number> }) {
  const total = DECISION_KEYS.reduce((sum, key) => sum + counts[key], 0);
  const radius = 44;
  const circumference = 2 * Math.PI * radius;

  let accumulatedLength = 0;
  const segments = DECISION_KEYS.map((key) => {
    const value = counts[key];
    const length = total === 0 ? 0 : (value / total) * circumference;
    const segment = {
      key,
      value,
      percentage: total === 0 ? 0 : (value / total) * 100,
      dashArray: `${length} ${circumference - length}`,
      dashOffset: -accumulatedLength,
    };
    accumulatedLength += length;
    return segment;
  });

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-6">
        <h3 className="text-sm font-semibold text-gray-900">Distribución de decisiones</h3>
        <p className="text-xs text-gray-500">
          Qué parte del volumen se resuelve al instante y qué parte requiere revisión.
        </p>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
        <div className="relative mx-auto h-40 w-40 shrink-0">
          <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
            <circle cx="60" cy="60" r={radius} fill="none" stroke="#E5E7EB" strokeWidth="12" />
            {segments.map((segment) => (
              segment.value > 0 ? (
                <circle
                  key={segment.key}
                  cx="60"
                  cy="60"
                  r={radius}
                  fill="none"
                  stroke={DECISION_META[segment.key].color}
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={segment.dashArray}
                  strokeDashoffset={segment.dashOffset}
                >
                  <title>{`${DECISION_META[segment.key].label}: ${formatNumber(segment.percentage, 1)}% (${formatNumber(segment.value, 0)} casos)`}</title>
                </circle>
              ) : null
            ))}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-semibold text-gray-900">{formatNumber(total, 0)}</span>
            <span className="text-[11px] uppercase tracking-[0.2em] text-gray-500">Casos</span>
          </div>
        </div>

        <div className="flex-1 space-y-4">
          {DECISION_KEYS.map((key) => {
            const value = counts[key];
            const percentage = total === 0 ? 0 : (value / total) * 100;

            return (
              <div key={key} className="space-y-2">
                <div className="flex items-center gap-3 text-sm">
                  <span className="inline-flex h-2.5 w-2.5 rounded-full" style={{ backgroundColor: DECISION_META[key].color }} />
                  <span className="font-medium text-gray-700">{DECISION_META[key].label}</span>
                  <span className="ml-auto text-gray-500">{formatNumber(percentage, 1)}%</span>
                  <span className="text-gray-500">{formatNumber(value, 0)}</span>
                </div>
                <svg viewBox="0 0 100 8" preserveAspectRatio="none" className="h-2 w-full overflow-visible rounded-full">
                  <rect x="0" y="0" width="100" height="8" rx="4" fill="#E5E7EB" />
                  <rect x="0" y="0" width={percentage} height="8" rx="4" fill={DECISION_META[key].color}>
                    <title>{`${DECISION_META[key].label}: ${formatNumber(value, 0)} casos`}</title>
                  </rect>
                </svg>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DecisionsByDayChart({ days }: { days: DailyDecisionPoint[] }) {
  const maxTotal = Math.max(1, ...days.map((day) => day.total));
  const chartWidth = 640;
  const chartHeight = 280;
  const padding = { top: 20, right: 16, bottom: 40, left: 16 };
  const plotHeight = chartHeight - padding.top - padding.bottom;
  const plotWidth = chartWidth - padding.left - padding.right;
  const groupWidth = plotWidth / days.length;
  const barWidth = Math.min(48, groupWidth * 0.56);
  const sevenDayAmount = days.reduce((sum, day) => sum + day.amount, 0);

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Decisiones por día (últimos 7 días)</h3>
          <p className="text-xs text-gray-500">
            Evolución diaria del volumen procesado con desglose approve / revisión / reject.
          </p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500">Importe 7 días</div>
          <div className="text-sm font-semibold text-gray-900">{formatCurrency(sevenDayAmount)}</div>
        </div>
      </div>

      <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="h-72 w-full">
        {[0.25, 0.5, 0.75, 1].map((level) => {
          const y = padding.top + plotHeight - (plotHeight * level);
          return (
            <g key={level}>
              <line x1={padding.left} y1={y} x2={padding.left + plotWidth} y2={y} stroke="#E5E7EB" strokeDasharray="4 4" />
              <text x={padding.left + plotWidth} y={y - 6} textAnchor="end" className="fill-gray-500 text-[10px]">
                {formatNumber(maxTotal * level, 0)}
              </text>
            </g>
          );
        })}

        {days.map((day, index) => {
          const x = padding.left + (index * groupWidth) + ((groupWidth - barWidth) / 2);
          let accumulatedHeight = 0;
          const tooltip = `${day.fullLabel} · ${formatNumber(day.total, 0)} decisiones (${formatCurrency(day.amount)} procesados)`;

          return (
            <g key={day.key}>
              <rect
                x={x - 6}
                y={padding.top}
                width={barWidth + 12}
                height={plotHeight}
                fill="transparent"
              >
                <title>{tooltip}</title>
              </rect>

              <rect
                x={x}
                y={padding.top}
                width={barWidth}
                height={plotHeight}
                rx={barWidth / 2}
                fill="#F3F4F6"
              />

              {DECISION_KEYS.map((key) => {
                const value = day.counts[key];
                const height = (value / maxTotal) * plotHeight;
                const y = padding.top + plotHeight - accumulatedHeight - height;
                accumulatedHeight += height;

                if (height <= 0) {
                  return null;
                }

                return (
                  <rect
                    key={key}
                    x={x}
                    y={y}
                    width={barWidth}
                    height={height}
                    fill={DECISION_META[key].color}
                  />
                );
              })}

              {day.total > 0 && (
                <text
                  x={x + (barWidth / 2)}
                  y={padding.top + plotHeight - accumulatedHeight - 8}
                  textAnchor="middle"
                  className="fill-gray-500 text-[10px]"
                >
                  {day.total}
                </text>
              )}

              <text
                x={x + (barWidth / 2)}
                y={chartHeight - 10}
                textAnchor="middle"
                className="fill-gray-500 text-[11px]"
              >
                {day.label}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-600">
        {DECISION_KEYS.map((key) => (
          <div key={key} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: DECISION_META[key].color }} />
            <span>{DECISION_META[key].label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function StatsView() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [claims, setClaims] = useState<ClaimSummary[]>([]);
  const [securityIncidents, setSecurityIncidents] = useState<SecurityIncident[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);

    const [statsResult, claimsResult, incidentsResult] = await Promise.allSettled([
      getStats(),
      getClaims(),
      getSecurityIncidents(),
    ]);

    if (statsResult.status === 'fulfilled') {
      setStats(statsResult.value);
      setLoadError(null);
    } else if (!stats) {
      setLoadError('No se pudieron cargar las estadísticas.');
    }

    if (claimsResult.status === 'fulfilled') {
      setClaims(claimsResult.value);
    }

    if (incidentsResult.status === 'fulfilled') {
      setSecurityIncidents(incidentsResult.value.incidents);
    }

    setLoading(false);
  }, [stats]);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => {
      void refresh();
    }, 10_000);

    return () => window.clearInterval(interval);
  }, [refresh]);

  const dailyDecisionPoints = useMemo(() => buildDailyDecisionPoints(claims), [claims]);

  if (!stats) {
    return (
      <div className="rounded-xl border border-gray-200 bg-gray-50 p-6 text-center text-sm text-gray-600">
        {loadError ?? 'Cargando estadísticas…'}
      </div>
    );
  }

  const decisionCounts: Record<DecisionKey, number> = {
    approve: stats.approved,
    human_review: stats.human_review,
    reject: stats.rejected,
  };

  const aiDurationLabel = formatDuration(stats.avg_duration_ms);
  const timeSavedPerCaseMinutes = MANUAL_BASELINE_MINUTES - (stats.avg_duration_ms / 60_000);
  const savedHours = stats.total_claims === 0 ? null : (stats.total_claims * timeSavedPerCaseMinutes) / 60;
  const estimatedSavings = savedHours === null ? null : savedHours * ANALYST_COST_PER_HOUR;
  const automationRate = stats.total_claims === 0
    ? null
    : ((stats.approved + stats.rejected) / stats.total_claims) * 100;
  const fraudsPrevented = stats.rejected + securityIncidents.length;
  const speedMultiplier = stats.avg_duration_ms > 0
    ? (MANUAL_BASELINE_MINUTES * 60_000) / stats.avg_duration_ms
    : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Estadísticas</h2>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          className="flex items-center gap-1.5 text-xs text-gray-600 transition-colors hover:text-primary-600"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualizar
        </button>
      </div>

      <div className="grid gap-3 rounded-2xl border border-primary-200 bg-primary-50 p-4 md:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500">Antes</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">45 min/caso</div>
          <p className="text-xs text-gray-500">Procesamiento manual</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500">Ahora</div>
          <div className="mt-1 text-lg font-semibold text-gray-900">{aiDurationLabel}</div>
          <p className="text-xs text-gray-500">Pipeline AI actual</p>
        </div>
        <div className="rounded-xl border border-primary-200 bg-white p-4">
          <div className="text-[10px] uppercase tracking-[0.2em] text-primary-900/70">Impacto</div>
          <div className="mt-1 text-3xl font-bold text-primary-600">
            {speedMultiplier === null ? '—' : `${formatNumber(speedMultiplier, speedMultiplier < 10 ? 1 : 0)}× más rápido`}
          </div>
          <p className="text-xs text-primary-900/70">Comparativa calculada en runtime</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <BusinessMetricCard
          icon={DollarSign}
          label="Ahorro estimado"
          value={estimatedSavings === null ? '—' : formatCurrency(estimatedSavings)}
          sub={savedHours === null ? 'Sin casos todavía para estimar el ahorro.' : `≈ ${formatNumber(savedHours, 1)} h liberadas al equipo este mes`}
          tooltip="Calculado como (45 min - tiempo real) × casos × 35€/hora (coste medio analista)."
          valueClass="text-primary-600"
        />
        <BusinessMetricCard
          icon={Zap}
          label="Tiempo reducido"
          value={`${formatNumber(timeSavedPerCaseMinutes, 1)} min menos por caso`}
          sub={`De 45 min/caso a ${aiDurationLabel} con IA gobernada`}
          tooltip="Baseline: 45 min/caso manual. Actual: tiempo medio del pipeline."
          valueClass="text-gray-900"
        />
        <BusinessMetricCard
          icon={Bot}
          label="Automatización"
          value={automationRate === null ? '—' : `${formatNumber(automationRate, 1)}%`}
          sub="Casos resueltos sin intervención humana"
          tooltip="Casos approve + reject (sin revisión humana) / total de casos."
          valueClass="text-gray-900"
        />
        <BusinessMetricCard
          icon={ShieldAlert}
          label="Fraudes evitados"
          value={formatNumber(fraudsPrevented, 0)}
          sub="Rechazos por riesgo + intentos de manipulación detectados"
          tooltip="Casos rejected por riesgo alto + incidentes de seguridad (prompt injection, manipulación)."
          valueClass="text-primary-600"
        />
      </div>

      <DecisionDistribution counts={decisionCounts} />

      <DecisionsByDayChart days={dailyDecisionPoints} />

      <details className="rounded-xl border border-gray-200 bg-gray-50 p-4 shadow-sm">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 [&::-webkit-details-marker]:hidden">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Métricas técnicas</h3>
            <p className="text-xs text-gray-500">
              Cerradas por defecto para que la conversación principal siga enfocada en negocio.
            </p>
          </div>
          <span className="flex items-center gap-2 text-xs text-gray-500">
            Mostrar detalle
            <ChevronDown className="h-4 w-4" />
          </span>
        </summary>

        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <TechnicalMetricCard
            icon={Clock3}
            label="avg_duration_ms"
            value={`${stats.avg_duration_ms.toLocaleString('es-ES')} ms`}
            sub="Tiempo medio end-to-end del pipeline."
          />
          <TechnicalMetricCard
            icon={Gauge}
            label="avg_risk_score"
            value={stats.avg_risk_score.toFixed(2)}
            sub="Score técnico medio devuelto por el motor de riesgo."
          />
          <TechnicalMetricCard
            icon={FileStack}
            label="active_policies"
            value={stats.active_policies.toLocaleString('es-ES')}
            sub="Pólizas activas disponibles en el entorno de demo."
          />
        </div>
      </details>
    </div>
  );
}
