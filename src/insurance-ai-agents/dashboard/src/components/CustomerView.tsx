import { Fragment, useState, useEffect, useCallback } from 'react';
import { Users, UserPlus, Loader2, RefreshCw, ChevronDown, ChevronUp, FileText } from 'lucide-react';
import type { CustomerHistory, NewCustomerRequest, CustomerDetail } from '../api';
import { getCustomers, registerCustomer, getCustomerDetail } from '../api';

const EMPTY_FORM: NewCustomerRequest = {
  name: '',
  years_as_customer: 0,
  previous_claims: 0,
  risk_profile: 'low',
  payment_history: 'excellent',
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

export default function CustomerView() {
  const [customers, setCustomers] = useState<CustomerHistory[]>([]);
  const [form, setForm] = useState<NewCustomerRequest>({ ...EMPTY_FORM });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<CustomerDetail | null>(null);
  const [listLoading, setListLoading] = useState(true);
  const [listLoaded, setListLoaded] = useState(false);

  const fetchCustomers = useCallback(() => {
    setListLoading(true);
    getCustomers()
      .then(setCustomers)
      .catch(() => {})
      .finally(() => {
        setListLoading(false);
        setListLoaded(true);
      });
  }, []);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name) return;
    setSubmitting(true);
    setError('');
    setSuccess('');
    try {
      const newCustomer = await registerCustomer(form);
      setCustomers((previous) => [newCustomer, ...previous]);
      setForm({ ...EMPTY_FORM });
      setSuccess(`Cliente ${newCustomer.customer_id} registrado correctamente.`);
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al registrar cliente');
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
      const response = await getCustomerDetail(id);
      setDetail(response);
    } catch {
      setDetail(null);
    }
  };

  const inputClass = 'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200';
  const labelClass = 'mb-1.5 block text-sm font-medium text-gray-700';

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-1 flex items-center gap-2">
          <UserPlus className="h-5 w-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Registrar Nuevo Cliente</h2>
        </div>
        <p className="mb-6 text-sm text-gray-600">
          El cliente queda disponible para vincularle pólizas y los agentes consultarán su historial al evaluar siniestros.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="block">
              <span className={labelClass}>Nombre completo *</span>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))}
                placeholder="María García López"
                className={inputClass}
                required
              />
            </label>
            <label className="block">
              <span className={labelClass}>Antigüedad como cliente (años)</span>
              <input
                type="number"
                value={form.years_as_customer}
                onChange={(e) => setForm((current) => ({ ...current, years_as_customer: Number.parseInt(e.target.value, 10) || 0 }))}
                min="0"
                className={inputClass}
              />
            </label>
            <label className="block">
              <span className={labelClass}>Reclamaciones previas</span>
              <input
                type="number"
                value={form.previous_claims}
                onChange={(e) => setForm((current) => ({ ...current, previous_claims: Number.parseInt(e.target.value, 10) || 0 }))}
                min="0"
                className={inputClass}
              />
            </label>
            <label className="block">
              <span className={labelClass}>Perfil de riesgo</span>
              <select
                value={form.risk_profile}
                onChange={(e) => setForm((current) => ({ ...current, risk_profile: e.target.value }))}
                className={inputClass}
              >
                <option value="low">Bajo</option>
                <option value="medium">Medio</option>
                <option value="high">Alto</option>
                <option value="unknown">Desconocido</option>
              </select>
            </label>
            <label className="block md:col-span-2">
              <span className={labelClass}>Historial de pagos</span>
              <select
                value={form.payment_history}
                onChange={(e) => setForm((current) => ({ ...current, payment_history: e.target.value }))}
                className={inputClass}
              >
                <option value="excellent">Excelente</option>
                <option value="good">Bueno</option>
                <option value="irregular">Irregular</option>
                <option value="new">Nuevo cliente</option>
              </select>
            </label>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Registrando…
              </>
            ) : (
              <>
                <UserPlus className="h-4 w-4" /> Registrar Cliente
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
            <Users className="h-5 w-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">Clientes Registrados</h2>
          </div>
          <button
            onClick={fetchCustomers}
            disabled={listLoading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 transition-colors hover:border-primary-300 hover:bg-primary-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${listLoading ? 'animate-spin' : ''}`} /> Actualizar
          </button>
        </div>

        {!listLoaded || (listLoading && customers.length === 0) ? (
          <div className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-sm text-gray-500">
            <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
            Cargando clientes desde la base de datos…
          </div>
        ) : customers.length === 0 ? (
          <p className="px-6 py-8 text-center text-sm text-gray-500">No hay clientes registrados.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-[880px] w-full">
              <thead className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-700">
                <tr>
                  <th className="px-4 py-3">Cliente ID</th>
                  <th className="px-4 py-3">Nombre</th>
                  <th className="px-4 py-3">Antigüedad</th>
                  <th className="px-4 py-3">Reclamaciones</th>
                  <th className="px-4 py-3">Riesgo</th>
                  <th className="px-4 py-3 text-right">Detalle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {customers.map((customer) => (
                  <Fragment key={customer.customer_id}>
                    <tr className="cursor-pointer transition-colors hover:bg-gray-50" onClick={() => toggleRow(customer.customer_id)}>
                      <td className="px-4 py-3 font-mono text-xs text-gray-900">{customer.customer_id}</td>
                      <td className="px-4 py-3 text-sm text-gray-800">{customer.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{customer.years_as_customer} años</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{customer.previous_claims}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex rounded-full border border-gray-200 bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                          {customer.risk_profile}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-gray-400">
                        {expandedId === customer.customer_id ? <ChevronUp className="ml-auto h-4 w-4" /> : <ChevronDown className="ml-auto h-4 w-4" />}
                      </td>
                    </tr>

                    {expandedId === customer.customer_id && (
                      <tr className="bg-gray-50">
                        <td colSpan={6} className="border-t border-gray-200 px-4 py-4">
                          {!detail ? (
                            <p className="text-sm text-gray-500">Cargando detalle…</p>
                          ) : (
                            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
                              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                                <h3 className="mb-3 text-sm font-semibold text-gray-900">Ficha del cliente</h3>
                                <div className="space-y-1.5">
                                  <Field label="ID cliente" value={detail.customer_id} />
                                  <Field label="Nombre" value={detail.name} />
                                  <Field label="Antigüedad" value={`${detail.years_as_customer} años`} />
                                  <Field label="Reclamaciones previas" value={detail.previous_claims} />
                                  <Field label="Perfil de riesgo" value={detail.risk_profile} />
                                  <Field label="Historial de pagos" value={detail.payment_history} />
                                </div>
                                {detail.previous_claims_details.length > 0 && (
                                  <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-3">
                                    <span className="text-xs font-medium text-gray-500">Reclamaciones anteriores</span>
                                    <ul className="mt-2 space-y-1 text-xs text-gray-700">
                                      {detail.previous_claims_details.map((claim) => (
                                        <li key={`${claim.year}-${claim.type}`}>
                                          • {claim.year} · {claim.type} · {claim.amount.toLocaleString('es-ES')}€ · <span className="text-gray-500">{claim.status}</span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>

                              <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                                <div className="mb-3 flex items-center gap-1.5">
                                  <FileText className="h-4 w-4 text-primary-600" />
                                  <h3 className="text-sm font-semibold text-gray-900">Pólizas vinculadas</h3>
                                </div>
                                {detail.policies && detail.policies.length > 0 ? (
                                  <ul className="space-y-2 text-sm text-gray-700">
                                    {detail.policies.map((policy) => (
                                      <li key={policy.policy_id} className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
                                        <div className="font-mono text-xs text-gray-900">{policy.policy_id}</div>
                                        <div className="mt-1 text-xs text-gray-600">
                                          {policy.vehicle} · {policy.coverage_type} · {policy.max_coverage.toLocaleString('es-ES')}€
                                        </div>
                                      </li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-sm text-gray-500">Este cliente no tiene pólizas vinculadas.</p>
                                )}
                              </div>
                            </div>
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
