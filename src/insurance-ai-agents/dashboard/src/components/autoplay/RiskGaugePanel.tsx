import { ShieldAlert, ShieldCheck, AlertOctagon, Loader2 } from 'lucide-react';
import { useEffect, useId, useState } from 'react';
import { BRAND } from '../../brand';

export type FraudProbability = 'low' | 'medium' | 'high';

export interface RiskGaugePanelProps {
  active: boolean;
  targetScore: number | null;
  fraudProbability: FraudProbability | null;
  phaseLabel?: string;
}

const GAUGE_RADIUS = 96;
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * GAUGE_RADIUS;
const GAUGE_HALF = Math.PI * GAUGE_RADIUS;
const GAUGE_SEGMENTS = [
  { length: GAUGE_HALF * 0.33, color: '#10b981', label: 'Bajo' },
  { length: GAUGE_HALF * 0.33, color: '#f59e0b', label: 'Medio' },
  { length: GAUGE_HALF * 0.34, color: '#ef4444', label: 'Alto' },
] as const;

const FRAUD_META: Record<FraudProbability, {
  scale: number;
  pct: number;
  label: string;
  color: string;
  pill: string;
  glow: string;
  Icon: typeof ShieldCheck;
}> = {
  low: {
    scale: 0.2,
    pct: 12,
    label: 'BAJA',
    color: '#10b981',
    pill: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    glow: 'shadow-emerald-200/60',
    Icon: ShieldCheck,
  },
  medium: {
    scale: 0.55,
    pct: 48,
    label: 'MEDIA',
    color: '#f59e0b',
    pill: 'border-amber-200 bg-amber-50 text-amber-800',
    glow: 'shadow-amber-200/60',
    Icon: ShieldAlert,
  },
  high: {
    scale: 0.9,
    pct: 86,
    label: 'ALTA',
    color: '#ef4444',
    pill: 'border-red-200 bg-red-50 text-red-700',
    glow: 'shadow-red-200/60',
    Icon: AlertOctagon,
  },
};

const RISK_WARMING_MESSAGES = [
  'Calculando risk score…',
  'Analizando histórico del cliente…',
  'Cruzando patrones de fraude…',
] as const;

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

// Ángulo de la aguja en grados de rotación SVG (positivo = horario).
// Línea base apunta a la derecha (3 o'clock). Queremos:
//   score=0   → punta a la izquierda → rotación -180° (o 180°)
//   score=50  → punta arriba        → rotación -90°
//   score=100 → punta a la derecha  → rotación 0°
function getNeedleRotation(score: number | null, active: boolean) {
  if (!active || score === null) return -90; // reposo: centro arriba
  const clamped = Math.max(0, Math.min(100, score));
  return -180 + clamped * 1.8;
}

function getScoreTone(score: number | null, active: boolean) {
  if (!active || score === null) return 'text-gray-500';
  if (score <= 33) return 'text-emerald-700';
  if (score <= 66) return 'text-amber-700';
  return 'text-red-700';
}

function getScoreBand(score: number | null) {
  if (score === null) return null;
  if (score <= 33) return 'Bajo';
  if (score <= 66) return 'Medio';
  return 'Alto';
}

export default function RiskGaugePanel({
  active,
  targetScore,
  fraudProbability,
  phaseLabel,
}: RiskGaugePanelProps) {
  const clipPathId = useId().replace(/:/g, '');
  const [warmingMessageIndex, setWarmingMessageIndex] = useState(0);
  const score = typeof targetScore === 'number' ? Math.max(0, Math.min(100, targetScore)) : null;
  const displayScore = active ? score : null;
  const needleRotation = getNeedleRotation(displayScore, active);
  const scoreTone = getScoreTone(displayScore, active);
  const scoreBand = getScoreBand(displayScore);
  const scoreLabel = displayScore === null ? '—' : Math.round(displayScore).toString();
  const riskPending = active && displayScore === null;
  const fraudPending = active && fraudProbability === null;
  const warmingUp = active && targetScore === null && fraudProbability === null;
  const fraudMeta = active && fraudProbability ? FRAUD_META[fraudProbability] : null;
  const fillScale = fraudMeta?.scale ?? (fraudPending ? 0.14 : 0);
  const fillColor = fraudMeta?.color ?? (warmingUp ? BRAND.primaryHex : fraudPending ? BRAND.primaryHex : '#94a3b8');
  const pillLabel = fraudMeta?.label ?? (fraudPending ? 'CALCULANDO' : '—');
  const pillTone = fraudMeta?.pill ?? (fraudPending
    ? `border-primary-200 bg-primary-50 text-primary-700${warmingUp ? '' : ' animate-pulse'}`
    : 'border-gray-200 bg-gray-50 text-gray-500');
  const FraudIcon = fraudMeta?.Icon ?? ShieldAlert;
  const fraudPct = fraudMeta?.pct ?? null;

  useEffect(() => {
    if (!warmingUp) {
      setWarmingMessageIndex(0);
      return;
    }
    const interval = window.setInterval(() => {
      setWarmingMessageIndex((current) => (current + 1) % RISK_WARMING_MESSAGES.length);
    }, 1400);
    return () => window.clearInterval(interval);
  }, [warmingUp]);

  // Termómetro: tube y=24..188 (h=164), bulbo cy=212 r=26 (y=186..238).
  // Rango llenable y=24..238 = 214px. fillScale=1 → topY=24, =0 → topY=238.
  const TH_TOP = 24;
  const TH_BOTTOM = 238;
  const TH_RANGE = TH_BOTTOM - TH_TOP;
  const fillTopY = TH_BOTTOM - fillScale * TH_RANGE;

  return (
    <section className="rounded-[28px] border border-gray-200 bg-white p-6 shadow-xl shadow-gray-200/60">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-primary-200 bg-primary-50 text-primary-700">
          <ShieldAlert className="h-5 w-5" />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-gray-500">Risk agent</p>
          <h3 className="text-lg font-semibold text-gray-900">Scoring y fraude</h3>
          {phaseLabel ? <p className="mt-1 text-xs text-gray-500">{phaseLabel}</p> : null}
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        {/* --- RISK SCORE CARD ----------------------------------------------- */}
        <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-gradient-to-br from-white via-gray-50/70 to-primary-50/30 p-5">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-gray-500">Risk score</p>
            {scoreBand ? (
              <span className={cx(
                'rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em]',
                scoreBand === 'Bajo' && 'border-emerald-200 bg-emerald-50 text-emerald-700',
                scoreBand === 'Medio' && 'border-amber-200 bg-amber-50 text-amber-800',
                scoreBand === 'Alto' && 'border-red-200 bg-red-50 text-red-700',
              )}>
                {scoreBand}
              </span>
            ) : null}
            {warmingUp ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-primary-200 bg-primary-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-primary-700">
                <Loader2 className="h-3 w-3 animate-spin" />
                Calculando
              </span>
            ) : null}
          </div>

          <div className="relative">
            <svg viewBox="0 0 300 180" className="mx-auto h-[180px] w-full max-w-[300px] overflow-visible">
              {/* Track gris de fondo: butt caps (flat) para empalme limpio */}
              <circle
                cx="150"
                cy="150"
                r={GAUGE_RADIUS}
                fill="none"
                stroke="#e5e7eb"
                strokeWidth="20"
                strokeLinecap="butt"
                strokeDasharray={`${GAUGE_HALF} ${GAUGE_CIRCUMFERENCE}`}
                transform="rotate(180 150 150)"
              />
              {/* Segmentos de color: butt caps + pequeño gap visual */}
              {GAUGE_SEGMENTS.map((segment, index) => {
                const SEGMENT_GAP = 2.5;
                const isFirst = index === 0;
                const isLast = index === GAUGE_SEGMENTS.length - 1;
                const startTrim = isFirst ? 0 : SEGMENT_GAP / 2;
                const endTrim = isLast ? 0 : SEGMENT_GAP / 2;
                const dashLength = Math.max(0, segment.length - startTrim - endTrim);
                const offsetCumulative = -GAUGE_SEGMENTS.slice(0, index).reduce((total, item) => total + item.length, 0);
                const offset = offsetCumulative - startTrim;
                return (
                  <circle
                    key={`zone-${segment.color}`}
                    cx="150"
                    cy="150"
                    r={GAUGE_RADIUS}
                    fill="none"
                    stroke={active ? segment.color : '#cbd5e1'}
                    strokeWidth="20"
                    strokeLinecap="butt"
                    strokeDasharray={`${dashLength} ${GAUGE_CIRCUMFERENCE}`}
                    strokeDashoffset={offset}
                    transform="rotate(180 150 150)"
                    opacity={warmingUp ? 0.28 : 1}
                    style={{ transition: 'opacity 0.4s ease-out' }}
                  />
                );
              })}
              {/* Pequeños capuchones redondeados sólo en los extremos exteriores */}
              <circle
                cx="150" cy="150" r={GAUGE_RADIUS}
                fill="none"
                stroke={active ? GAUGE_SEGMENTS[0].color : '#cbd5e1'}
                strokeWidth="20" strokeLinecap="round"
                strokeDasharray={`0.5 ${GAUGE_CIRCUMFERENCE}`}
                transform="rotate(180 150 150)"
                opacity={warmingUp ? 0.28 : 1}
                style={{ transition: 'opacity 0.4s ease-out' }}
              />
              <circle
                cx="150" cy="150" r={GAUGE_RADIUS}
                fill="none"
                stroke={active ? GAUGE_SEGMENTS[GAUGE_SEGMENTS.length - 1].color : '#cbd5e1'}
                strokeWidth="20" strokeLinecap="round"
                strokeDasharray={`0.5 ${GAUGE_CIRCUMFERENCE}`}
                strokeDashoffset={-GAUGE_HALF + 0.5}
                transform="rotate(180 150 150)"
                opacity={warmingUp ? 0.28 : 1}
                style={{ transition: 'opacity 0.4s ease-out' }}
              />

              {/* Marcas y etiquetas numéricas */}
              <text x="40" y="170" fill="#6b7280" fontSize="11" fontWeight="600" opacity={warmingUp ? 0.4 : 1}>0</text>
              <text x="144" y="40" fill="#6b7280" fontSize="11" fontWeight="600" opacity={warmingUp ? 0.4 : 1}>50</text>
              <text x="245" y="170" fill="#6b7280" fontSize="11" fontWeight="600" opacity={warmingUp ? 0.4 : 1}>100</text>
              <text x="78" y="86" fill="#94a3b8" fontSize="9" fontWeight="600" opacity={warmingUp ? 0.4 : 1}>25</text>
              <text x="208" y="86" fill="#94a3b8" fontSize="9" fontWeight="600" opacity={warmingUp ? 0.4 : 1}>75</text>

              {/* Aguja: sólo si no estamos cargando */}
              {!warmingUp ? (
                <g
                  transform={`rotate(${needleRotation} 150 150)`}
                  style={{ transition: 'transform 1.4s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
                >
                  <line
                    x1="150" y1="150" x2="234" y2="150"
                    stroke="rgba(15, 23, 42, 0.12)"
                    strokeWidth="7" strokeLinecap="round"
                    transform="translate(0, 2)"
                  />
                  <line
                    x1="150" y1="150" x2="234" y2="150"
                    stroke={active ? BRAND.primaryHex : '#94a3b8'}
                    strokeWidth="5" strokeLinecap="round"
                  />
                  <circle cx="234" cy="150" r="3" fill={active ? BRAND.primaryHex : '#94a3b8'} />
                </g>
              ) : null}
              {/* Pivot */}
              <circle cx="150" cy="150" r="13" fill="#ffffff" stroke="#e5e7eb" strokeWidth="2" />
              {!warmingUp ? (
                <circle cx="150" cy="150" r="6" fill={active ? BRAND.primaryHex : '#94a3b8'} />
              ) : null}
            </svg>

            {/* Spinner overlay centrado en el hueco superior del semicírculo */}
            {warmingUp ? (
              <div className="pointer-events-none absolute inset-x-0 top-[46%] -translate-y-1/2 flex justify-center">
                <Loader2 className="h-7 w-7 animate-spin text-primary-500/80" />
              </div>
            ) : null}
          </div>

          <div className="mt-2 min-h-[64px] text-center">
            {warmingUp ? (
              <div className="flex flex-col items-center justify-center gap-0.5 py-3">
                <p key={warmingMessageIndex} className="animate-fade-in text-sm font-medium text-gray-500">
                  {RISK_WARMING_MESSAGES[warmingMessageIndex]}
                </p>
                <p className="text-[10px] uppercase tracking-[0.22em] text-gray-300">— / 100</p>
              </div>
            ) : (
              <p className={cx('text-5xl font-semibold tracking-tight tabular-nums', scoreTone)}>
                {scoreLabel}
                <span className="ml-1.5 text-lg font-medium text-gray-400">/ 100</span>
              </p>
            )}
          </div>
        </div>

        {/* --- FRAUD SIGNAL CARD --------------------------------------------- */}
        <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-gradient-to-br from-white via-gray-50/70 to-primary-50/30 p-5">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-gray-500">Fraud signal</p>
            {warmingUp ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-primary-200 bg-primary-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-primary-700">
                <Loader2 className="h-3 w-3 animate-spin" />
                Calculando
              </span>
            ) : (
              <div className={cx(
                'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.2em] shadow-sm',
                pillTone,
                fraudMeta?.glow,
              )}>
                <FraudIcon className="h-3 w-3" />
                {pillLabel}
              </div>
            )}
          </div>

          <div className="flex items-center gap-4">
            {/* Termómetro */}
            <div className="relative">
              <svg viewBox="0 0 100 260" className="h-[210px] w-[78px] overflow-visible">
                <defs>
                  <clipPath id={clipPathId}>
                    <rect x="34" y={TH_TOP} width="32" height="166" rx="16" />
                    <circle cx="50" cy="212" r="26" />
                  </clipPath>
                  <linearGradient id={`${clipPathId}-shine`} x1="0" x2="1" y1="0" y2="0">
                    <stop offset="0" stopColor="rgba(255,255,255,0.45)" />
                    <stop offset="0.4" stopColor="rgba(255,255,255,0)" />
                  </linearGradient>
                </defs>

                {/* Fondo gris claro dentro de la silueta */}
                <g clipPath={`url(#${clipPathId})`}>
                  <rect x="0" y="0" width="100" height="260" fill="#f3f4f6" />
                </g>

                {warmingUp ? (
                  <g clipPath={`url(#${clipPathId})`}>
                    {/* Pequeño "charco" rojo pulsante en la base del bulbo */}
                    <circle cx="50" cy="220" r="14" fill={BRAND.primaryHex} opacity="0.18">
                      <animate
                        attributeName="opacity"
                        values="0.12;0.32;0.12"
                        dur="1.8s"
                        repeatCount="indefinite"
                      />
                      <animate
                        attributeName="r"
                        values="12;15;12"
                        dur="1.8s"
                        repeatCount="indefinite"
                      />
                    </circle>
                    {/* Burbujas orgánicas con tamaño, ritmo y oscilación variados */}
                    {[
                      { delay: '0s',   dur: '2.4s', x: 50, r: 4.5, drift: 4 },
                      { delay: '0.5s', dur: '2.8s', x: 46, r: 3.2, drift: -3 },
                      { delay: '1.1s', dur: '2.2s', x: 53, r: 5,   drift: 3 },
                      { delay: '1.6s', dur: '2.6s', x: 48, r: 3.8, drift: -2 },
                      { delay: '2.0s', dur: '2.5s', x: 52, r: 3,   drift: 2.5 },
                    ].map((b, i) => (
                      <circle key={i} cx={b.x} cy={210} r={b.r} fill={BRAND.primaryHex} opacity="0">
                        <animate
                          attributeName="cy"
                          values="216;28"
                          dur={b.dur}
                          begin={b.delay}
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="cx"
                          values={`${b.x};${b.x + b.drift};${b.x - b.drift * 0.6};${b.x + b.drift * 0.4};${b.x}`}
                          keyTimes="0;0.3;0.55;0.8;1"
                          dur={b.dur}
                          begin={b.delay}
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="opacity"
                          values="0;0.85;0.85;0"
                          keyTimes="0;0.12;0.82;1"
                          dur={b.dur}
                          begin={b.delay}
                          repeatCount="indefinite"
                        />
                        <animate
                          attributeName="r"
                          values={`${b.r * 0.6};${b.r};${b.r * 0.8}`}
                          keyTimes="0;0.4;1"
                          dur={b.dur}
                          begin={b.delay}
                          repeatCount="indefinite"
                        />
                      </circle>
                    ))}
                  </g>
                ) : (
                  <g clipPath={`url(#${clipPathId})`}>
                    <rect
                      x="0"
                      y={fillTopY}
                      width="100"
                      height={Math.max(0, TH_BOTTOM - fillTopY) + 4}
                      fill={fillColor}
                      className={fraudPending ? 'animate-pulse' : undefined}
                      style={{ transition: 'y 0.9s ease-out, height 0.9s ease-out, fill 0.6s' }}
                    />
                    {/* Brillo lateral sutil */}
                    <rect x="34" y={TH_TOP} width="14" height="200" fill={`url(#${clipPathId}-shine)`} />
                  </g>
                )}

                {/* Contorno por encima */}
                <rect x="34" y={TH_TOP} width="32" height="166" rx="16" fill="none" stroke="#cbd5e1" strokeWidth="2.5" />
                <circle cx="50" cy="212" r="26" fill="none" stroke="#cbd5e1" strokeWidth="2.5" />

                {/* Marcas */}
                {[0.25, 0.5, 0.75].map((t) => {
                  const y = TH_BOTTOM - t * TH_RANGE;
                  return (
                    <line key={t} x1="66" x2="74" y1={y} y2={y} stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round" opacity={warmingUp ? 0.5 : 1} />
                  );
                })}
                <text x="78" y={TH_BOTTOM - 0.25 * TH_RANGE + 4} fill="#94a3b8" fontSize="9" fontWeight="600" opacity={warmingUp ? 0.5 : 1}>25%</text>
                <text x="78" y={TH_BOTTOM - 0.5 * TH_RANGE + 4} fill="#94a3b8" fontSize="9" fontWeight="600" opacity={warmingUp ? 0.5 : 1}>50%</text>
                <text x="78" y={TH_BOTTOM - 0.75 * TH_RANGE + 4} fill="#94a3b8" fontSize="9" fontWeight="600" opacity={warmingUp ? 0.5 : 1}>75%</text>
              </svg>
            </div>

            {/* Valor numérico y descripción al lado */}
            <div className="flex-1 space-y-3">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gray-500">Probabilidad</p>
                {warmingUp ? (
                  <p className="mt-1 text-4xl font-semibold tracking-tight tabular-nums text-gray-300 animate-pulse">
                    —
                    <span className="ml-0.5 text-xl font-medium text-gray-300">%</span>
                  </p>
                ) : (
                  <p
                    className="mt-1 text-5xl font-semibold tracking-tight tabular-nums transition-colors"
                    style={{ color: fraudMeta ? fillColor : '#9ca3af' }}
                  >
                    {fraudPct !== null ? fraudPct : (fraudPending ? '··' : '—')}
                    <span className="ml-0.5 text-xl font-medium text-gray-400">%</span>
                  </p>
                )}
              </div>
              <div className="rounded-xl border border-gray-200 bg-white/80 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gray-500">Veredicto del modelo</p>
                {warmingUp ? (
                  <p className="mt-1 inline-flex items-center gap-2 text-sm font-medium text-gray-400">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Analizando indicios…
                  </p>
                ) : (
                  <p className="mt-1 text-sm font-semibold" style={{ color: fraudMeta ? fillColor : '#6b7280' }}>
                    {fraudMeta
                      ? fraudProbability === 'low'
                        ? 'Sin indicios de fraude'
                        : fraudProbability === 'medium'
                          ? 'Algunos indicadores sospechosos'
                          : 'Múltiples señales de fraude'
                      : fraudPending ? 'Analizando indicios…' : 'Sin datos'}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
