import { useCallback, useEffect, useMemo, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Clock,
  Database,
  Euro,
  FileSearch,
  Gavel,
  LayoutGrid,
  Play,
  Scale,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Siren,
  Sparkles,
  Timer,
  Upload,
  UserCheck,
  Zap,
  XCircle,
} from 'lucide-react';
import type { ClaimSummary, SecurityIncident, StatsResponse } from '../api';
import { getClaims, getSecurityIncidents, getStats } from '../api';
import { BRAND } from '../brand';

interface HeroViewProps {
  onCTAClick: () => void;
}

interface HeroMetric {
  icon: LucideIcon;
  label: string;
  display: string;
  description: string;
  valueClass: string;
  countTarget?: number;
  countFormatter?: (value: number) => string;
}

interface DemoUseCase {
  key: string;
  icon: LucideIcon;
  title: string;
  amount: number;
  expected: string;
  description: string;
  accent: string;
}

interface PlatformBadge {
  icon: LucideIcon;
  name: string;
  description: string;
  featured?: boolean;
}

const HERO_BADGES: Array<{ icon: LucideIcon; label: string }> = [
  { icon: Sparkles, label: 'Powered by Microsoft Agent Framework' },
  { icon: Sparkles, label: 'Azure OpenAI' },
  { icon: Shield, label: 'Entra ID' },
  { icon: Database, label: 'Cosmos DB' },
  { icon: Activity, label: 'APIM' },
];

const FLOW_STEPS: Array<{ icon: LucideIcon; title: string; description: string }> = [
  { icon: Upload, title: 'Cliente sube parte', description: 'Captura del siniestro y evidencia en un único flujo guiado.' },
  { icon: FileSearch, title: 'Intake extrae datos', description: 'La IA estructura el expediente y elimina trabajo manual.' },
  { icon: ShieldAlert, title: 'Risk evalúa fraude', description: 'Cruza señales de riesgo y detecta incoherencias automáticamente.' },
  { icon: Scale, title: 'Compliance valida regulación', description: 'Aplica reglas de negocio y cumplimiento antes de decidir.' },
  { icon: Gavel, title: 'Decisión', description: 'Aprueba, rechaza o escala con reasoning y trazabilidad completa.' },
];

const PLATFORM_STACK: PlatformBadge[] = [
  {
    icon: ShieldCheck,
    name: BRAND.partnerBannerName,
    description: 'caso de uso de seguros con foco en gobierno, marca y experiencia cliente',
    featured: true,
  },
  { icon: Sparkles, name: 'Microsoft Agent Framework', description: 'orquestación multi-agente gobernada' },
  { icon: Sparkles, name: 'Azure OpenAI', description: 'razonamiento, extracción y decisión asistida' },
  { icon: Shield, name: 'Microsoft Entra ID', description: 'identidad, roles y acceso corporativo seguro' },
  { icon: Database, name: 'Azure Cosmos DB', description: 'persistencia auditable de expedientes y resultados' },
  { icon: Activity, name: 'Azure API Management', description: 'seguridad, políticas y exposición controlada de APIs' },
];

const DEMO_USE_CASES: DemoUseCase[] = [
  {
    key: 'low_risk',
    icon: CheckCircle2,
    title: 'Bajo Riesgo',
    amount: 2500,
    expected: 'Aprobación automática',
    description: 'Colisión leve con parte amistoso firmado. Caso típico de alta frecuencia y bajo importe.',
    accent: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  },
  {
    key: 'high_amount',
    icon: Euro,
    title: 'Alto Monto',
    amount: 15000,
    expected: 'Aprobación con auditoría',
    description: 'Daños severos por temporal sobre vehículo de gama alta. Aprobación con trazabilidad reforzada.',
    accent: 'text-primary-700 bg-primary-50 border-primary-200',
  },
  {
    key: 'human_review',
    icon: UserCheck,
    title: 'Revisión Humana',
    amount: 32000,
    expected: 'Escalado a perito',
    description: 'Siniestro complejo con informe pericial. La IA escala al equipo humano por importe y casuística.',
    accent: 'text-amber-700 bg-amber-50 border-amber-200',
  },
  {
    key: 'prompt_injection',
    icon: ShieldAlert,
    title: 'Prompt Injection',
    amount: 3000,
    expected: 'Rechazo + alerta seguridad',
    description: 'Intento de manipular al agente con instrucciones ocultas. El guardrail lo detecta y bloquea.',
    accent: 'text-purple-700 bg-purple-50 border-purple-200',
  },
  {
    key: 'fraudulent',
    icon: Siren,
    title: 'Fraudulento',
    amount: 8500,
    expected: 'Escalado por riesgo alto',
    description: 'Robo sin testigos ni evidencia. Señales de fraude que disparan revisión humana.',
    accent: 'text-red-700 bg-red-50 border-red-200',
  },
];

const DEMO_TOTAL_EXPOSURE = DEMO_USE_CASES.reduce((sum, item) => sum + item.amount, 0);

function useCountUp(target: number, duration = 1_400): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const nextTarget = Number.isFinite(target) ? Math.max(0, Math.round(target)) : 0;
    if (nextTarget === 0) {
      setValue(0);
      return;
    }

    let frameId = 0;
    let startTime: number | null = null;

    const step = (timestamp: number) => {
      if (startTime === null) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(nextTarget * eased));
      if (progress < 1) {
        frameId = window.requestAnimationFrame(step);
      }
    };

    setValue(0);
    frameId = window.requestAnimationFrame(step);

    return () => window.cancelAnimationFrame(frameId);
  }, [duration, target]);

  return value;
}

function CountUpValue({
  target,
  formatter,
  className,
}: {
  target: number;
  formatter: (value: number) => string;
  className: string;
}) {
  const value = useCountUp(target);

  return <div className={className}>{formatter(value)}</div>;
}

function MetricCard({ icon: Icon, label, display, description, valueClass, countTarget, countFormatter }: HeroMetric) {
  const useCountUpValue = typeof countTarget === 'number' && countFormatter;
  return (
    <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <Icon className="pointer-events-none absolute right-5 top-5 h-16 w-16 text-primary-200" />
      <div className="relative">
        <div className="text-[11px] uppercase tracking-[0.26em] text-gray-500">{label}</div>
        {useCountUpValue ? (
          <CountUpValue
            target={countTarget!}
            formatter={countFormatter!}
            className={`animate-count-up mt-4 text-4xl font-bold tracking-tight md:text-5xl ${valueClass}`}
          />
        ) : (
          <div className={`animate-count-up mt-4 text-4xl font-bold tracking-tight md:text-5xl ${valueClass}`}>{display}</div>
        )}
        <p className="mt-3 max-w-[16rem] text-sm leading-relaxed text-gray-600">{description}</p>
      </div>
    </div>
  );
}

function formatInteger(value: number): string {
  return value.toLocaleString('es-ES');
}

function formatCurrency(value: number): string {
  return `€ ${Math.round(value).toLocaleString('es-ES')}`;
}

function formatPercent(value: number): string {
  return `${Math.round(value).toLocaleString('es-ES')}%`;
}

function formatSeconds(value: number): string {
  return `${value.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} s`;
}

export default function HeroView({ onCTAClick }: HeroViewProps) {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [claims, setClaims] = useState<ClaimSummary[]>([]);
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);

  const refreshHeroData = useCallback(async () => {
    const [statsResult, claimsResult, incidentsResult] = await Promise.allSettled([
      getStats(),
      getClaims(),
      getSecurityIncidents(),
    ]);

    if (statsResult.status === 'fulfilled') {
      setStats(statsResult.value);
    }

    if (claimsResult.status === 'fulfilled') {
      setClaims(claimsResult.value);
    }

    if (incidentsResult.status === 'fulfilled') {
      setIncidents(incidentsResult.value.incidents);
    }
  }, []);

  useEffect(() => {
    void refreshHeroData();
    const interval = window.setInterval(() => {
      void refreshHeroData();
    }, 20_000);

    return () => window.clearInterval(interval);
  }, [refreshHeroData]);

  const metrics = useMemo<HeroMetric[]>(() => {
    const hasStatsData = stats !== null && stats.total_claims > 0;
    const processedCount = stats?.total_claims ?? 0;
    const automatedCount = (stats?.approved ?? 0) + (stats?.rejected ?? 0);
    const automationRate = hasStatsData ? Math.round((automatedCount / stats!.total_claims) * 100) : null;
    const avgSeconds = hasStatsData && stats!.avg_duration_ms > 0 ? stats!.avg_duration_ms / 1000 : null;
    const securityIncidents = incidents.length;

    return [
      {
        icon: LayoutGrid,
        label: 'Casos de uso demo',
        display: formatInteger(DEMO_USE_CASES.length),
        description: 'Escenarios reales preparados: aprobación, alto monto, revisión humana, fraude y prompt injection.',
        valueClass: 'text-primary-600',
        countTarget: DEMO_USE_CASES.length,
        countFormatter: formatInteger,
      },
      {
        icon: Euro,
        label: 'Exposición demo',
        display: formatCurrency(DEMO_TOTAL_EXPOSURE),
        description: 'Importe total cubierto por los 5 escenarios de la demo (importe agregado a evaluar).',
        valueClass: 'text-gray-900',
        countTarget: DEMO_TOTAL_EXPOSURE,
        countFormatter: formatCurrency,
      },
      {
        icon: Sparkles,
        label: 'Procesados en esta sesión',
        display: hasStatsData ? formatInteger(processedCount) : '—',
        description: automationRate !== null
          ? `${automationRate}% resueltos automáticamente (approve + reject), el resto escalado a revisión humana.`
          : 'Lanza la demo o un caso individual para empezar a alimentar las métricas reales.',
        valueClass: 'text-gray-900',
        countTarget: hasStatsData ? processedCount : undefined,
        countFormatter: hasStatsData ? formatInteger : undefined,
      },
      {
        icon: Timer,
        label: 'Tiempo medio IA',
        display: avgSeconds !== null ? formatSeconds(avgSeconds) : '—',
        description: securityIncidents > 0
          ? `Pipeline end-to-end medido en vivo. ${securityIncidents} incidente(s) de seguridad detectado(s).`
          : 'Tiempo end-to-end del pipeline multi-agente, frente a los 45 min del proceso manual.',
        valueClass: 'text-primary-600',
      },
    ];
  }, [incidents.length, stats]);

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[28px] border border-gray-200 bg-gradient-to-br from-white via-primary-50 to-white px-8 py-10 shadow-lg md:px-12 md:py-14">
        <div className="pointer-events-none absolute -right-20 top-0 h-52 w-52 rounded-full bg-primary-100/80 blur-3xl" />
        <div className="pointer-events-none absolute -left-16 bottom-0 h-48 w-48 rounded-full bg-primary-50 blur-3xl" />

        <div className="relative mx-auto max-w-4xl space-y-6 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 shadow-sm">
            <Sparkles className="h-4 w-4 text-primary-500" />
            Plataforma comercial para tramitación inteligente de siniestros
          </div>

          <div className="space-y-4">
            <div className="mx-auto mb-4 inline-flex items-center justify-center gap-3 rounded-2xl border border-gray-200 bg-white px-6 py-3 shadow-md">
              <img src={BRAND.logoUrl} alt={BRAND.logoAlt} className="h-10 w-auto" />
              {!BRAND.logoHasWordmark && (
                <span className="text-2xl font-bold tracking-tight text-gray-900">{BRAND.name}</span>
              )}
            </div>
            <h2 className="text-4xl font-semibold tracking-tight md:text-6xl">
              <span className="text-gray-900">{BRAND.productName}</span>{' '}
              <span className="text-primary-600">{BRAND.productNameAccent}</span>
            </h2>
            <p className="mx-auto max-w-3xl text-lg leading-relaxed text-gray-600 md:text-xl">
              Caso de uso: {BRAND.name} · {BRAND.caseStudyDescription}
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-3">
            {HERO_BADGES.map(({ icon: Icon, label }) => (
              <div
                key={label}
                className="inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 shadow-sm"
              >
                <Icon className="h-3.5 w-3.5 text-primary-500" />
                <span>{label}</span>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={onCTAClick}
            className="inline-flex items-center gap-2 rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition-colors hover:bg-primary-700"
          >
            <Play className="h-4 w-4" fill="currentColor" />
            Probar ahora
          </button>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-gray-500">KPIs que compra negocio</p>
            <h3 className="text-2xl font-semibold text-gray-900">Resultado económico, eficiencia y control</h3>
          </div>
          <p className="text-sm text-gray-500">Conectado a /api/stats, /api/claims y /api/security/incidents.</p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <MetricCard key={metric.label} {...metric} />
          ))}
        </div>

        <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-gray-500">Casos de uso incluidos</p>
              <h4 className="text-xl font-semibold text-gray-900">5 escenarios que cubren el ciclo completo</h4>
            </div>
            <p className="text-sm text-gray-500">
              Exposición agregada: <span className="font-semibold text-gray-900">{formatCurrency(DEMO_TOTAL_EXPOSURE)}</span>
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {DEMO_USE_CASES.map(({ icon: Icon, title, amount, expected, description, accent, key }) => (
              <div key={key} className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-gray-50/60 p-4">
                <div className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${accent}`}>
                  <Icon className="h-3.5 w-3.5" />
                  {title}
                </div>
                <div>
                  <div className="text-lg font-semibold text-gray-900">{formatCurrency(amount)}</div>
                  <div className="text-[11px] uppercase tracking-[0.2em] text-gray-500">{expected}</div>
                </div>
                <p className="text-xs leading-relaxed text-gray-600">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-stretch">
        <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gray-50 text-gray-400">
              <Clock className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.26em] text-gray-500">Antes</p>
              <h3 className="text-2xl font-semibold text-gray-900">45 min por caso</h3>
            </div>
          </div>
          <ul className="space-y-3 text-sm text-gray-700">
            <li className="flex items-start gap-3">
              <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
              <span>Errores humanos al reescribir datos y revisar coberturas.</span>
            </li>
            <li className="flex items-start gap-3">
              <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
              <span>Sin audit trail trazable para justificar por qué se aprobó o rechazó.</span>
            </li>
            <li className="flex items-start gap-3">
              <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
              <span>Fraudes e intentos de manipulación que se cuelan hasta fases tardías.</span>
            </li>
          </ul>
        </div>

        <div className="hidden items-center justify-center md:flex">
          <div className="flex h-16 w-16 items-center justify-center rounded-full border border-gray-200 bg-white text-primary-400 shadow-sm">
            <ArrowRight className="h-7 w-7" />
          </div>
        </div>

        <div className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-50 text-primary-600">
              <Zap className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.26em] text-primary-600/80">Ahora</p>
              <h3 className="text-2xl font-semibold text-gray-900">30 segundos por caso</h3>
            </div>
          </div>
          <ul className="space-y-3 text-sm text-gray-700">
            <li className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
              <span>3 agentes IA colaboran y entregan una decisión lista para negocio.</span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
              <span>Audit trail completo para explicar, revisar y gobernar cada expediente.</span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
              <span>Fraude, prompt injection y anomalías detectadas automáticamente.</span>
            </li>
          </ul>
        </div>
      </section>

      <section className="rounded-3xl border border-gray-200 bg-gray-50 p-6 shadow-sm">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-gray-500">Flujo operativo</p>
            <h3 className="text-2xl font-semibold text-gray-900">De la carga del parte a la decisión final</h3>
          </div>
          <div className="hidden rounded-full border border-primary-200 bg-white px-3 py-1 text-xs text-primary-700 md:inline-flex">
            Multi-agent orchestration live
          </div>
        </div>

        <div className="overflow-x-auto pb-2">
          <div className="relative min-w-[980px] overflow-hidden">
            <div className="pointer-events-none absolute left-0 right-0 top-16 hidden h-px bg-gradient-to-r from-transparent via-primary-400/40 to-transparent md:block" />
            <div className="timeline-light pointer-events-none absolute top-16 hidden md:block" />

            <div className="grid gap-4 md:grid-cols-5">
              {FLOW_STEPS.map(({ icon: Icon, title, description }, index) => (
                <div key={title} className="relative rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-50 text-primary-600">
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className="text-[11px] font-medium uppercase tracking-[0.24em] text-gray-500">0{index + 1}</span>
                  </div>
                  <h4 className="text-base font-semibold text-gray-900">{title}</h4>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-gray-500">Powered by</p>
          <h3 className="text-2xl font-semibold text-gray-900">Stack enterprise listo para producción</h3>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {PLATFORM_STACK.map(({ icon: Icon, name, description, featured }) => (
            <div
              key={name}
              className={`flex items-center gap-4 rounded-xl border p-4 shadow-sm ${featured ? 'border-primary-300 bg-primary-50' : 'border-gray-200 bg-white'}`}
            >
              <div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${featured ? 'bg-white text-primary-600' : 'bg-primary-50 text-primary-600'}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-900">{name}</h4>
                <p className="text-xs text-gray-600">{description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-3xl border border-primary-200 bg-gradient-to-r from-primary-50 via-white to-primary-50 p-8 text-center shadow-sm">
        <p className="text-xs uppercase tracking-[0.28em] text-primary-700">Siguiente paso</p>
        <h3 className="mt-3 text-3xl font-semibold text-gray-900">Ver una demo automática ▶</h3>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-relaxed text-gray-600">
          Abre el flujo cliente para enseñar en directo cómo los agentes reducen tiempos, detectan fraude y dejan trazabilidad completa.
        </p>
        <button
          type="button"
          onClick={() => {
            // TODO: cuando autoplay-demo esté listo, abrir el modal en lugar de cambiar tab.
            onCTAClick();
          }}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-md transition-colors hover:bg-primary-700"
        >
          Ver una demo automática
          <ArrowRight className="h-4 w-4" />
        </button>
      </section>
    </div>
  );
}
