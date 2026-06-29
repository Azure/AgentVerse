import { useState, useEffect } from 'react';
import {
  Shield,
  GitBranch,
  CheckCircle2,
  XCircle,
  Award,
  Cpu,
  FileCheck,
  Lock,
  AlertTriangle,
  Activity,
  Users,
} from 'lucide-react';
import { getGovernanceStatus } from '../api';
import type { GovernanceStatus } from '../api';

function Pill({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${
        ok ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'
      }`}
    >
      {ok ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      {children}
    </span>
  );
}

export function GovernanceView() {
  const [data, setData] = useState<GovernanceStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchOnce = async () => {
      try {
        const response = await getGovernanceStatus();
        if (!cancelled) {
          setData(response);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Error');
      }
    };

    fetchOnce();
    const id = setInterval(fetchOnce, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <AlertTriangle className="mr-2 inline h-5 w-5" />
          {error}
        </div>
      </div>
    );
  }

  if (!data) {
    return <div className="p-6 text-gray-500">Cargando estado de gobernanza…</div>;
  }

  const apimActive = data.apim.enabled;
  const passRate = data.evals.latest ? Math.round(data.evals.latest.pass_rate * 100) : null;
  const passRateTone = (passRate ?? 0) >= 80 ? 'text-emerald-700' : 'text-red-700';

  return (
    <div className="space-y-6 p-6">
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-primary-200 bg-primary-50 px-3 py-1 text-sm font-medium text-primary-700">
              <Award className="h-4 w-4" />
              Gobernanza & Cumplimiento
            </span>
            <h1 className="mt-3 text-3xl font-bold text-gray-900">Centro de Control AI</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
              Cada llamada a IA atraviesa un AI Gateway con identidad gestionada, content safety y métricas de tokens.
              Cada cambio de prompt pasa por un pipeline de evaluación automática antes de llegar a producción.
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
            <div className="text-xs uppercase tracking-wide text-gray-500">Pipeline</div>
            <div className="font-mono text-lg text-gray-900">v{data.pipeline_version}</div>
            <div className="mt-1 text-xs text-gray-500">commit {data.git_commit}</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-700">
              <Shield className="h-4 w-4 text-primary-600" />
              APIM AI Gateway
            </div>
            <Pill ok={apimActive}>{apimActive ? 'Activo' : 'Modo directo'}</Pill>
          </div>
          <div className="text-2xl font-bold text-gray-900">
            {apimActive ? `${data.apim.policies.filter((policy) => policy.active).length} políticas` : 'Bypass para dev'}
          </div>
          <div className="mt-1 truncate text-xs text-gray-500">{data.apim.gateway_url}</div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-700">
              <FileCheck className="h-4 w-4 text-primary-600" />
              Eval Gate
            </div>
            {passRate !== null ? <Pill ok={passRate >= 80}>{passRate}% pass</Pill> : <span className="text-xs text-gray-500">sin ejecuciones</span>}
          </div>
          <div className={`text-2xl font-bold ${passRate !== null ? passRateTone : 'text-gray-900'}`}>
            {data.evals.latest ? `${data.evals.latest.passed}/${data.evals.latest.total}` : '— / —'}
          </div>
          <div className="mt-1 text-xs text-gray-500">
            {data.evals.latest
              ? `Última ejecución: ${new Date(data.evals.latest.timestamp).toLocaleString()}`
              : 'Aún no se han ejecutado evals'}
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-2 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-700">
              <Cpu className="h-4 w-4 text-primary-600" />
              Modelo
            </div>
            <span className="rounded-full border border-primary-200 bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700">GA</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{data.model}</div>
          <div className="mt-1 text-xs text-gray-500">Azure OpenAI · GlobalStandard</div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900">Políticas activas en el AI Gateway</h2>
          </div>
          <ul className="space-y-2">
            {data.apim.policies.map((policy) => (
              <li key={policy.id} className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm">
                <span className="text-gray-700">{policy.name}</span>
                <Pill ok={policy.active}>{policy.active ? 'on' : 'off'}</Pill>
              </li>
            ))}
          </ul>
          <div className="mt-4 border-t border-gray-200 pt-4 text-xs text-gray-500">
            Definidas en <code className="rounded bg-gray-100 px-1 py-0.5">infra/apim-policy.xml</code> y aplicadas por Bicep al desplegar APIM StandardV2.
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary-600" />
            <h2 className="font-semibold text-gray-900">Pipeline de evaluación</h2>
          </div>
          {data.evals.latest ? (
            <div className="space-y-3">
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-gray-600">Tasa de aprobación</span>
                <span className={`text-3xl font-bold ${passRateTone}`}>{passRate}%</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                  <div className="text-xs text-gray-500">Total</div>
                  <div className="text-lg font-bold text-gray-900">{data.evals.latest.total}</div>
                </div>
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                  <div className="text-xs text-emerald-700">Pasaron</div>
                  <div className="text-lg font-bold text-emerald-700">{data.evals.latest.passed}</div>
                </div>
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <div className="text-xs text-red-700">Fallaron</div>
                  <div className="text-lg font-bold text-red-700">{data.evals.latest.failed}</div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-500">
              Aún no se ha ejecutado el dataset dorado. Ejecuta:
              <pre className="mt-2 rounded-lg border border-gray-200 bg-gray-50 p-2 text-xs text-gray-700">python -m evals.run_evals</pre>
            </div>
          )}
          <div className="mt-4 space-y-1 border-t border-gray-200 pt-4 text-xs text-gray-500">
            <div>
              Dataset: <code className="rounded bg-gray-100 px-1 py-0.5">{data.evals.dataset_path}</code>
            </div>
            <div>
              Workflow: <code className="rounded bg-gray-100 px-1 py-0.5">{data.evals.workflow}</code>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Users className="h-5 w-5 text-primary-600" />
          <h2 className="font-semibold text-gray-900">Propiedad del código (CODEOWNERS)</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs uppercase text-gray-500">
                <th className="py-2 pr-4">Ruta</th>
                <th className="py-2">Equipos responsables</th>
              </tr>
            </thead>
            <tbody>
              {data.code_ownership.map((row, index) => (
                <tr key={index} className="border-b border-gray-100 last:border-0">
                  <td className="py-2 pr-4 font-mono text-xs text-gray-700">{row.path}</td>
                  <td className="py-2">
                    <div className="flex flex-wrap gap-1">
                      {row.owners.map((owner) => (
                        <span
                          key={owner}
                          className="inline-flex rounded-full border border-primary-200 bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700"
                        >
                          {owner}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 text-xs text-gray-500">
          GitHub bloquea automáticamente PRs que tocan estos paths sin aprobación de los equipos correspondientes.
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <Lock className="h-5 w-5 text-primary-600" />
          <h2 className="font-semibold text-gray-900">Checks de proceso & evidencia auditable</h2>
        </div>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {Object.entries(data.checks).map(([key, value]) => (
            <div key={key} className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
              <span className="text-sm text-gray-700">{prettifyCheck(key)}</span>
              <Pill ok={value}>{value ? 'presente' : 'falta'}</Pill>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-center gap-2 text-center text-xs text-gray-500">
        <GitBranch className="h-3 w-3" />
        commit {data.git_commit} · pipeline v{data.pipeline_version} · refrescado {new Date(data.deployed_at).toLocaleTimeString()}
      </div>
    </div>
  );
}

function prettifyCheck(key: string): string {
  const map: Record<string, string> = {
    pull_request_template: 'Plantilla de Pull Request',
    codeowners: 'Archivo CODEOWNERS',
    deploy_workflow: 'Workflow de despliegue por agente',
    eval_workflow: 'Workflow Eval-Gate en PRs',
    infra_as_code: 'Infraestructura como código (Bicep)',
    apim_policy_xml: 'Política XML del AI Gateway',
  };
  return map[key] || key;
}
