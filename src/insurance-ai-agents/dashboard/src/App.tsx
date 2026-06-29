import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { Activity, UserCircle, ClipboardList, BarChart3, ScrollText, Users, ShieldAlert, Award, LogIn, LogOut, Sparkles, PlayCircle } from 'lucide-react';
import ClaimForm from './components/ClaimForm';
import Pipeline from './components/Pipeline';
import DecisionPanel from './components/DecisionPanel';
import AuditTrail from './components/AuditTrail';
import ActivityFeed from './components/ActivityFeed';
import OperatorView from './components/OperatorView';
import StatsView from './components/StatsView';
import PolicyView from './components/PolicyView';
import CustomerView from './components/CustomerView';
import SecurityView from './components/SecurityView';
import HeroView from './components/HeroView';
import { GovernanceView } from './components/GovernanceView';
import AutoPlayDemo from './components/AutoPlayDemo';
import Toast from './components/Toast';
import VoiceCallButton from './components/VoiceCallButton';
import { BRAND } from './brand';
import type { ActivityEvent } from './components/ActivityFeed';
import type { ClaimRequest, ClaimResult, PipelineUpdate, SecurityIncident } from './api';
import { evaluateClaim, connectWebSocket, getSecurityIncidents } from './api';
import { useAuth } from './auth/useAuth';

type Stage = 'intake' | 'risk_assessment' | 'compliance' | 'decision';
type StageStatus = 'pending' | 'processing' | 'completed' | 'failed';
type Tab = 'inicio' | 'cliente' | 'operario' | 'estadisticas' | 'clientes' | 'polizas' | 'seguridad' | 'gobernanza';

const EMPTY_STAGE_STATUSES: Record<Stage, StageStatus> = {
  intake: 'pending',
  risk_assessment: 'pending',
  compliance: 'pending',
  decision: 'pending',
};

const EMPTY_STAGE_TOKENS: Record<Stage, string> = {
  intake: '',
  risk_assessment: '',
  compliance: '',
  decision: '',
};

function isStage(value: string): value is Stage {
  return value in EMPTY_STAGE_STATUSES;
}

function mapStreamingAgentToStage(agent: string): Stage | null {
  if (agent === 'risk') return 'risk_assessment';
  return isStage(agent) ? agent : null;
}

type TabDef = { id: Tab; label: string; icon: React.ElementType; role: 'customer' | 'operator' };

const ALL_TABS: TabDef[] = [
  { id: 'inicio',       label: 'Inicio',       icon: Sparkles,     role: 'operator' },
  { id: 'cliente',      label: 'Cliente',      icon: UserCircle,   role: 'customer' },
  { id: 'operario',     label: 'Operario',     icon: ClipboardList, role: 'operator' },
  { id: 'estadisticas', label: 'Estadísticas', icon: BarChart3,    role: 'operator' },
  { id: 'clientes',     label: 'Clientes',     icon: Users,        role: 'operator' },
  { id: 'polizas',      label: 'Pólizas',      icon: ScrollText,   role: 'operator' },
  { id: 'seguridad',    label: 'Seguridad',    icon: ShieldAlert,  role: 'operator' },
  { id: 'gobernanza',   label: 'Gobernanza',   icon: Award,        role: 'operator' },
];

export default function App() {
  const auth = useAuth();

  // Filtra tabs por viewMode (en modo customer sólo mostramos Cliente)
  const tabs = useMemo<TabDef[]>(
    () => ALL_TABS.filter(t => auth.viewMode === 'operator' ? true : t.role === 'customer'),
    [auth.viewMode]
  );

  const defaultTab: Tab = auth.viewMode === 'operator' ? 'inicio' : 'cliente';
  const [activeTab, setActiveTab] = useState<Tab>(defaultTab);
  const [autoplayOpen, setAutoplayOpen] = useState(false);

  useEffect(() => {
    setActiveTab(defaultTab);
  }, [defaultTab]);

  useEffect(() => {
    if (!tabs.some(t => t.id === activeTab)) {
      setActiveTab(defaultTab);
    }
  }, [tabs, activeTab, defaultTab]);

  const [stageStatuses, setStageStatuses] = useState<Record<Stage, StageStatus>>(EMPTY_STAGE_STATUSES);
  const [stageTokens, setStageTokens] = useState<Record<Stage, string>>(EMPTY_STAGE_TOKENS);
  const [stageData, setStageData] = useState<Partial<Record<Stage, Record<string, unknown>>>>({});
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([]);
  const [result, setResult] = useState<ClaimResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ── Security incidents polling: badge counter + toast notifications ──
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);
  const [seenIds, setSeenIds] = useState<Set<string>>(() => {
    try {
      const raw = localStorage.getItem('security_seen_ids');
      return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch { return new Set(); }
  });
  const [toasts, setToasts] = useState<{ key: string; incident: SecurityIncident }[]>([]);
  const knownIdsRef = useRef<Set<string>>(new Set());
  const initializedRef = useRef(false);

  const incidentKey = (i: SecurityIncident) => `${i.claim_id}-${i.detected_at}`;

  useEffect(() => {
    if (!auth.isOperator) return; // sólo el operario ve incidentes
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await getSecurityIncidents();
        if (cancelled) return;
        const newToasts: { key: string; incident: SecurityIncident }[] = [];
        for (const inc of res.incidents) {
          const id = incidentKey(inc);
          if (!knownIdsRef.current.has(id)) {
            knownIdsRef.current.add(id);
            // Skip toasts on the very first poll (avoid flooding on app load)
            if (initializedRef.current) {
              newToasts.push({ key: `toast-${id}-${Date.now()}`, incident: inc });
            }
          }
        }
        if (newToasts.length > 0) {
          setToasts(prev => [...prev, ...newToasts]);
        }
        setIncidents(res.incidents);
        initializedRef.current = true;
      } catch { /* silent */ }
    };
    poll();
    const interval = setInterval(poll, 4000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [auth.isOperator]);

  // Auto-dismiss toasts after 7s
  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map(t =>
      setTimeout(() => setToasts(prev => prev.filter(x => x.key !== t.key)), 7000)
    );
    return () => timers.forEach(clearTimeout);
  }, [toasts]);

  // Mark all incidents as seen when the user enters the Security tab
  useEffect(() => {
    if (activeTab === 'seguridad' && incidents.length > 0) {
      const ids = incidents.map(incidentKey);
      const next = new Set(ids);
      setSeenIds(next);
      try { localStorage.setItem('security_seen_ids', JSON.stringify(ids)); } catch { /* ignore */ }
    }
  }, [activeTab, incidents]);

  const newIncidentCount = incidents.filter(i => !seenIds.has(incidentKey(i))).length;

  const resetPipeline = useCallback(() => {
    setStageStatuses({ ...EMPTY_STAGE_STATUSES });
    setStageTokens({ ...EMPTY_STAGE_TOKENS });
    setStageData({});
    setActivityEvents([]);
    setResult(null);
    setError('');
  }, []);

  const handleSubmit = useCallback(async (req: ClaimRequest) => {
    resetPipeline();
    setLoading(true);

    // Generate claim ID shared between WebSocket and REST call
    const claimId = `CLM-${crypto.randomUUID().substring(0, 8).toUpperCase()}`;

    // Connect WebSocket FIRST for real-time stage updates
    const { ws, ready } = connectWebSocket(claimId, (update: PipelineUpdate) => {
      if (update.type === 'progress') {
        if (!isStage(update.stage)) return;

        const stage = update.stage;
        const status: StageStatus = update.status === 'completed'
          ? 'completed'
          : update.status === 'processing'
            ? 'processing'
            : 'failed';

        if (status === 'processing') {
          setStageTokens(prev => ({ ...prev, [stage]: '' }));
        }

        setStageStatuses(prev => ({ ...prev, [stage]: status }));
        if (Object.keys(update.data).length > 0) {
          setStageData(prev => ({ ...prev, [stage]: update.data }));
        }
        setActivityEvents(prev => [...prev, {
          stage: update.stage,
          status: update.status,
          timestamp: update.timestamp || new Date().toISOString(),
          data: update.data,
        }]);
        return;
      }

      if (update.type === 'token') {
        const stage = mapStreamingAgentToStage(update.agent);
        if (!stage) return;
        setStageTokens(prev => ({
          ...prev,
          [stage]: `${prev[stage]}${update.text}`,
        }));
      }
    });

    try {
      // Wait for WebSocket to be ready before sending the HTTP request
      await ready;
      // Send claim_id so backend uses the same ID as the WebSocket
      const res = await evaluateClaim({ ...req, claim_id: claimId });
      setResult(res);
      setStageData(prev => ({
        ...prev,
        decision: {
          decision: res.decision,
          confidence: res.confidence,
          reasoning: res.reasoning,
        },
      }));
      // Ensure all stages show completed (WebSocket may have already set most)
      setStageStatuses(prev => ({ ...prev, decision: 'completed' }));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
      ws.close();
    }
  }, [resetPipeline]);

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white/95 backdrop-blur-sm sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img
              src={BRAND.logoUrl}
              alt={BRAND.logoAlt}
              className="h-10 w-auto"
            />
            {!BRAND.logoHasWordmark && (
              <span className="text-lg font-bold tracking-tight text-gray-900">{BRAND.name}</span>
            )}
            <div className="hidden md:block h-10 w-px bg-gray-200" />
            <div className="hidden md:block">
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">
                {BRAND.productName} <span className="text-primary-600">{BRAND.productNameAccent}</span>
              </h1>
              <p className="text-xs text-gray-500">Multi-Agent Decision Platform · Governed &amp; Auditable</p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-600">
            <Activity className="w-3.5 h-3.5 text-green-600" />
            <span>Pipeline Active</span>
            <span className="mx-2 text-gray-300">|</span>
            <span>v1.0.0</span>
            {auth.isOperator && auth.authenticated && (
              <>
                <span className="mx-2 text-gray-300">|</span>
                <button
                  onClick={() => setAutoplayOpen(true)}
                  className="inline-flex items-center gap-1.5 rounded-md bg-primary-600 px-3 py-1.5 text-white shadow-sm shadow-primary-900/20 transition hover:bg-primary-700"
                >
                  <PlayCircle size={14} />
                  <span>Demo automática</span>
                </button>
              </>
            )}
            {auth.enabled && (
              <>
                <span className="mx-2 text-gray-300">|</span>
                {auth.authenticated && auth.account ? (
                  <>
                    {auth.isCustomer && auth.isOperator && (
                      <div className="flex items-center gap-1 mr-2 rounded-md bg-gray-100 p-0.5 border border-gray-200">
                        <button
                          onClick={() => auth.setViewMode('customer')}
                          className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                            auth.viewMode === 'customer' ? 'bg-primary-600 text-white' : 'text-gray-600 hover:text-gray-900'
                          }`}
                        >Cliente</button>
                        <button
                          onClick={() => auth.setViewMode('operator')}
                          className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                            auth.viewMode === 'operator' ? 'bg-primary-600 text-white' : 'text-gray-600 hover:text-gray-900'
                          }`}
                        >Operario</button>
                      </div>
                    )}
                    <span className="text-gray-700 hidden sm:inline" title={auth.account.username}>
                      {auth.account.name || auth.account.username}
                    </span>
                    <button
                      onClick={() => auth.logout()}
                      className="flex items-center gap-1 px-2 py-1 rounded text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors"
                      title="Cerrar sesión"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => auth.login()}
                    className="flex items-center gap-1 px-3 py-1 rounded bg-primary-600 hover:bg-primary-700 text-white transition-colors"
                  >
                    <LogIn className="w-3.5 h-3.5" />
                    <span>Iniciar sesión</span>
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Tab Bar */}
        <div className="max-w-7xl mx-auto px-6">
          <nav className="flex gap-1 -mb-px">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`relative flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === id
                    ? 'border-primary-600 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-900 hover:border-gray-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
                {id === 'seguridad' && newIncidentCount > 0 && (
                  <span className="ml-1 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1.5 rounded-full text-[10px] font-bold bg-primary-600 text-white shadow-sm shadow-primary-600/30 animate-pulse">
                    {newIncidentCount > 99 ? '99+' : newIncidentCount}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Login gate cuando AUTH_ENABLED y no autenticado */}
        {auth.enabled && !auth.authenticated && (
          <div className="max-w-md mx-auto mt-12 p-8 rounded-xl border border-gray-200 bg-white shadow-md text-center">
            <img src={BRAND.logoUrl} alt={BRAND.logoAlt} className="h-12 w-auto mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Acceso restringido</h2>
            <p className="text-sm text-gray-600 mb-6">Inicia sesión con tu cuenta corporativa para acceder a la plataforma.</p>
            <button
              onClick={() => auth.login()}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition-colors"
            >
              <LogIn className="w-4 h-4" />
              Iniciar sesión con Microsoft Entra
            </button>
          </div>
        )}

        {auth.enabled && auth.authenticated && !auth.isCustomer && !auth.isOperator && (
          <div className="max-w-md mx-auto mt-12 p-8 rounded-xl border border-amber-300 bg-amber-50 text-center shadow-sm">
            <ShieldAlert className="w-12 h-12 mx-auto text-amber-600 mb-4" />
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Sin permisos</h2>
            <p className="text-sm text-gray-700">Tu cuenta no tiene asignados los roles <code className="text-amber-700 font-mono">Customer.Submit</code> ni <code className="text-amber-700 font-mono">Operator.Review</code>. Solicita acceso al administrador del tenant.</p>
          </div>
        )}

        {(!auth.enabled || (auth.authenticated && (auth.isCustomer || auth.isOperator))) && <>
        {activeTab === 'inicio' && <HeroView onCTAClick={() => setActiveTab('cliente')} />}

        {/* ── Cliente View ── */}
        {activeTab === 'cliente' && (
          <>
            <section>
              <ClaimForm onSubmit={handleSubmit} loading={loading} />
            </section>

            {(loading || result) && (
              <section className="animate-slide-in">
                <Pipeline statuses={stageStatuses} tokens={stageTokens} stageData={stageData} />
              </section>
            )}

            {activityEvents.length > 0 && (
              <section>
                <ActivityFeed events={activityEvents} />
              </section>
            )}

            {error && (
              <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700">
                <strong>Error:</strong> {error}
              </div>
            )}

            {result && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-slide-in">
                <DecisionPanel result={result} />
                <AuditTrail result={result} />
              </div>
            )}
          </>
        )}

        {/* ── Operario View ── */}
        {activeTab === 'operario' && <OperatorView />}

        {/* ── Estadísticas View ── */}
        {activeTab === 'estadisticas' && <StatsView />}

        {/* ── Clientes View ── */}
        {activeTab === 'clientes' && <CustomerView />}

        {/* ── Pólizas View ── */}
        {activeTab === 'polizas' && <PolicyView />}

        {/* ── Seguridad View ── */}
        {activeTab === 'seguridad' && <SecurityView />}

        {/* ── Gobernanza View ── */}
        {activeTab === 'gobernanza' && <GovernanceView />}
        </>}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12 py-6 text-center text-xs text-gray-500">
        Powered by Microsoft Agent Framework • Azure AI Foundry • Governed by GitHub • Secured by APIM AI Gateway
      </footer>

      {/* Toast notifications (bottom-right) */}
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none">
        {toasts.map(t => (
          <div key={t.key} className="pointer-events-auto">
            <Toast
              incident={t.incident}
              onClose={() => setToasts(prev => prev.filter(x => x.key !== t.key))}
              onClick={() => {
                setActiveTab('seguridad');
                setToasts(prev => prev.filter(x => x.key !== t.key));
              }}
            />
          </div>
        ))}
      </div>

      <AutoPlayDemo open={autoplayOpen} onClose={() => setAutoplayOpen(false)} />
      <VoiceCallButton />
    </div>
  );
}
