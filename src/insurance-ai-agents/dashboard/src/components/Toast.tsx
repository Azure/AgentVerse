import { useEffect, useState } from 'react';
import { AlertTriangle, ShieldAlert, X } from 'lucide-react';
import type { SecurityIncident } from '../api';

interface ToastProps {
  incident: SecurityIncident;
  onClose: () => void;
  onClick?: () => void;
}

const SEVERITY_STYLES: Record<string, { badge: string; icon: string }> = {
  critical: { badge: 'bg-red-50 text-red-800 border-red-200', icon: 'text-red-600' },
  high: { badge: 'bg-red-50 text-red-700 border-red-200', icon: 'text-red-500' },
  medium: { badge: 'bg-amber-50 text-amber-800 border-amber-200', icon: 'text-amber-600' },
  low: { badge: 'bg-amber-50 text-amber-700 border-amber-200', icon: 'text-amber-500' },
};

const TYPE_LABEL: Record<string, string> = {
  prompt_injection: 'Intento de manipulación',
  fraud_suspected: 'Posible fraude detectado',
};

export default function Toast({ incident, onClose, onClick }: ToastProps) {
  const [visible, setVisible] = useState(false);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    const timeout = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(timeout);
  }, []);

  const handleClose = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setClosing(true);
    setTimeout(onClose, 300);
  };

  const style = SEVERITY_STYLES[incident.severity] ?? SEVERITY_STYLES.medium;
  const isInjection = incident.incident_type === 'prompt_injection';
  const Icon = isInjection ? ShieldAlert : AlertTriangle;
  const label = TYPE_LABEL[incident.incident_type] ?? incident.incident_type;

  return (
    <div
      onClick={onClick}
      className={`
        w-80 cursor-pointer rounded-lg border border-red-300 bg-white p-4 shadow-lg
        transform transition-all duration-300 ease-out
        ${visible && !closing ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
      `}
    >
      <div className="flex items-start gap-3">
        <div className={`shrink-0 ${style.icon} animate-pulse`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center justify-between gap-2">
            <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.badge}`}>
              {label}
            </span>
            <button
              onClick={handleClose}
              className="text-gray-400 transition-colors hover:text-gray-700"
              aria-label="Cerrar"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <p className="mb-1 font-mono text-sm text-gray-900">{incident.claim_id}</p>
          <p className="line-clamp-2 text-xs leading-snug text-gray-600">{incident.description}</p>
          <p className="mt-2 text-[10px] text-gray-500">Click para ver en Seguridad →</p>
        </div>
      </div>
    </div>
  );
}
