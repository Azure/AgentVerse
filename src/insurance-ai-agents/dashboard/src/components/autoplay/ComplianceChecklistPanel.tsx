import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, Circle, Loader2, Scale, XCircle } from 'lucide-react';

export type RuleStatus = 'pending' | 'checking' | 'passed' | 'warning' | 'failed';

export interface ComplianceRule {
  id: string;
  label: string;
  status: RuleStatus;
  detail?: string;
}

export interface ComplianceChecklistPanelProps {
  active: boolean;
  rules: ComplianceRule[];
  phaseLabel?: string;
}

const COMPLIANCE_WARMING_MESSAGES = [
  'Revisando reglas regulatorias...',
  'Validando límites de cobertura...',
  'Comprobando documentación...',
] as const;

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function getStatusStyles(status: RuleStatus) {
  switch (status) {
    case 'checking':
      return {
        icon: <Loader2 className="h-5 w-5 animate-spin text-primary-600" />,
        row: 'border-primary-200 bg-primary-50',
      };
    case 'passed':
      return {
        icon: <CheckCircle2 className="h-5 w-5 text-emerald-600" />,
        row: 'border-emerald-200 bg-emerald-50',
      };
    case 'warning':
      return {
        icon: <AlertTriangle className="h-5 w-5 text-amber-600" />,
        row: 'border-amber-200 bg-amber-50',
      };
    case 'failed':
      return {
        icon: <XCircle className="h-5 w-5 text-red-600" />,
        row: 'border-red-200 bg-red-50',
      };
    default:
      return {
        icon: <Circle className="h-5 w-5 text-gray-400" />,
        row: 'border-gray-200 bg-gray-50',
      };
  }
}

export default function ComplianceChecklistPanel({
  active,
  rules,
  phaseLabel,
}: ComplianceChecklistPanelProps) {
  const [animatedRuleIds, setAnimatedRuleIds] = useState<string[]>([]);
  const [warmingCheckingCount, setWarmingCheckingCount] = useState(0);
  const [warmingMessageIndex, setWarmingMessageIndex] = useState(0);
  const previousStatusesRef = useRef<Record<string, RuleStatus>>({});
  const timersRef = useRef<number[]>([]);
  const warmingTimersRef = useRef<number[]>([]);
  const allRulesPending = active && rules.length > 0 && rules.every((rule) => rule.status === 'pending');

  useEffect(() => {
    const previousStatuses = previousStatusesRef.current;
    const nextStatuses = Object.fromEntries(rules.map((rule) => [rule.id, rule.status]));

    rules.forEach((rule, index) => {
      const previousStatus = previousStatuses[rule.id];
      if (rule.status === 'pending' || previousStatus === rule.status) return;

      const startTimer = window.setTimeout(() => {
        setAnimatedRuleIds((current) => current.includes(rule.id) ? current : [...current, rule.id]);

        const endTimer = window.setTimeout(() => {
          setAnimatedRuleIds((current) => current.filter((item) => item !== rule.id));
        }, 600);

        timersRef.current.push(endTimer);
      }, active ? index * 140 : 0);

      timersRef.current.push(startTimer);
    });

    previousStatusesRef.current = nextStatuses;
  }, [active, rules]);

  useEffect(() => {
    warmingTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    warmingTimersRef.current = [];

    if (!allRulesPending) {
      setWarmingCheckingCount(0);
      setWarmingMessageIndex(0);
      return;
    }

    setWarmingCheckingCount(1);

    for (let index = 1; index < rules.length; index += 1) {
      const timer = window.setTimeout(() => {
        setWarmingCheckingCount(index + 1);
      }, index * 800);

      warmingTimersRef.current.push(timer);
    }

    const messageInterval = window.setInterval(() => {
      setWarmingMessageIndex((current) => (current + 1) % COMPLIANCE_WARMING_MESSAGES.length);
    }, 1400);

    warmingTimersRef.current.push(messageInterval);

    return () => {
      warmingTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      warmingTimersRef.current = [];
    };
  }, [allRulesPending, rules.length]);

  useEffect(() => () => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    warmingTimersRef.current.forEach((timer) => window.clearTimeout(timer));
  }, []);

  return (
    <section className="rounded-[28px] border border-gray-200 bg-white p-6 shadow-xl shadow-gray-200/60">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-gray-200 bg-gray-50 text-gray-700">
          <Scale className="h-5 w-5" />
        </div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-gray-500">Compliance agent</p>
          <h3 className="text-lg font-semibold text-gray-900">Validación de cumplimiento</h3>
          {phaseLabel ? <p className="mt-1 text-xs text-gray-500">{phaseLabel}</p> : null}
        </div>
      </div>

      <div className="space-y-3">
        {allRulesPending ? (
          <div className="rounded-xl border border-primary-200 bg-primary-50 px-4 py-3 text-xs font-medium text-gray-700 transition-opacity duration-300">
            {COMPLIANCE_WARMING_MESSAGES[warmingMessageIndex]}
          </div>
        ) : null}

        {rules.map((rule, index) => {
          const visualStatus: RuleStatus = allRulesPending && index < warmingCheckingCount ? 'checking' : rule.status;
          const statusStyles = getStatusStyles(visualStatus);
          const shouldPulse = animatedRuleIds.includes(rule.id);

          return (
            <div
              key={rule.id}
              className={cx(
                'flex items-center gap-4 rounded-xl border p-4 transition-colors duration-300',
                statusStyles.row,
                visualStatus === 'pending' && 'text-gray-500',
                visualStatus === 'checking' && active && 'shadow-md shadow-primary-100/60',
              )}
              style={shouldPulse ? { animation: 'pulseRow 0.6s ease-out both' } : undefined}
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-gray-200 bg-white">
                {statusStyles.icon}
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-base font-medium text-gray-900">{rule.label}</p>
                {rule.detail ? <p className="mt-1 text-xs text-gray-500">{rule.detail}</p> : null}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
