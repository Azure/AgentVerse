import { Fragment, useState, useEffect, useCallback } from 'react';
import { ScrollText, Plus, Loader2, RefreshCw, ChevronDown, ChevronUp, User, FileText } from 'lucide-react';
import type { Policy, NewPolicyRequest, PolicyDetail, CustomerHistory } from '../api';
import { getPolicies, registerPolicy, getPolicyDetail, getCustomers } from '../api';

const EMPTY_FORM: NewPolicyRequest = {
  customer_id: '',
  vehicle: '',
  coverage_type: 'Todo Riesgo',
  max_coverage: 50000,
  start_date: '',
  end_date: '',
};

function Field({ label, value }: Readonly<{ label: string; value: unknown }>) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="flex gap-2 text-xs">
      <span className="shrink-0 text-gray-500">{label}:</span>
      <span className="text-gray-800">{String(value)}</span>
    </div>
  );
}

export default function PolicyView() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [customers, setCustomers] = useState<CustomerHistory[]>([]);
  const [form, setForm] = useState<NewPolicyRequest>({ ...EMPTY_FORM });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<PolicyDetail | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [listLoaded, setListLoaded] = useState(false);

  const refresh = useCallback(() => {
    setListLoading(true);
    Promise.allSettled([
      getPolicies().then(setPolicies),
      getCustomers().then(setCustomers),
    ]).finally(() => {
      setListLoading(false);
      setListLoaded(true);
    });
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.customer_id || !form.vehicle || !form.max_coverage) return;
    setSubmitting(true);
    setError('');
    setSuccess('');
    try {
      const newPolicy = await registerPolicy(form);
      setPolicies((previous) => [newPolicy, ...previous]);
      setForm({ ...EMPTY_FORM });
      setSuccess(`Póliza ${newPolicy.policy_id} registrada correctamente.`);
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al registrar póliza');
    } finally {
      setSubmitting(false);
    }
  };

  const toggleRow = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }

    setExpandedId(id);
    setDetail(null);
    try {
      const response = await getPolicyDetail(id);
      setDetail(response);
    } catch {
      setDetail(null);
    }
  };

  const inputClass = 'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200';
  const labelClass = 'mb-1.5 block text-sm font-medium text-gray-700';
  const noCustomers = listLoaded && customers.length === 0;

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-1 flex items-center gap-2">
          <Plus className="h-5 w-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Registrar Nueva Póliza</h2>
        </div>
        <p className="mb-6 text-sm text-gray-600">
          La póliza se vincula a un cliente existente. Si el cliente no está dado de alta, créalo antes desde la pestaña Clientes.
        </p>

        {noCustomers && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            No hay clientes registrados. Crea uno primero en la pestaña <strong>Clientes</strong>.
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="block md:col-span-2">
              <span className={labelClass}>Cliente *</span>
              <select
                value={form.customer_id}
                onChange={(e) => setForm((current) => ({ ...current, customer_id: e.target.value }))}
                className={inputClass}
                required
                disabled={noCustomers}
              >
                <option value="">Selecciona un cliente</option>
                {customers.map((customer) => (
                  <option key={customer.customer_id} value={customer.customer_id}>
                    {customer.customer_id} · {customer.name} ({customer.risk_profile})
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className={labelClass}>Vehículo *</span>
              <input
                type="text"
                value={form.vehicle}
                onChange={(e) => setForm((current) => ({ ...current, vehicle: e.target.value }))}
                placeholder="Toyota Corolla 2023"
                className={inputClass}
                required
              />
            </label>
            <label className="block">
              <span className={labelClass}>Tipo de cobertura</span>
              <select
                value={form.coverage_type}
                onChange={(e) => setForm((current) => ({ ...current, coverage_type: e.target.value }))}
                className={inputClass}
              >
                <option value="Todo Riesgo">Todo Riesgo</option>
                <option value="Terceros">Terceros</option>
                <option value="Terceros Ampliado">Terceros Ampliado</option>
              </select>
            </label>
            <label className="block">
              <span className={labelClass}>Cobertura máxima (€) *</span>
              <input
                type="number"
                value={form.max_coverage || ''}
                onChange={(e) => setForm((current) => ({ ...current, max_coverage: Number.parseFloat(e.target.value) || 0 }))}
                placeholder="50000"
                min="1"
                className={inputClass}
                required
              />
            </label>
            <label className="block">
              <span className={labelClass}>Fecha de inicio</span>
              <input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm((current) => ({ ...current, start_date: e.target.value }))}
                className={inputClass}
              />
            </label>
            <label className="block">
              <span className={labelClass}>Fecha de vencimiento</span>
              <input
                type="date"
                value={form.end_date}
                onChange={(e) => setForm((current) => ({ ...current, end_date: e.target.value }))}
                className={inputClass}
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={submitting || noCustomers}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Registrando…
              </>
            ) : (
              <>
                <Plus className="h-4 w-4" /> Registrar Póliza
              </>
            )}
          </button>
        </form>

        {error && <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
        {success && <p className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{success}</p>}
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-2">
            <ScrollText className="h-5 w-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">Pólizas Registradas</h2>
          </div>
          <button
            onClick={refresh}
            disabled={listLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:border-primary-300 hover:bg-primary-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${listLoading ? 'animate-spin' : ''}`} /> Actualizar
          </button>
        </div>

        {!listLoaded || (listLoading && policies.length === 0) ? (
          <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-sm text-gray-500">
            <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
            Cargando pólizas desde la base de datos…
          </div>
        ) : policies.length === 0 ? (
          <p className="px-6 py-8 text-center text-sm text-gray-500">No hay pólizas registradas.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-[920px] w-full">
              <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-700">
                <tr>
                  <th className="px-4 py-3">Póliza ID</th>
                  <th className="px-4 py-3">Titular</th>
                  <th className="px-4 py-3">Vehículo</th>
                  <th className="px-4 py-3">Cobertura</th>
                  <th className="px-4 py-3">Máximo</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3 text-right">Detalle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {policies.map((policy) => (
                  <Fragment key={policy.policy_id}>
                    <tr className="cursor-pointer transition-colors hover:bg-gray-50" onClick={() => toggleRow(policy.policy_id)}>
                      <td className="px-4 py-3 font-mono text-xs text-gray-900">{policy.policy_id}</td>
                      <td className="px-4 py-3 text-sm text-gray-800">{policy.customer_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{policy.vehicle}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{policy.coverage_type}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">€{policy.max_coverage.toLocaleString('es-ES')}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                          {policy.status || 'Activa'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-400">
                        {expandedId === policy.policy_id ? <ChevronUp className="ml-auto h-4 w-4" /> : <ChevronDown className="ml-auto h-4 w-4" />}
                      </td>
                    </tr>

                    {expandedId === policy.policy_id && (
                      <tr className="bg-gray-50">
                        <td colSpan={7} className="border-t border-gray-200 px-4 py-4">
                          {detail ? (
                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                                <div className="mb-2 flex items-center gap-1.5">
                                  <FileText className="h-4 w-4 text-primary-600" />
                                  <span className="text-sm font-semibold text-gray-900">Datos de la póliza</span>
                                </div>
                                <div className="space-y-1.5">
                                  <Field label="ID póliza" value={detail.policy_id} />
                                  <Field label="ID cliente" value={detail.customer_id} />
                                  <Field label="Vehículo" value={detail.vehicle} />
                                  <Field label="Cobertura" value={detail.coverage_type} />
                                  <Field label="Máx. cubierto" value={`${detail.max_coverage.toLocaleString('es-ES')}€`} />
                                  <Field label="Estado" value={detail.status} />
                                  <Field label="Inicio" value={detail.start_date} />
                                  <Field label="Vencimiento" value={detail.end_date} />
                                </div>
                              </div>
                              {detail.customer_history && (
                                <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                                  <div className="mb-2 flex items-center gap-1.5">
                                    <User className="h-4 w-4 text-primary-600" />
                                    <span className="text-sm font-semibold text-gray-900">Cliente vinculado</span>
                                  </div>
                                  <div className="space-y-1.5">
                                    <Field label="Nombre" value={detail.customer_history.name} />
                                    <Field label="Antigüedad" value={`${detail.customer_history.years_as_customer} años`} />
                                    <Field label="Reclamaciones previas" value={detail.customer_history.previous_claims} />
                                    <Field label="Perfil de riesgo" value={detail.customer_history.risk_profile} />
                                    <Field label="Historial de pagos" value={detail.customer_history.payment_history} />
                                  </div>
                                </div>
                              )}
                            </div>
                          ) : (
                            <p className="text-sm text-gray-500">Cargando detalle…</p>
                          )}
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
