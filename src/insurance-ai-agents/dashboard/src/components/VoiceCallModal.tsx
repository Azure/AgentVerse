import { useEffect, useRef, useState } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Loader2, CheckCircle2, AlertTriangle, Music, ScanEye } from 'lucide-react';
import { VoiceAudioClient, type VoiceEvent } from '../voice/audioClient';
import { BRAND } from '../brand';

type Line = { who: 'user' | 'assistant' | 'system'; text: string; ts: number };

function buildWsBase(): string {
  // Same resolution rule as connectWebSocket() in api.ts so we work
  // whether or not VITE_API_URL is set (dev = empty + same origin).
  const apiBase = import.meta.env.VITE_API_URL || '';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = apiBase ? new URL(apiBase).host : window.location.host;
  return `${proto}//${host}`;
}

function newSessionId() {
  return `voice-${Math.random().toString(36).slice(2, 10)}-${Date.now().toString(36)}`;
}

export default function VoiceCallModal({
  open,
  onClose,
  sessionId: externalSessionId,
  onSessionStarted,
  zClassName,
}: {
  open: boolean;
  onClose: () => void;
  /** Optional pre-allocated session id so external windows (e.g. the
   *  operator view) can attach to the same call. If omitted, a fresh id
   *  is generated for each open. */
  sessionId?: string;
  /** Fired once the underlying VoiceAudioClient is created with the
   *  resolved session id. Useful when the parent generates the id
   *  externally OR when it wants to know which id the modal chose. */
  onSessionStarted?: (sessionId: string) => void;
  /** Tailwind z-index class so the modal can be raised above other
   *  modals (e.g. the auto-demo at z-[140]). Default: z-[80]. */
  zClassName?: string;
}) {
  const [status, setStatus] = useState<'idle' | 'connecting' | 'live' | 'closed' | 'error'>('idle');
  const [muted, setMuted] = useState(false);
  const [holdMusic, setHoldMusic] = useState(false);
  const [lines, setLines] = useState<Line[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Sesión efectiva tras resolver la pre-allocated o generar una nueva.
  // Se expone como estado para que el botón de "vista de operario" pueda
  // abrir window.open con la id correcta.
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const operatorWindowRef = useRef<Window | null>(null);
  const clientRef = useRef<VoiceAudioClient | null>(null);
  const assistantBufferRef = useRef('');
  const scrollerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    let active = true;
    const sessionId = externalSessionId || newSessionId();
    const client = new VoiceAudioClient(sessionId, buildWsBase());
    clientRef.current = client;
    assistantBufferRef.current = '';
    setLines([{ who: 'system', text: 'Conectando con el asistente...', ts: Date.now() }]);
    setStatus('connecting');
    setError(null);
    setActiveSessionId(sessionId);
    onSessionStarted?.(sessionId);

    const unsubscribe = client.on((e: VoiceEvent) => {
      if (!active) return;
      switch (e.type) {
        case 'connected':
          setStatus('live');
          setLines((p) => [...p, { who: 'system', text: 'Conectado. Puede empezar a hablar.', ts: Date.now() }]);
          break;
        case 'transcript.user':
          if (e.text.trim()) setLines((p) => [...p, { who: 'user', text: e.text, ts: Date.now() }]);
          break;
        case 'transcript.assistant.delta':
          assistantBufferRef.current += e.text;
          break;
        case 'transcript.assistant.done': {
          const full = e.text || assistantBufferRef.current;
          assistantBufferRef.current = '';
          if (full.trim()) setLines((p) => [...p, { who: 'assistant', text: full.trim(), ts: Date.now() }]);
          break;
        }
        case 'tool.result':
          if (e.name === 'lookup_customer') {
            const r = e.result as { found?: boolean; name?: string };
            setLines((p) => [...p, {
              who: 'system',
              text: r?.found ? `Cliente encontrado: ${r.name}` : 'DNI no encontrado',
              ts: Date.now(),
            }]);
          } else if (e.name === 'submit_claim') {
            const r = e.result as { decision?: string; claim_id?: string };
            setLines((p) => [...p, {
              who: 'system',
              text: `Pipeline ejecutado: ${r?.decision ?? '?'} (${r?.claim_id ?? '?'})`,
              ts: Date.now(),
            }]);
          }
          break;
        case 'hold_music_start':
          setHoldMusic(true);
          break;
        case 'hold_music_stop':
          setHoldMusic(false);
          break;
        case 'hangup':
          // Server-driven close: agent finished its goodbye and asked us to
          // hang up. Wait for the local playback queue to drain (the audio
          // server sends arrives in advance of being heard) before truly
          // closing, so the last sentence is never cut off.
          setLines((p) => [...p, { who: 'system', text: 'Llamada finalizada por el asistente', ts: Date.now() }]);
          setStatus('closed');
          {
            const drainAndClose = () => {
              const remaining = clientRef.current?.remainingPlaybackSec() ?? 0;
              // Add 600 ms buffer so the speaker really finishes the last
              // syllable + the natural reverb tail before we close.
              const waitMs = Math.max(800, remaining * 1000 + 600);
              setTimeout(() => {
                clientRef.current?.stop().catch(() => undefined);
                onClose();
              }, waitMs);
            };
            drainAndClose();
          }
          break;
        case 'error':
          setError(e.message);
          setStatus('error');
          break;
        case 'closed':
          setStatus('closed');
          break;
        default:
          break;
      }
    });

    client.start().catch((err) => {
      setStatus('error');
      setError((err as Error).message);
    });

    return () => {
      active = false;
      unsubscribe();
      client.stop().catch(() => undefined);
      clientRef.current = null;
      setActiveSessionId(null);
      // Si la ventana del operador estaba abierta para esta sesión, la
      // cerramos: la sesión ya no existe en el backend, así que dejarla
      // viva sólo mostraría un error "sesión no encontrada".
      if (operatorWindowRef.current && !operatorWindowRef.current.closed) {
        try {
          operatorWindowRef.current.close();
        } catch {
          /* ignore */
        }
      }
      operatorWindowRef.current = null;
    };
  }, [open, externalSessionId]);

  useEffect(() => {
    if (scrollerRef.current) scrollerRef.current.scrollTop = scrollerRef.current.scrollHeight;
  }, [lines.length, holdMusic]);

  const handleHangup = () => {
    clientRef.current?.stop().catch(() => undefined);
    onClose();
  };

  const openOperatorView = () => {
    if (!activeSessionId) return;
    // Si ya hay una ventana de operador abierta para esta sesión,
    // simplemente la enfocamos en vez de abrir un duplicado.
    if (operatorWindowRef.current && !operatorWindowRef.current.closed) {
      try {
        operatorWindowRef.current.focus();
        return;
      } catch {
        /* fallthrough — fall back to opening a fresh one */
      }
    }
    const url = `${window.location.origin}/?view=voice-operator&session=${encodeURIComponent(activeSessionId)}`;
    try {
      operatorWindowRef.current = window.open(
        url,
        `operator-${activeSessionId}`,
        'width=1280,height=820',
      );
    } catch {
      operatorWindowRef.current = null;
    }
  };

  const toggleMute = () => {
    // We cannot truly mute the upstream send without disconnecting, but we
    // can ignore the local mic processor by short-circuiting in audioClient.
    // For the demo, the UI just records muted state. Real mute would need
    // pausing the AudioContext or a flag in audioClient.
    setMuted((m) => !m);
  };

  if (!open) return null;

  return (
    <div className={`fixed inset-0 ${zClassName ?? 'z-[80]'} flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm`}>
      <div className="w-full max-w-2xl overflow-hidden rounded-3xl bg-white shadow-2xl">
        {/* Header */}
        <header className="flex items-center justify-between bg-gradient-to-r from-primary-600 to-primary-700 px-6 py-4 text-white">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-full bg-white/20">
              <Phone className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold">Asistente de voz · {BRAND.voiceAssistantName}</p>
              <p className="text-xs opacity-80">
                {status === 'connecting' && 'Conectando...'}
                {status === 'live' && 'En llamada'}
                {status === 'closed' && 'Llamada finalizada'}
                {status === 'error' && 'Error'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleHangup}
            className="inline-flex items-center gap-2 rounded-full bg-red-500 px-4 py-2 text-sm font-semibold hover:bg-red-600"
          >
            <PhoneOff className="h-4 w-4" />
            Colgar
          </button>
        </header>

        {/* Body */}
        <div className="flex h-[420px] flex-col">
          <div ref={scrollerRef} className="flex-1 space-y-3 overflow-y-auto bg-gray-50 p-4">
            {lines.map((l, i) => (
              <Bubble key={`${l.ts}-${i}`} line={l} />
            ))}
            {holdMusic && (
              <div className="flex items-center gap-3 rounded-2xl border border-primary-200 bg-primary-50 px-4 py-3">
                <Music className="h-5 w-5 animate-pulse text-primary-600" />
                <div>
                  <p className="text-sm font-semibold text-primary-700">Procesando su parte...</p>
                  <p className="text-xs text-gray-600">Los agentes IA están evaluando su caso. Por favor espere.</p>
                </div>
                <Loader2 className="ml-auto h-4 w-4 animate-spin text-primary-600" />
              </div>
            )}
            {error && (
              <div className="flex items-start gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between border-t border-gray-200 bg-white px-6 py-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={toggleMute}
                disabled={status !== 'live'}
                className={`grid h-11 w-11 place-items-center rounded-full text-white transition-colors ${
                  muted ? 'bg-red-500 hover:bg-red-600' : 'bg-primary-600 hover:bg-primary-700'
                } disabled:opacity-50`}
                title={muted ? 'Activar micrófono' : 'Silenciar'}
              >
                {muted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
              </button>
              <div className="text-xs text-gray-500">
                {status === 'live' ? (
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" /> Micrófono activo
                  </span>
                ) : (
                  <span>{status === 'connecting' ? 'Conectando…' : 'Sin conexión'}</span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              <span>Cifrado · Azure OpenAI gpt-realtime-mini</span>
              <button
                type="button"
                onClick={openOperatorView}
                disabled={!activeSessionId || status === 'idle' || status === 'closed'}
                title="Abrir vista de operario en una nueva ventana"
                aria-label="Abrir vista de operario"
                className="ml-1 grid h-6 w-6 place-items-center rounded-full text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-gray-400"
              >
                <ScanEye className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Bubble({ line }: { line: Line }) {
  if (line.who === 'system') {
    return (
      <div className="mx-auto max-w-xl rounded-full bg-gray-200 px-3 py-1 text-center text-[11px] uppercase tracking-wide text-gray-600">
        {line.text}
      </div>
    );
  }
  const isUser = line.who === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm leading-relaxed shadow-sm ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-white text-gray-800 ring-1 ring-gray-200'
        }`}
      >
        {!isUser && <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary-600">{BRAND.voiceAssistantName}</p>}
        {line.text}
      </div>
    </div>
  );
}
