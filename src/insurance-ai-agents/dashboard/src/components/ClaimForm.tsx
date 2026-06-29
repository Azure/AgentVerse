import { useState, useEffect, useRef } from 'react';
import { Send, FileText, Loader2, ImagePlus, X, CheckCircle2, Euro, UserCheck, ShieldAlert, Siren } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ClaimRequest, Scenario } from '../api';
import { getScenarios } from '../api';

interface Props {
  onSubmit: (req: ClaimRequest) => void;
  loading: boolean;
}

const SCENARIO_OPTIONS: Array<{ key: string; label: string; Icon: LucideIcon }> = [
  { key: 'low_risk', label: 'Bajo Riesgo', Icon: CheckCircle2 },
  { key: 'high_amount', label: 'Alto Monto', Icon: Euro },
  { key: 'human_review', label: 'Revisión Humana', Icon: UserCheck },
  { key: 'prompt_injection', label: 'Prompt Injection', Icon: ShieldAlert },
  { key: 'fraudulent', label: 'Fraudulento', Icon: Siren },
];

export default function ClaimForm({ onSubmit, loading }: Props) {
  const [scenarios, setScenarios] = useState<Record<string, Scenario>>({});
  const [scenariosLoaded, setScenariosLoaded] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [form, setForm] = useState<ClaimRequest>({
    policy_id: '',
    customer_id: '',
    incident_type: 'collision',
    description: '',
    estimated_amount: 0,
  });
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getScenarios()
      .then((data) => {
        setScenarios(data);
      })
      .catch(() => {})
      .finally(() => setScenariosLoaded(true));
  }, []);

  const updateForm = (patch: Partial<ClaimRequest>) => {
    setSelectedScenario(null);
    setForm((current) => ({ ...current, ...patch }));
  };

  const loadScenario = (name: string) => {
    const s = scenarios[name];
    if (!s) return;
    setSelectedScenario(name);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setForm({ ...s });
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setSelectedScenario(null);
      setImagePreview(result);
      const b64 = result.split(',')[1];
      setForm((current) => ({ ...current, image_b64: b64 }));
    };
    reader.readAsDataURL(file);
  };

  const removeImage = () => {
    setSelectedScenario(null);
    setImagePreview(null);
    setForm((current) => {
      const { image_b64: _, ...rest } = current;
      return rest as ClaimRequest;
    });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.policy_id || !form.description) return;
    onSubmit(form);
  };

  const labelClass = 'mb-1.5 block text-sm font-medium text-gray-700';
  const inputClass = 'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200';

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Nuevo Siniestro</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!scenariosLoaded && (
            <span className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.2em] text-gray-400">
              <Loader2 className="h-3 w-3 animate-spin" />
              Cargando escenarios…
            </span>
          )}
          {SCENARIO_OPTIONS.map(({ key, label, Icon }) => {
            const available = !!scenarios[key];
            const isSelected = selectedScenario === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => available && loadScenario(key)}
                disabled={!available}
                aria-disabled={!available}
                title={available ? `Cargar caso: ${label}` : 'Disponible cuando el backend responda'}
                className={[
                  'inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors',
                  !available
                    ? 'cursor-not-allowed border-dashed border-gray-200 bg-gray-50 text-gray-400 opacity-60'
                    : isSelected
                      ? 'border-primary-600 bg-primary-600 text-white shadow-sm'
                      : 'border-gray-200 bg-gray-100 text-gray-800 hover:border-primary-300 hover:bg-primary-50',
                ].join(' ')}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label className={labelClass}>Póliza ID</label>
          <input
            type="text"
            value={form.policy_id}
            onChange={(e) => updateForm({ policy_id: e.target.value })}
            placeholder="POL-2026-001"
            className={inputClass}
            required
          />
        </div>

        <div>
          <label className={labelClass}>Cliente ID</label>
          <input
            type="text"
            value={form.customer_id}
            onChange={(e) => updateForm({ customer_id: e.target.value })}
            placeholder="CUST-1001"
            className={inputClass}
            required
          />
        </div>

        <div>
          <label className={labelClass}>Tipo de Incidente</label>
          <select
            value={form.incident_type}
            onChange={(e) => updateForm({ incident_type: e.target.value })}
            className={inputClass}
          >
            <option value="collision">Colisión</option>
            <option value="theft">Robo</option>
            <option value="fire">Incendio</option>
            <option value="natural_disaster">Desastre Natural</option>
            <option value="vandalism">Vandalismo</option>
            <option value="other">Otro</option>
          </select>
        </div>

        <div>
          <label className={labelClass}>Monto Estimado (€)</label>
          <input
            type="number"
            value={form.estimated_amount || ''}
            onChange={(e) => updateForm({ estimated_amount: parseFloat(e.target.value) || 0 })}
            placeholder="2500"
            min="1"
            className={inputClass}
            required
          />
        </div>

        <div className="md:col-span-2">
          <label className={labelClass}>Descripción del Siniestro</label>
          <textarea
            value={form.description}
            onChange={(e) => updateForm({ description: e.target.value })}
            placeholder="Describe los hechos del siniestro..."
            rows={4}
            className={`${inputClass} resize-none`}
            required
          />
        </div>

        <div className="md:col-span-2">
          <label className={labelClass}>Imagen del Siniestro (opcional)</label>
          <div className="flex items-center gap-4">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              className="hidden"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-100 px-4 py-2 text-sm text-gray-800 transition-colors hover:border-primary-300 hover:bg-primary-50"
            >
              <ImagePlus className="h-4 w-4" />
              Adjuntar Imagen
            </button>
            {imagePreview && (
              <div className="relative">
                <img
                  src={imagePreview}
                  alt="Preview"
                  className="h-16 w-16 rounded-lg border border-gray-200 object-cover"
                />
                <button
                  type="button"
                  onClick={removeImage}
                  className="absolute -right-2 -top-2 rounded-full bg-red-600 p-0.5 text-white transition-colors hover:bg-red-700"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="md:col-span-2">
          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-6 py-3 font-medium text-white shadow-md transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Procesando Siniestro...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" /> Evaluar Siniestro
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
