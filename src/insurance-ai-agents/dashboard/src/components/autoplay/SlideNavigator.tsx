import type { LucideIcon } from 'lucide-react';
import {
  ArrowRight,
  CheckCircle2,
  FileSearch,
  Gavel,
  Radio,
  Scale,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';

export type SlideKey = 'intake' | 'risk_assessment' | 'compliance' | 'decision';
export type SlideStatus = 'pending' | 'live' | 'completed' | 'failed';

export interface SlideDescriptor {
  key: SlideKey;
  status: SlideStatus;
  hasSnapshot: boolean;
  unseen: boolean;
}

interface SlideMeta {
  icon: LucideIcon;
  label: string;
  short: string;
}

const SLIDE_META: Record<SlideKey, SlideMeta> = {
  intake: { icon: FileSearch, label: 'Intake Agent', short: 'Intake' },
  risk_assessment: { icon: ShieldAlert, label: 'Risk Agent', short: 'Riesgo' },
  compliance: { icon: Scale, label: 'Compliance Agent', short: 'Compliance' },
  decision: { icon: Gavel, label: 'Decision Agent', short: 'Decisión' },
};

interface SlideNavigatorProps {
  slides: SlideDescriptor[];
  viewingSlide: SlideKey;
  liveSlide: SlideKey;
  isPinned: boolean;
  onSelect: (slide: SlideKey) => void;
  onReturnToLive: () => void;
}

function statusClasses(status: SlideStatus, isActive: boolean, hasSnapshot: boolean): string {
  if (isActive) {
    if (status === 'live') return 'border-primary-400 bg-primary-50 text-primary-800 shadow-sm';
    if (status === 'completed') return 'border-emerald-300 bg-emerald-50 text-emerald-800 shadow-sm';
    if (status === 'failed') return 'border-red-300 bg-red-50 text-red-800 shadow-sm';
    return 'border-gray-300 bg-white text-gray-800 shadow-sm';
  }
  if (status === 'live') return 'border-primary-300 bg-white text-primary-700 hover:bg-primary-50';
  if (status === 'completed' && hasSnapshot) return 'border-emerald-200 bg-white text-emerald-700 hover:bg-emerald-50';
  if (status === 'failed') return 'border-red-200 bg-white text-red-700 hover:bg-red-50';
  return 'border-dashed border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed';
}

function StatusBadge({ status, hasSnapshot }: { status: SlideStatus; hasSnapshot: boolean }) {
  if (status === 'live') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-primary-700">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-primary-600" />
        </span>
        Directo
      </span>
    );
  }
  if (status === 'completed' && hasSnapshot) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-700">
        <CheckCircle2 className="h-3 w-3" />
        Completado
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-red-700">Fallido</span>
    );
  }
  return (
    <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-400">Pendiente</span>
  );
}

export default function SlideNavigator({
  slides,
  viewingSlide,
  liveSlide,
  isPinned,
  onSelect,
  onReturnToLive,
}: SlideNavigatorProps) {
  const liveMeta = SLIDE_META[liveSlide];
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-gray-500">Pipeline de agentes</p>
        {isPinned ? (
          <button
            type="button"
            onClick={onReturnToLive}
            className="inline-flex items-center gap-1.5 rounded-full border border-primary-300 bg-primary-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary-700 transition hover:bg-primary-100"
          >
            <Radio className="h-3 w-3" />
            Volver al directo · {liveMeta.short}
            <ArrowRight className="h-3 w-3" />
          </button>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">
            <Sparkles className="h-3 w-3" />
            Siguiendo al agente activo
          </span>
        )}
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {slides.map((slide) => {
          const meta = SLIDE_META[slide.key];
          const Icon = meta.icon;
          const isActive = slide.key === viewingSlide;
          const clickable = slide.status === 'live' || slide.status === 'failed' || (slide.status === 'completed' && slide.hasSnapshot);
          const classes = statusClasses(slide.status, isActive, slide.hasSnapshot);
          return (
            <button
              key={slide.key}
              type="button"
              onClick={() => clickable && onSelect(slide.key)}
              disabled={!clickable}
              aria-pressed={isActive}
              className={`relative flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition ${classes}`}
            >
              <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                slide.status === 'live'
                  ? 'bg-primary-600 text-white'
                  : slide.status === 'completed' && slide.hasSnapshot
                    ? 'bg-emerald-100 text-emerald-700'
                    : slide.status === 'failed'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-200 text-gray-500'
              }`}>
                <Icon className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{meta.short}</p>
                <StatusBadge status={slide.status} hasSnapshot={slide.hasSnapshot} />
              </div>
              {slide.unseen && (
                <span className="absolute right-2 top-2 inline-flex items-center gap-1 rounded-full bg-primary-600 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-white shadow">
                  Nuevo
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
