import { Clock, CheckCircle2, XCircle, FileSearch, ShieldAlert, Scale, Gavel } from 'lucide-react';
import type { ClaimResult, AuditEntry } from '../api';

interface Props {
  result: ClaimResult;
}

const stageIcons: Record<string, typeof FileSearch> = {
  intake: FileSearch,
  risk_assessment: ShieldAlert,
  compliance: Scale,
  decision: Gavel,
};

const stageLabels: Record<string, string> = {
  intake: 'Claims Intake Agent',
  risk_assessment: 'Risk & Fraud Agent',
  compliance: 'Compliance Agent',
  decision: 'Decisión Final',
};

export default function AuditTrail({ result }: Props) {
  const metadata = (result as ClaimResult & {
    metadata?: { model?: string; pipeline_version?: string };
  }).metadata;
  const model = typeof metadata?.model === 'string' ? metadata.model : 'gpt-5.4-mini';
  const pipelineVersion = typeof metadata?.pipeline_version === 'string' ? metadata.pipeline_version : '1.0.0';

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium uppercase tracking-wider text-gray-600">Audit Trail</h3>
        <span className="text-xs text-gray-500">ID: {result.claim_id}</span>
      </div>

      <div className="space-y-1">
        {result.audit_trail.map((entry: AuditEntry, i: number) => {
          const Icon = stageIcons[entry.stage] || Clock;
          const isCompleted = entry.status === 'completed';
          const TimelineIcon = isCompleted ? CheckCircle2 : XCircle;

          return (
            <div key={i} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div
                  className={[
                    'flex h-7 w-7 items-center justify-center rounded-full',
                    isCompleted ? 'bg-gray-300 text-gray-700' : 'bg-primary-500 text-white',
                  ].join(' ')}
                >
                  <TimelineIcon className="h-4 w-4" />
                </div>
                {i < result.audit_trail.length - 1 && <div className="my-1 w-px flex-1 bg-gray-200" />}
              </div>

              <div className="flex-1 pb-4">
                <div className="flex items-center gap-2">
                  <Icon className="h-3.5 w-3.5 text-primary-600" />
                  <span className="text-sm font-medium text-gray-800">{stageLabels[entry.stage] || entry.stage}</span>
                  <span className="ml-auto text-[10px] text-gray-500">{entry.duration_ms}ms</span>
                </div>
                <p className="mt-1 text-xs text-gray-600">{entry.result_summary}</p>
                <p className="mt-0.5 text-[10px] text-gray-500">{new Date(entry.timestamp).toLocaleTimeString('es-ES')}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 border-t border-gray-200 pt-4">
        <h4 className="mb-2 text-[10px] uppercase text-gray-500">Metadata</h4>
        <div className="grid grid-cols-1 gap-2 text-[11px] text-gray-700 sm:grid-cols-2">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <span className="text-gray-500">Modelo: </span>
            <span>{model}</span>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <span className="text-gray-500">Pipeline: </span>
            <span>{pipelineVersion}</span>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <span className="text-gray-500">Duración total: </span>
            <span>{result.total_duration_ms}ms</span>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
            <span className="text-gray-500">Timestamp: </span>
            <span>{new Date(result.timestamp).toLocaleString('es-ES')}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
