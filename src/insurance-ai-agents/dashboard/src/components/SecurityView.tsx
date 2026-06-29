import { useEffect, useState, useCallback } from 'react';
import { Shield, AlertTriangle, RefreshCw, FileWarning, Loader2 } from 'lucide-react';
import { getSecurityIncidents } from '../api';
import type { SecurityIncident } from '../api';

const SEVERITY_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-red-50 text-red-700 border-red-200',
  medium: 'bg-amber-50 text-amber-800 border-amber-200',
  low: 'bg-amber-50 text-amber-700 border-amber-200',
};

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-red-50 text-red-700 border-red-200',
  closed: 'bg-gray-100 text-gray-700 border-gray-200',
};

const TYPE_BADGE: Record<string, { label: string; classes: string }> = {
  prompt_injection: {
    label: 'Prompt injection',
    classes: 'bg-red-50 border-red-200 text-red-700',
  },
  fraud_suspected: {
    label: 'Posible fraude',
    classes: 'bg-amber-50 border-amber-200 text-amber-800',
  },
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function SecurityView() {
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);
  const [total, setTotal] = useState(0);
  const [open, setOpen] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    getSecurityIncidents()
      .then((response) => {
        setIncidents(response.incidents);
        setTotal(response.total);
        setOpen(response.open);
      })
      .catch(() => {})
      .finally(() => {
        setLoading(false);
        setLoaded(true);
      });
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-red-200 bg-red-50">
              <Shield className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Incidentes de Seguridad</h2>
              <p className="text-sm text-gray-600">Intentos de manipulación del sistema detectados por los agentes.</p>
            </div>
          </div>
          <button
            onClick={refresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:border-red-300 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <div className="mb-1 text-xs uppercase tracking-wide text-gray-500">Total detectados</div>
            <div className="text-2xl font-semibold text-gray-900">{total}</div>
          </div>
          <div className="rounded-xl border border-red-700 bg-red-600 p-4 text-white shadow-sm">
            <div className="mb-1 text-xs uppercase tracking-wide text-red-100">Abiertos</div>
            <div className="text-2xl font-semibold">{open}</div>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <div className="mb-1 text-xs uppercase tracking-wide text-gray-500">Cerrados</div>
            <div className="text-2xl font-semibold text-gray-900">{total - open}</div>
          </div>
        </div>
      </div>

      {!loaded || (loading && incidents.length === 0) ? (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-gray-200 bg-white p-12 text-sm text-gray-500 shadow-sm">
          <Loader2 className="h-5 w-5 animate-spin text-red-500" />
          Consultando incidentes de seguridad…
        </div>
      ) : incidents.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
          <Shield className="mx-auto mb-3 h-12 w-12 text-gray-300" />
          <p className="text-sm text-gray-600">No se han detectado incidentes de seguridad.</p>
          <p className="mt-1 text-xs text-gray-500">El sistema está monitorizando intentos de manipulación en tiempo real.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map((incident) => (
            <div
              key={`${incident.claim_id}-${incident.detected_at}`}
              className="rounded-xl border border-red-200 bg-white p-5 shadow-sm transition-colors hover:border-red-300"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-red-200 bg-red-50">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-gray-900">{incident.claim_id}</span>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${SEVERITY_BADGE[incident.severity] ?? SEVERITY_BADGE.medium}`}>
                      {incident.severity.toUpperCase()}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${STATUS_BADGE[incident.status] ?? STATUS_BADGE.open}`}>
                      {incident.status === 'open' ? 'ABIERTO' : 'CERRADO'}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${(TYPE_BADGE[incident.incident_type] ?? { classes: 'bg-gray-100 border-gray-200 text-gray-700' }).classes}`}>
                      {(TYPE_BADGE[incident.incident_type]?.label) ?? incident.incident_type}
                    </span>
                    <span className="ml-auto text-xs text-gray-500">{formatDate(incident.detected_at)}</span>
                  </div>

                  <p className="mb-3 text-sm text-gray-800">{incident.description}</p>

                  <div className="mb-3 grid grid-cols-1 gap-3 text-xs sm:grid-cols-2">
                    <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                      <div className="mb-0.5 text-[10px] uppercase tracking-wide text-gray-500">Póliza</div>
                      <div className="font-mono text-gray-800">{incident.policy_id}</div>
                    </div>
                    <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                      <div className="mb-0.5 text-[10px] uppercase tracking-wide text-gray-500">Cliente</div>
                      <div className="font-mono text-gray-800">{incident.customer_id}</div>
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div className="mb-1.5 flex items-center gap-1.5">
                      <FileWarning className="h-3.5 w-3.5 text-amber-600" />
                      <span className="text-[10px] uppercase tracking-wide text-gray-500">Extracto de la carga maliciosa</span>
                    </div>
                    <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-gray-700">
                      {incident.raw_payload_excerpt}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
