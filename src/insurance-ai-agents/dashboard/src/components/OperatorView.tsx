import { Fragment, useState, useEffect, useCallback } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  ClipboardList,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Brain,
  ShieldCheck,
  Scale,
  Image as ImageIcon,
  FileText,
  User,
  Sparkles,
  Loader2,
} from 'lucide-react';
import type { ClaimSummary, ClaimAuditDetail } from '../api';
import { getClaims, getClaimAudit, getClaimImage } from '../api';

const DECISION_BADGE: Record<string, string> = {
  approve: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  human_review: 'bg-amber-50 text-amber-800 border-amber-200',
  reject: 'bg-red-50 text-red-700 border-red-200',
};

const DECISION_LABEL: Record<string, string> = {
  approve: 'Aprobado',
  human_review: 'Revisión',
  reject: 'Rechazado',
};

function Section({
  icon: Icon,
  title,
  aiBadge,
  children,
}: Readonly<{ icon: LucideIcon; title: string; aiBadge?: boolean; children: React.ReactNode }>) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-primary-600" />
          <h4 className="text-sm font-semibold text-gray-900">{title}</h4>
        </div>
        {aiBadge && (
          <span className="inline-flex items-center gap-1 rounded-full border border-primary-200 bg-primary-50 px-2 py-0.5 text-[10px] text-primary-700">
            <Sparkles className="h-3 w-3" />
            GPT-4o · Azure OpenAI
          </span>
        )}
      </div>
      <div className="space-y-2 text-xs text-gray-700">{children}</div>
    </div>
  );
}

function Field({ label, value }: Readonly<{ label: string; value: unknown }>) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="flex gap-2 text-xs">
      <span className="shrink-0 text-gray-500">{label}:</span>
      <span className="text-gray-800">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
    </div>
  );
}

export default function OperatorView() {
  const [claims, setClaims] = useState<ClaimSummary[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClaimAuditDetail | null>(null);
  const [image, setImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [listLoaded, setListLoaded] = useState(false);

  const fetchClaims = useCallback(() => {
    setListLoading(true);
    getClaims()
      .then(setClaims)
      .catch(() => {})
      .finally(() => {
        setListLoading(false);
        setListLoaded(true);
      });
  }, []);

  useEffect(() => {
    fetchClaims();
    const interval = setInterval(fetchClaims, 10_000);
    return () => clearInterval(interval);
  }, [fetchClaims]);

  const toggleRow = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
      setImage(null);
      return;
    }

    setExpandedId(id);
    setLoading(true);
    setDetail(null);
    setImage(null);

    try {
      const data = await getClaimAudit(id);
      setDetail(data);
      if (data.has_image) {
        const img = await getClaimImage(id);
        setImage(img);
      }
    } catch {
      setDetail(null);
    } finally {
      setLoading(false);
    }
  };

  const reviewQueueCount = claims.filter((claim) => claim.decision === 'human_review').length;

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary-100 bg-primary-50">
              <ClipboardList className="h-5 w-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Panel del Operario</h2>
              <p className="text-sm text-gray-600">Siniestros procesados y expedientes pendientes de revisión manual.</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">
              {reviewQueueCount} en revisión humana
            </span>
            <button
              onClick={fetchClaims}
              disabled={listLoading}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:border-primary-300 hover:bg-primary-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${listLoading ? 'animate-spin' : ''}`} />
              Actualizar
            </button>
          </div>
        </div>

        {!listLoaded || (listLoading && claims.length === 0) ? (
          <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-sm text-gray-500">
            <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
            Cargando siniestros desde la base de datos…
          </div>
        ) : claims.length === 0 ? (
          <p className="px-6 py-8 text-center text-sm text-gray-500">No hay siniestros procesados aún.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-[920px] w-full">
              <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-700">
                <tr>
                  <th className="px-4 py-3">Claim ID</th>
                  <th className="px-4 py-3">Decisión</th>
                  <th className="px-4 py-3">Confianza</th>
                  <th className="px-4 py-3">Duración</th>
                  <th className="px-4 py-3">Fecha</th>
                  <th className="px-4 py-3 text-right">Detalle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {claims.map((claim) => (
                  <Fragment key={claim.claim_id}>
                    <tr className="cursor-pointer transition-colors hover:bg-gray-50" onClick={() => toggleRow(claim.claim_id)}>
                      <td className="px-4 py-3 font-mono text-xs text-gray-900">{claim.claim_id}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${DECISION_BADGE[claim.decision] || 'border-gray-200 bg-gray-50 text-gray-600'}`}>
                          {DECISION_LABEL[claim.decision] || claim.decision}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">{(claim.confidence * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{(claim.total_duration_ms / 1000).toFixed(2)}s</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{new Date(claim.timestamp).toLocaleString('es-ES')}</td>
                      <td className="px-4 py-3 text-right text-gray-400">
                        {expandedId === claim.claim_id ? <ChevronUp className="ml-auto h-4 w-4" /> : <ChevronDown className="ml-auto h-4 w-4" />}
                      </td>
                    </tr>

                    {expandedId === claim.claim_id && (
                      <tr className="bg-gray-50">
                        <td colSpan={6} className="border-t border-gray-200 px-4 py-4">
                          {(() => {
                            if (loading) return <p className="text-sm text-gray-500">Cargando detalle…</p>;
                            if (!detail) return <p className="text-sm text-gray-500">No se pudo cargar el detalle.</p>;

                            return (
                              <div className="space-y-4">
                                <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                                  <div className="mb-2 flex items-center justify-between gap-3">
                                    <h3 className="text-sm font-semibold text-gray-900">Decisión final del orquestador</h3>
                                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${DECISION_BADGE[detail.decision]}`}>
                                      {DECISION_LABEL[detail.decision]} · {(detail.confidence * 100).toFixed(0)}%
                                    </span>
                                  </div>
                                  <p className="text-sm leading-relaxed text-gray-700">{detail.reasoning}</p>
                                </div>

                                {image && (
                                  <Section icon={ImageIcon} title="Evidencia fotográfica analizada por GPT-4o Vision">
                                    <div className="flex min-w-0 flex-col items-start gap-4 md:flex-row">
                                      <img
                                        src={`data:image/jpeg;base64,${image}`}
                                        alt="Evidencia"
                                        className="max-h-48 w-full shrink-0 rounded-lg border border-gray-200 bg-white object-contain md:w-48"
                                      />
                                      <div className="min-w-0 flex-1 space-y-2">
                                        {detail.intake_result?.image_matches_description === false && (
                                          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
                                            ⚠ Imagen NO coherente con el siniestro
                                            {detail.intake_result?.image_concerns && <div className="mt-0.5 text-red-700">{detail.intake_result.image_concerns}</div>}
                                          </div>
                                        )}
                                        {detail.intake_result?.image_matches_description === true && (
                                          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                                            ✓ Imagen coherente con el siniestro descrito
                                          </div>
                                        )}
                                        <div>
                                          <span className="text-xs text-gray-500">Análisis del agente sobre la imagen:</span>
                                          <p className="mt-1 break-words text-sm leading-relaxed text-gray-700">
                                            {detail.intake_result?.image_analysis || 'El agente integró el análisis visual en el resumen general.'}
                                          </p>
                                        </div>
                                      </div>
                                    </div>
                                  </Section>
                                )}

                                {(detail.policy || detail.customer_history) && (
                                  <Section icon={FileText} title="Fuentes de datos consultadas por los agentes">
                                    <p className="mb-2 text-xs italic text-gray-500">
                                      Esta es la información real del sistema (póliza + historial del cliente) que los agentes han usado vía tool calls.
                                    </p>
                                    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                                      {detail.policy && (
                                        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                                          <div className="mb-2 flex items-center gap-1.5">
                                            <FileText className="h-3.5 w-3.5 text-primary-600" />
                                            <span className="text-xs font-semibold text-gray-900">Póliza {detail.policy.policy_id}</span>
                                          </div>
                                          <Field label="Titular" value={detail.policy.customer_name} />
                                          <Field label="Vehículo" value={detail.policy.vehicle} />
                                          <Field label="Cobertura" value={detail.policy.coverage_type} />
                                          <Field label="Máx. cubierto" value={`${detail.policy.max_coverage.toLocaleString('es-ES')}€`} />
                                          <Field label="Estado" value={detail.policy.status} />
                                          <Field label="Vigencia" value={detail.policy.start_date && detail.policy.end_date ? `${detail.policy.start_date} → ${detail.policy.end_date}` : null} />
                                        </div>
                                      )}
                                      {detail.customer_history && (
                                        <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                                          <div className="mb-2 flex items-center gap-1.5">
                                            <User className="h-3.5 w-3.5 text-primary-600" />
                                            <span className="text-xs font-semibold text-gray-900">Cliente {detail.customer_history.customer_id}</span>
                                          </div>
                                          <Field label="Nombre" value={detail.customer_history.name} />
                                          <Field label="Antigüedad" value={`${detail.customer_history.years_as_customer} años`} />
                                          <Field label="Reclamaciones previas" value={detail.customer_history.previous_claims} />
                                          <Field label="Perfil de riesgo" value={detail.customer_history.risk_profile} />
                                          <Field label="Historial de pagos" value={detail.customer_history.payment_history} />
                                          {detail.customer_history.previous_claims_details.length > 0 && (
                                            <div className="mt-2">
                                              <span className="text-xs text-gray-500">Reclamaciones anteriores:</span>
                                              <ul className="mt-1 space-y-0.5 text-xs text-gray-700">
                                                {detail.customer_history.previous_claims_details.map((previousClaim) => (
                                                  <li key={`${previousClaim.year}-${previousClaim.type}`}>
                                                    • {previousClaim.year} · {previousClaim.type} · {previousClaim.amount.toLocaleString('es-ES')}€ · <span className="text-gray-500">{previousClaim.status}</span>
                                                  </li>
                                                ))}
                                              </ul>
                                            </div>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  </Section>
                                )}

                                <Section icon={Brain} title="Agente 1 · Claims Intake" aiBadge>
                                  <Field label="Póliza válida" value={detail.intake_result?.policy_valid} />
                                  <Field label="Severidad" value={detail.intake_result?.severity} />
                                  <div className="pt-1">
                                    <span className="text-gray-500">Resumen del agente:</span>
                                    <p className="mt-1 text-sm leading-relaxed text-gray-700">{detail.intake_result?.summary}</p>
                                  </div>
                                  {detail.intake_result?.extracted_data && (
                                    <details className="pt-2">
                                      <summary className="cursor-pointer text-gray-500 transition-colors hover:text-gray-700">Datos extraídos</summary>
                                      <pre className="mt-2 overflow-x-auto rounded-lg border border-gray-200 bg-gray-50 p-3 text-[11px] text-gray-700">{JSON.stringify(detail.intake_result.extracted_data, null, 2)}</pre>
                                    </details>
                                  )}
                                </Section>

                                <Section icon={ShieldCheck} title="Agente 2 · Risk Assessment" aiBadge>
                                  <Field label="Score de riesgo" value={`${detail.risk_result?.risk_score}/10`} />
                                  <Field label="Probabilidad de fraude" value={detail.risk_result?.fraud_probability} />
                                  <div className="pt-1">
                                    <span className="text-gray-500">Razonamiento:</span>
                                    <p className="mt-1 text-sm leading-relaxed text-gray-700">{detail.risk_result?.reasoning}</p>
                                  </div>
                                  {Array.isArray(detail.risk_result?.risk_factors) && detail.risk_result.risk_factors.length > 0 && (
                                    <div className="pt-2">
                                      <span className="text-gray-500">Factores considerados:</span>
                                      <ul className="mt-1 space-y-1">
                                        {detail.risk_result.risk_factors.map((factor: any) => (
                                          <li key={factor.factor} className="flex items-start gap-2">
                                            <span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${factor.impact === 'positive' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                                            <span className="text-gray-700">
                                              {factor.factor} <span className="text-gray-500">(peso {factor.weight})</span>
                                            </span>
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </Section>

                                <Section icon={Scale} title="Agente 3 · Compliance" aiBadge>
                                  <Field
                                    label="Cumple normativa"
                                    value={detail.compliance_result?.compliant === undefined ? null : detail.compliance_result.compliant ? 'Sí' : 'No'}
                                  />
                                  <Field label="Decisión recomendada" value={detail.compliance_result?.decision} />
                                  <div className="pt-1">
                                    <span className="text-gray-500">Razonamiento:</span>
                                    <p className="mt-1 text-sm leading-relaxed text-gray-700">{detail.compliance_result?.reasoning}</p>
                                  </div>
                                  {Array.isArray(detail.compliance_result?.regulations_checked) && (
                                    <div className="pt-2">
                                      <span className="text-gray-500">Regulaciones aplicadas:</span>
                                      <div className="mt-1 flex flex-wrap gap-1">
                                        {detail.compliance_result.regulations_checked.map((regulation: string) => (
                                          <span
                                            key={regulation}
                                            className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] text-gray-700"
                                          >
                                            {regulation}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </Section>

                                <Section icon={ClipboardList} title="Trazabilidad del pipeline">
                                  <div className="space-y-2">
                                    {detail.audit_trail.map((entry) => (
                                      <div
                                        key={`${entry.stage}-${entry.timestamp}`}
                                        className="grid gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700 md:grid-cols-[minmax(0,10rem)_6rem_5rem_minmax(0,1fr)]"
                                      >
                                        <span className="font-mono text-primary-600">{entry.stage}</span>
                                        <span className={entry.status === 'completed' ? 'text-emerald-700' : 'text-red-700'}>{entry.status}</span>
                                        <span className="text-gray-500">{entry.duration_ms}ms</span>
                                        <span>{entry.result_summary}</span>
                                      </div>
                                    ))}
                                  </div>
                                </Section>
                              </div>
                            );
                          })()}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
