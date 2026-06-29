import { CheckCircle2, AlertTriangle, XCircle, Clock, Gauge, Sparkles } from 'lucide-react';
import type { ClaimResult } from '../api';

interface Props {
  result: ClaimResult;
}

const decisionConfig = {
  approve: {
    icon: CheckCircle2,
    label: 'APROBADO',
    sublabel: 'Aprobación Automática',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    text: 'text-emerald-700',
  },
  human_review: {
    icon: AlertTriangle,
    label: 'REVISIÓN HUMANA',
    sublabel: 'Requiere Validación Manual',
    badge: 'bg-amber-50 text-amber-800 border-amber-200',
    text: 'text-amber-800',
  },
  reject: {
    icon: XCircle,
    label: 'RECHAZADO',
    sublabel: 'Siniestro Denegado',
    badge: 'bg-red-50 text-red-700 border-red-200',
    text: 'text-red-700',
  },
};

export default function DecisionPanel({ result }: Props) {
  const cfg = decisionConfig[result.decision] || decisionConfig.human_review;
  const Icon = cfg.icon;
  const riskScore = (result.risk_result as Record<string, unknown>)?.risk_score as number;
  const fraudProb = (result.risk_result as Record<string, unknown>)?.fraud_probability as string;
  const fraudTone = fraudProb === 'high'
    ? 'text-red-700'
    : fraudProb === 'medium'
      ? 'text-amber-700'
      : 'text-emerald-700';

  return (
    <div className="space-y-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="text-center">
        <div className={`inline-flex items-center gap-3 rounded-full border px-6 py-3 ${cfg.badge}`}>
          <Icon className={`h-8 w-8 ${cfg.text}`} />
          <div className="text-left">
            <p className={`text-2xl font-bold tracking-wide ${cfg.text}`}>{cfg.label}</p>
            <p className="text-xs text-gray-500">{cfg.sublabel}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-center">
          <Gauge className="mx-auto mb-1 h-4 w-4 text-gray-400" />
          <p className="text-xl font-bold text-gray-900">
            {riskScore ?? '—'}<span className="text-xs text-gray-500">/10</span>
          </p>
          <p className="text-[10px] uppercase text-gray-500">Risk Score</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-center">
          <AlertTriangle className="mx-auto mb-1 h-4 w-4 text-gray-400" />
          <p className={`text-sm font-bold ${fraudTone}`}>
            {fraudProb === 'high' ? 'ALTO' : fraudProb === 'medium' ? 'MEDIO' : 'BAJO'}
          </p>
          <p className="text-[10px] uppercase text-gray-500">Fraude</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-center">
          <Clock className="mx-auto mb-1 h-4 w-4 text-gray-400" />
          <p className="text-xl font-bold text-gray-900">
            {(result.total_duration_ms / 1000).toFixed(1)}<span className="text-xs text-gray-500">s</span>
          </p>
          <p className="text-[10px] uppercase text-gray-500">Duración</p>
        </div>
      </div>

      <div>
        <div className="mb-1 flex justify-between text-xs text-gray-500">
          <span>Confianza</span>
          <span>{(result.confidence * 100).toFixed(0)}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
          <div
            className="h-full rounded-full bg-primary-600 transition-all duration-1000"
            style={{ width: `${result.confidence * 100}%` }}
          />
        </div>
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-xs font-medium uppercase text-gray-500">Razonamiento</h4>
          <span className="inline-flex items-center gap-1 rounded-full border border-primary-200 bg-primary-50 px-2 py-0.5 text-[10px] text-primary-700">
            <Sparkles className="h-3 w-3" />
            Generado por GPT-4o · Azure OpenAI
          </span>
        </div>
        <p className="text-sm leading-relaxed text-gray-700">{result.reasoning}</p>
      </div>
    </div>
  );
}
