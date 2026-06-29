/**
 * Voice IVR audio client.
 *
 * Wraps the WebSocket session against `/ws/voice/{id}` plus all the audio
 * plumbing the browser needs to talk to Azure OpenAI gpt-realtime:
 *
 *  - Mic capture via getUserMedia → AudioContext → ScriptProcessor
 *  - Resampling from the browser's native 48 kHz down to 24 kHz mono PCM16
 *  - Base64 encoding & streaming chunks to the backend
 *  - Receiving audio chunks back, queue + low-latency playback through a
 *    second AudioContext sink
 *  - Hold-music synthesis (a soft chord progression) for the wait while the
 *    multi-agent pipeline processes the claim
 *
 * Public surface is intentionally tiny — the React component (VoiceCallModal)
 * only deals with high-level events.
 */

export type VoiceEvent =
  | { type: 'connecting' }
  | { type: 'connected' }
  | { type: 'transcript.user'; text: string }
  | { type: 'transcript.assistant.delta'; text: string }
  | { type: 'transcript.assistant.done'; text: string }
  | { type: 'tool.result'; name: string; result: unknown }
  | { type: 'hold_music_start' }
  | { type: 'hold_music_stop' }
  | { type: 'hangup' }
  | { type: 'speech_started' }
  | { type: 'speech_stopped' }
  | { type: 'error'; message: string }
  | { type: 'closed' };

type Listener = (e: VoiceEvent) => void;

const TARGET_SR = 24_000;
const CHUNK_MS = 100;

export class VoiceAudioClient {
  private ws: WebSocket | null = null;
  private audioCtxIn: AudioContext | null = null;
  private audioCtxOut: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private srcNode: MediaStreamAudioSourceNode | null = null;
  private playQueueTimeSec = 0;
  private listeners: Listener[] = [];
  private holdMusic: HoldMusicSynth | null = null;
  private ringTone: RingTone | null = null;
  private playMuted = false;
  // Mic gating — we don't send anything during the agent's first greeting
  // so the model can actually produce it (the realtime API will not respond
  // if there is an active input_audio_buffer being filled when
  // response.create fires). Enabled after the first transcript.assistant.done
  // arrives, or as a safety net after 8 s.
  private micUnlocked = false;
  private micUnlockTimer: number | null = null;
  // Echo guard: while the assistant's audio is queued for playback we
  // refuse to send any mic data upstream (so Leo's voice doesn't get
  // captured as a fake user turn). We use the ACTUAL playback queue end
  // (playQueueTimeSec) as the source of truth rather than the time the
  // last delta arrived, because the delta arrives well before the audio
  // is heard. After playback ends we open the mic IMMEDIATELY — no extra
  // tail. The user often answers in the natural <100ms gap after Leo
  // stops talking, and any extra tail clips their first syllable
  // ("Quiero" → "iero" → Whisper drops it). The browser's WebRTC-grade
  // echoCancellation handles residual speaker bleed; if any echo still
  // makes it through, the server VAD threshold (0.55) and the Whisper
  // hallucination filter on the backend catch it.
  private static readonly ECHO_TAIL_S = 0;

  constructor(private readonly sessionId: string, private readonly wsBaseUrl: string) {}

  on(listener: Listener) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private emit(e: VoiceEvent) {
    for (const l of this.listeners) l(e);
  }

  async start() {
    this.emit({ type: 'connecting' });
    // 1) Mic — disable autoGainControl (it amplifies far/background voice)
    //    and keep echoCancellation + noiseSuppression which actually help.
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 48_000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
        },
        video: false,
      });
    } catch (e) {
      this.emit({ type: 'error', message: `No se ha podido acceder al micrófono: ${(e as Error).message}` });
      throw e;
    }
    // 2) Output sink
    this.audioCtxOut = new AudioContext({ sampleRate: TARGET_SR });
    this.playQueueTimeSec = this.audioCtxOut.currentTime;
    // 3) Input pipeline
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const Ctx: any = (window as any).AudioContext || (window as any).webkitAudioContext;
    this.audioCtxIn = new Ctx({ sampleRate: 48_000 });
    this.srcNode = this.audioCtxIn!.createMediaStreamSource(this.mediaStream);
    // ScriptProcessor requires a power-of-two buffer size between 256 and
    // 16384. 4096 samples @ 48 kHz = ~85 ms per chunk, which keeps latency
    // low while not flooding the WS with tiny messages.
    const bufferSize = 4096;
    this.processor = this.audioCtxIn!.createScriptProcessor(bufferSize, 1, 1);
    this.srcNode.connect(this.processor);
    // Need to connect to destination otherwise some browsers don't run the processor
    this.processor.connect(this.audioCtxIn!.destination);
    this.processor.onaudioprocess = (ev) => this.handleMicChunk(ev);
    // 4) Open WS
    const url = `${this.wsBaseUrl}/ws/voice/${this.sessionId}`;
    this.ws = new WebSocket(url);
    this.ws.onopen = () => {
      this.emit({ type: 'connected' });
      // Play a Spanish ring tone immediately so the user knows the call is
      // active while gpt-realtime spins up and generates the first
      // greeting audio (typically 1-3 s of upstream latency).
      this.ringTone = new RingTone(this.audioCtxOut!);
      this.ringTone.start();
      // Safety net: if the agent's first transcript.assistant.done never
      // arrives (network glitch, model didn't respond), unlock the mic
      // after 8 s so the user can talk anyway.
      this.micUnlockTimer = window.setTimeout(() => {
        this.micUnlocked = true;
        this.micUnlockTimer = null;
        this.stopRingTone();
      }, 8000);
    };
    this.ws.onclose = () => this.emit({ type: 'closed' });
    this.ws.onerror = () => this.emit({ type: 'error', message: 'Conexión perdida con el asistente' });
    this.ws.onmessage = (msg) => this.handleServerMessage(msg);
  }

  async stop() {
    this.playMuted = true;
    this.stopRingTone();
    this.processor?.disconnect();
    this.srcNode?.disconnect();
    this.audioCtxIn?.close().catch(() => undefined);
    this.audioCtxOut?.close().catch(() => undefined);
    this.audioCtxIn = null;
    this.audioCtxOut = null;
    this.mediaStream?.getTracks().forEach((t) => t.stop());
    this.mediaStream = null;
    if (this.holdMusic) {
      this.holdMusic.stop();
      this.holdMusic = null;
    }
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        /* ignore */
      }
      this.ws = null;
    }
  }

  /** Send text input (debug / fallback for muted mic). */
  sendText(text: string) {
    this.ws?.send(JSON.stringify({ type: 'text', text }));
  }

  /** Cancel the assistant's current speech (barge-in). */
  interrupt() {
    this.ws?.send(JSON.stringify({ type: 'interrupt' }));
  }

  /** Seconds of assistant audio still queued for playback (0 if drained). */
  remainingPlaybackSec(): number {
    if (!this.audioCtxOut) return 0;
    return Math.max(0, this.playQueueTimeSec - this.audioCtxOut.currentTime);
  }

  // ---------------------------------------------------------------- audio in
  private handleMicChunk(ev: AudioProcessingEvent) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    if (!this.micUnlocked) return;
    const inputBuf = ev.inputBuffer.getChannelData(0);
    // Precise echo gate with PARTIAL BUFFER TRIM:
    //   - Buffer represents audio captured from (tNow - bufferDuration) to
    //     tNow in the AudioContext clock.
    //   - The assistant's playback ends at playQueueTimeSec.
    //   - We drop everything captured BEFORE playQueueTimeSec + ECHO_TAIL_S
    //     (that's potential echo) and keep everything captured AFTER.
    //   - If the gate ends partway through this buffer, slice the buffer
    //     and send only the un-gated tail. This is what lets the user
    //     start talking the instant Leo stops without losing the first
    //     syllable: no full-buffer drop, no missing audio.
    if (this.audioCtxOut) {
      const tNow = this.audioCtxOut.currentTime;
      const sampleRate = ev.inputBuffer.sampleRate || 48_000;
      const bufferDurationS = inputBuf.length / sampleRate;
      const bufferStart = tNow - bufferDurationS;
      const gateEnd = this.playQueueTimeSec + VoiceAudioClient.ECHO_TAIL_S;
      if (gateEnd >= tNow) {
        return; // whole buffer is during/right after Leo's audio → drop
      }
      if (gateEnd > bufferStart) {
        // Partial overlap. Slice off the front part that was during gate.
        const cutSamples = Math.max(
          0,
          Math.min(inputBuf.length, Math.ceil((gateEnd - bufferStart) * sampleRate))
        );
        const trimmed = inputBuf.subarray(cutSamples);
        if (trimmed.length > 0) this.sendMicChunk(trimmed);
        return;
      }
    }
    this.sendMicChunk(inputBuf);
  }

  private sendMicChunk(buf: Float32Array) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const downsampled = downsampleBuffer(buf, 48_000, TARGET_SR);
    const pcm16 = floatTo16BitPCM(downsampled);
    const copy = new ArrayBuffer(pcm16.byteLength);
    new Uint8Array(copy).set(new Uint8Array(pcm16.buffer, pcm16.byteOffset, pcm16.byteLength));
    const b64 = arrayBufferToBase64(copy);
    this.ws.send(JSON.stringify({ type: 'audio.append', audio: b64 }));
  }

  // --------------------------------------------------------------- audio out
  private handleServerMessage(msg: MessageEvent) {
    let event: { type: string; [k: string]: unknown };
    try {
      event = JSON.parse(typeof msg.data === 'string' ? msg.data : '{}');
    } catch {
      return;
    }
    switch (event.type) {
      case 'audio.delta':
        // First assistant audio: stop the ring tone, the call is "answered".
        this.stopRingTone();
        this.enqueueAudio(String(event.audio || ''));
        break;
      case 'transcript.user':
        this.emit({ type: 'transcript.user', text: String(event.text || '') });
        break;
      case 'transcript.assistant.delta':
        this.emit({ type: 'transcript.assistant.delta', text: String(event.text || '') });
        break;
      case 'transcript.assistant.done':
        this.emit({ type: 'transcript.assistant.done', text: String(event.text || '') });
        // First time the agent finished a phrase: unlock the mic for the user.
        if (!this.micUnlocked) {
          this.micUnlocked = true;
          if (this.micUnlockTimer !== null) {
            window.clearTimeout(this.micUnlockTimer);
            this.micUnlockTimer = null;
          }
        }
        break;
      case 'tool.result':
        this.emit({ type: 'tool.result', name: String(event.name || ''), result: event.result });
        break;
      case 'hold_music_start':
        // Wait until the agent has finished speaking its "voy a procesar..."
        // intro phrase before kicking in the music. Otherwise the music
        // starts on top of Lola's voice and sounds jarring.
        this.startHoldMusicWhenSilent();
        this.emit({ type: 'hold_music_start' });
        break;
      case 'hold_music_stop':
        this.stopHoldMusic();
        this.emit({ type: 'hold_music_stop' });
        break;
      case 'hangup':
        this.emit({ type: 'hangup' });
        break;
      case 'input_audio_buffer.speech_started':
        this.emit({ type: 'speech_started' });
        break;
      case 'input_audio_buffer.speech_stopped':
        this.emit({ type: 'speech_stopped' });
        break;
      case 'error':
        this.emit({ type: 'error', message: String(event.message || 'Error desconocido') });
        break;
      default:
        break;
    }
  }

  private enqueueAudio(b64: string) {
    if (!b64 || !this.audioCtxOut || this.playMuted) return;
    const raw = base64ToArrayBuffer(b64);
    const samples = new Int16Array(raw);
    const float = new Float32Array(samples.length);
    for (let i = 0; i < samples.length; i++) float[i] = samples[i] / 0x7fff;
    const buf = this.audioCtxOut.createBuffer(1, float.length, TARGET_SR);
    buf.getChannelData(0).set(float);
    const src = this.audioCtxOut.createBufferSource();
    src.buffer = buf;
    src.connect(this.audioCtxOut.destination);
    // Schedule sequentially so chunks play back-to-back without gaps
    const startAt = Math.max(this.audioCtxOut.currentTime, this.playQueueTimeSec);
    src.start(startAt);
    this.playQueueTimeSec = startAt + buf.duration;
  }

  // ------------------------------------------------------------ hold music
  private startHoldMusic() {
    if (this.holdMusic || !this.audioCtxOut) return;
    this.holdMusic = new HoldMusicSynth(this.audioCtxOut);
    this.holdMusic.start();
  }

  /** Defer hold-music start until any queued assistant audio has finished. */
  private startHoldMusicWhenSilent() {
    if (!this.audioCtxOut) return;
    // Schedule music to start AFTER the currently queued audio ends. This
    // covers the typical "voy a procesar su caso..." sentence the agent
    // says immediately before calling submit_claim — without this guard
    // the music starts on top of Lola's voice and sounds jarring.
    const now = this.audioCtxOut.currentTime;
    const delaySec = Math.max(0, this.playQueueTimeSec - now + 0.2);
    if (delaySec < 0.05) {
      this.startHoldMusic();
      return;
    }
    window.setTimeout(() => this.startHoldMusic(), delaySec * 1000);
  }

  private stopRingTone() {
    if (!this.ringTone) return;
    this.ringTone.stop();
    this.ringTone = null;
  }

  private stopHoldMusic() {
    if (!this.holdMusic) return;
    this.holdMusic.stop();
    this.holdMusic = null;
  }
}

// ---------------------------------------------------------------------------
// Audio utilities
// ---------------------------------------------------------------------------
function downsampleBuffer(buffer: Float32Array, srcRate: number, dstRate: number): Float32Array {
  if (srcRate === dstRate) return buffer;
  const ratio = srcRate / dstRate;
  const newLen = Math.round(buffer.length / ratio);
  const out = new Float32Array(newLen);
  let pos = 0;
  let i = 0;
  while (pos < newLen) {
    const next = Math.round((pos + 1) * ratio);
    let sum = 0;
    let count = 0;
    for (; i < next && i < buffer.length; i++) {
      sum += buffer[i];
      count++;
    }
    out[pos] = count ? sum / count : 0;
    pos++;
  }
  return out;
}

function floatTo16BitPCM(input: Float32Array): Int16Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

function arrayBufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return window.btoa(binary);
}

function base64ToArrayBuffer(b64: string): ArrayBuffer {
  const binary = window.atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

// ---------------------------------------------------------------------------
// Hold music synthesizer — gentle ambient chord progression
// ---------------------------------------------------------------------------
// We don't want to ship an MP3 file just for a hold-music cue, so synthesize
// a quiet, slow chord progression with the Web Audio API. Each chord plays
// for ~4 seconds and crossfades smoothly into the next so there are no
// click/pop artifacts when oscillators stop.
class HoldMusicSynth {
  private masterGain: GainNode;
  private activeChord: { oscillators: OscillatorNode[]; gain: GainNode } | null = null;
  private intervalHandle: number | null = null;
  private chordIdx = 0;
  private readonly chords: number[][] = [
    [220, 261.63, 329.63], // A minor (A, C, E)
    [196, 246.94, 293.66], // G major (G, B, D)
    [174.61, 220, 261.63], // F major (F, A, C)
    [196, 246.94, 329.63], // G sus
  ];
  private readonly fadeInS = 0.4;
  private readonly chordDurationS = 4.0;

  constructor(private ctx: AudioContext) {
    this.masterGain = ctx.createGain();
    this.masterGain.gain.value = 0;
    // Soft low-pass to take the harshness off pure sine fundamentals.
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 1800;
    lp.Q.value = 0.7;
    this.masterGain.connect(lp);
    lp.connect(ctx.destination);
  }

  start() {
    const t = this.ctx.currentTime;
    this.masterGain.gain.cancelScheduledValues(t);
    this.masterGain.gain.setValueAtTime(0, t);
    this.masterGain.gain.linearRampToValueAtTime(0.07, t + this.fadeInS);
    this.playNextChord();
    this.intervalHandle = window.setInterval(
      () => this.playNextChord(),
      this.chordDurationS * 1000,
    );
  }

  stop() {
    if (this.intervalHandle !== null) {
      clearInterval(this.intervalHandle);
      this.intervalHandle = null;
    }
    const t = this.ctx.currentTime;
    this.masterGain.gain.cancelScheduledValues(t);
    // Take the current value and ramp it down — avoids the snap that
    // happens with setValueAtTime when the previous schedule was active.
    this.masterGain.gain.setValueAtTime(this.masterGain.gain.value, t);
    this.masterGain.gain.linearRampToValueAtTime(0, t + this.fadeInS);
    // Stop oscillators slightly after the ramp completes
    const stopAt = t + this.fadeInS + 0.05;
    this.activeChord?.oscillators.forEach((o) => {
      try {
        o.stop(stopAt);
      } catch {
        /* */
      }
    });
    this.activeChord = null;
  }

  /** Play the next chord with a soft crossfade against the previous one. */
  private playNextChord() {
    const ctx = this.ctx;
    const t = ctx.currentTime;
    const fade = 0.6; // crossfade time

    // Fade out and stop the previous chord
    const old = this.activeChord;
    if (old) {
      old.gain.gain.cancelScheduledValues(t);
      old.gain.gain.setValueAtTime(old.gain.gain.value, t);
      old.gain.gain.linearRampToValueAtTime(0, t + fade);
      old.oscillators.forEach((o) => {
        try {
          o.stop(t + fade + 0.1);
        } catch {
          /* */
        }
      });
    }

    // Build the new chord with its own gain node so we can envelope it
    const chord = this.chords[this.chordIdx % this.chords.length];
    this.chordIdx++;
    const chordGain = ctx.createGain();
    chordGain.gain.setValueAtTime(0, t);
    chordGain.gain.linearRampToValueAtTime(1, t + fade);
    chordGain.connect(this.masterGain);
    const oscillators: OscillatorNode[] = [];
    chord.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      // Triangle waves are softer and less prone to phase clicks than pure
      // sine when amplitude is non-zero at stop time.
      osc.type = i === 0 ? 'triangle' : 'sine';
      osc.frequency.value = freq;
      // Slight detune adds subtle warmth without sounding off-key.
      osc.detune.value = i === 1 ? -3 : i === 2 ? 4 : 0;
      const oscGain = ctx.createGain();
      oscGain.gain.value = i === 0 ? 0.5 : 0.35;
      osc.connect(oscGain);
      oscGain.connect(chordGain);
      osc.start(t);
      oscillators.push(osc);
    });
    this.activeChord = { oscillators, gain: chordGain };
  }
}

// ---------------------------------------------------------------------------
// Spanish ring tone — plays while we wait for the realtime model to send
// the first audio chunk. Pattern is the classic Telefónica cadence:
// 1.5 s tone on (at 425 Hz, the European reference tone) + 3 s silence,
// looping until stop() is called.
// ---------------------------------------------------------------------------
class RingTone {
  private gain: GainNode;
  private osc: OscillatorNode | null = null;
  private intervalHandle: number | null = null;
  private cycleOnMs = 1500;
  private cycleOffMs = 3000;

  constructor(private ctx: AudioContext) {
    this.gain = ctx.createGain();
    this.gain.gain.value = 0;
    // Mild low-pass so the 425 Hz tone has a phone-like timbre rather
    // than a sharp test tone.
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 1500;
    this.gain.connect(lp);
    lp.connect(ctx.destination);
  }

  start() {
    this.osc = this.ctx.createOscillator();
    this.osc.type = 'sine';
    this.osc.frequency.value = 425;
    this.osc.connect(this.gain);
    this.osc.start();
    this.toneOn();
    // Schedule the on/off cycle
    this.intervalHandle = window.setInterval(
      () => this.toneOn(),
      this.cycleOnMs + this.cycleOffMs,
    );
  }

  stop() {
    if (this.intervalHandle !== null) {
      clearInterval(this.intervalHandle);
      this.intervalHandle = null;
    }
    const t = this.ctx.currentTime;
    this.gain.gain.cancelScheduledValues(t);
    this.gain.gain.setValueAtTime(this.gain.gain.value, t);
    this.gain.gain.linearRampToValueAtTime(0, t + 0.2);
    if (this.osc) {
      try {
        this.osc.stop(t + 0.3);
      } catch {
        /* */
      }
      this.osc = null;
    }
  }

  private toneOn() {
    const t = this.ctx.currentTime;
    this.gain.gain.cancelScheduledValues(t);
    this.gain.gain.setValueAtTime(0, t);
    this.gain.gain.linearRampToValueAtTime(0.18, t + 0.05);
    // Hold then ramp off
    this.gain.gain.setValueAtTime(0.18, t + this.cycleOnMs / 1000 - 0.05);
    this.gain.gain.linearRampToValueAtTime(0, t + this.cycleOnMs / 1000);
  }
}
