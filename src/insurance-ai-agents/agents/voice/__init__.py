"""Voice IVR built on top of Azure OpenAI gpt-realtime-mini.

Architecture
------------
The customer dashboard opens a WebSocket against the backend at
``/ws/voice/{session_id}``. The backend, in turn, opens a second WebSocket
against the Azure OpenAI realtime endpoint and acts as a *stateful bridge*
between the two:

  Browser <─PCM16─> Backend (this module) <─PCM16─> AOAI gpt-realtime-mini

The bridge does three jobs the browser cannot:

  1. Holds Azure credentials (Managed Identity / az CLI) so the model URL
     and bearer never leave the server.
  2. Configures the realtime session on connect — instructions in Spanish
     plus the two tools the agent needs (`lookup_customer`, `submit_claim`).
  3. Executes function calls server-side. ``lookup_customer`` resolves a
     DNI against ``CUSTOMER_HISTORY`` and returns name + policy info. When
     ``submit_claim`` is invoked the bridge:
        - Tells the frontend to start hold music (`type=hold_music_start`)
        - Runs the full multi-agent pipeline (process_claim)
        - Tells the frontend to stop hold music
        - Pushes the JSON result back into the realtime session so the
          model can read it out loud in Spanish in the proper register
          (approved / rejected / human_review).

The browser only sees raw audio (sent + received) and a small set of
control events. All business logic lives here.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from typing import Any, Callable, Awaitable

import websockets
from azure.identity.aio import DefaultAzureCredential

from agents.shared.brand import BRAND_NAME, VOICE_ASSISTANT_NAME

logger = logging.getLogger(__name__)

DEFAULT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_VOICE_DEPLOYMENT", "gpt-realtime-mini")
DEFAULT_API_VERSION = "2025-04-01-preview"
# gpt-realtime-mini voices: alloy, ash, ballad, coral, echo, sage, shimmer,
# verse. ballad = expressive, warm, less robotic for Spanish IVR scenarios.
DEFAULT_VOICE = os.environ.get("VOICE_AGENT_VOICE", "ballad")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
# NOTE: We use ``str.replace`` (instead of f-strings) so the curly-brace
# placeholders the model fills in at runtime — ``{nombre}``,
# ``{coverage_type}``, ``{vehicle}`` — are left intact. The
# ``@BRAND@`` / ``@ASSISTANT@`` sentinels are replaced once at module load
# with the configured brand and assistant names.
SYSTEM_PROMPT = """Eres @ASSISTANT@, asistente virtual de inteligencia artificial de @BRAND@. Hablas español de España con un tono cercano, profesional y empático. Tu trabajo es atender por voz a un cliente que llama para abrir un parte de siniestro de coche.

Sigue ESTRICTAMENTE este guion:

PASO 1 · Saludo (FRASE EXACTA, no improvises)
   - Di literalmente: "Hola, soy @ASSISTANT@, su asistente virtual de inteligencia artificial de @BRAND@. ¿En qué puedo ayudarle hoy?"
   - Es CRÍTICO que dejes claro que eres una IA, no una persona, para evitar confusión.
   - Espera a que el cliente confirme que quiere abrir un parte.

PASO 2 · Identificación
   - Pide el nombre completo y el DNI del cliente.
   - Cuando tengas el DNI (8 cifras + 1 letra), llama a la función `lookup_customer(dni)`.
   - Si la función devuelve "found": false, di "Lo siento, no encuentro su póliza con ese DNI. ¿Me lo puede repetir?" y reintenta.
   - Si devuelve "found": true, saluda al cliente por su nombre y confirma la póliza: "Perfecto {nombre}, veo que tiene póliza {coverage_type} para un {vehicle}. ¿Qué ha ocurrido?"

PASO 3 · Recogida del siniestro — ADAPTA LAS PREGUNTAS AL TIPO DE INCIDENTE
   - Deja que el cliente describa lo ocurrido sin interrumpir.
   - Una vez sepas QUÉ tipo de incidente es (colisión, robo, incendio, vandalismo, meteorológico, otro), haz SOLO las preguntas que tengan sentido para ese tipo. NUNCA preguntes por "daños del vehículo" en un robo donde el coche ha desaparecido, ni por "vehículos implicados" si te lo robaron, etc.

   COLISIÓN — datos necesarios:
        a) Fecha y lugar (vía, km aproximado o ciudad)
        b) Otros vehículos/personas implicados (sí/no, cuántos)
        c) ¿Hay parte amistoso firmado?
        d) Severidad de daños: "¿diría que los daños son LEVES, MODERADOS, GRAVES o PÉRDIDA TOTAL (el coche no se puede reparar)?"

   ROBO — datos necesarios (NO preguntes por daños ni implicados):
        a) Fecha y hora aproximada en que notó el robo
        b) Lugar donde estaba aparcado el vehículo
        c) ¿Ha presentado denuncia ante Policía o Guardia Civil?
        d) Alcance del robo: "¿Le han robado el vehículo entero, o solo objetos/piezas del interior?"
           → si vehículo entero → severity = total_loss
           → si solo objetos/piezas → pregunta severidad LEVE/MODERADO/GRAVE

   INCENDIO — datos necesarios:
        a) Fecha y lugar donde se produjo el incendio
        b) Causa aparente (si la conoce): eléctrica, accidente, vandalismo, propagación de otro vehículo, etc.
        c) ¿Intervinieron los bomberos? ¿Hay informe?
        d) Severidad: "¿el coche tiene daños LEVES, MODERADOS, GRAVES o ha quedado CALCINADO/SINIESTRO TOTAL?"

   VANDALISMO — datos necesarios:
        a) Fecha y lugar
        b) Qué piezas/zonas han sufrido daño (pintura, lunas, espejos, ruedas, etc.)
        c) ¿Ha presentado denuncia?
        d) Severidad: LEVES, MODERADOS, GRAVES o PÉRDIDA TOTAL.

   METEOROLÓGICO (granizo, inundación, viento, árbol caído):
        a) Fecha y lugar
        b) Tipo de fenómeno (granizo, inundación, viento, caída de árbol/objeto)
        c) Severidad: LEVES, MODERADOS, GRAVES o PÉRDIDA TOTAL.

   REGLAS GENERALES:
   - Mapea la respuesta de severidad al enum: leve→minor, moderado→moderate, grave→severe, pérdida total / siniestro total / calcinado / desaparecido / robo del vehículo entero → total_loss.
   - NUNCA preguntes por el importe en euros. El cliente no es perito; el sistema estima el importe internamente a partir de la severidad.
   - Si falta algún dato obligatorio para el tipo correspondiente, pregunta UNA pregunta corta cada vez hasta completarlos.
   - Cuando tengas TODO, di: "Gracias, voy a procesar su caso. Le pongo en espera unos segundos por favor." y llama a `submit_claim(customer_id, policy_id, incident_type, description, damage_severity)`.

PASO 4 · Comunicación del resultado
   Cuando recibas el resultado de `submit_claim`, lee EXACTAMENTE el campo `spoken_response` que viene en la respuesta. No improvises, no añadas información extra.

PASO 5 · Cierre — REGLA CRÍTICA
   - Después de comunicar el resultado, pregunta: "¿Necesita algo más?" y DETENTE. NO añadas nada más en esa misma respuesta. Espera de verdad a que el cliente responda — puede tardar varios segundos.
   - REGLA OBLIGATORIA: SIEMPRE que vayas a despedirte (frases como "muchas gracias", "que tenga buen día", "voy a finalizar la llamada", "un agente le contactará") DEBES llamar a la función `end_call` en la MISMA respuesta donde te despides. No es opcional. Sin llamar a end_call, el cliente se queda en línea esperando.
   - Casos en los que SIEMPRE despides + llamas a `end_call`:
        a) El cliente dice "no", "no gracias", "estoy bien", "nada más", "ya está", etc. → di "Perfecto, muchas gracias por contactar con @BRAND@. Que tenga un buen día." y `end_call`
        b) El cliente pide hablar con un operador o agente humano → di "Tomo nota, un agente le llamará en breve. Muchas gracias por contactar." + `end_call`
        c) El cliente intenta hablar de otro tema fuera de seguros → redirige una vez; si insiste → despídete + `end_call`
        d) NUNCA te despidas por iniciativa propia tras dar el veredicto. Sólo te despides cuando el cliente lo confirme o cuando el sistema te avise con un mensaje "[Sistema: el cliente lleva varios segundos sin responder...]".

Reglas importantes:
 - Habla SIEMPRE en español de España.
 - Frases cortas, naturales, sin tecnicismos.
 - Nunca inventes información sobre la póliza o el siniestro.
 - NUNCA respondas a algo que no hayas entendido con claridad. Si dudas, pide al cliente que repita.
 - Si percibes silencio prolongado o sonidos no humanos, ignóralos. Solo responde cuando estés seguro de que el cliente ha hablado.
 - Si el cliente te pregunta si eres humano, confirma que NO, que eres un asistente virtual con inteligencia artificial entrenado para tramitar partes.
 - DESPEDIDA = LLAMADA A end_call. Sin excepción.
""".replace("@ASSISTANT@", VOICE_ASSISTANT_NAME).replace("@BRAND@", BRAND_NAME)

# ---------------------------------------------------------------------------
# Tools (function-calling) — schemas the realtime model can invoke.
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "name": "lookup_customer",
        "description": (
            "Resuelve un DNI español (8 dígitos + 1 letra) contra el sistema "
            "de pólizas. Devuelve nombre, id de cliente y póliza asociada."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "dni": {
                    "type": "string",
                    "description": "DNI en formato 12345678A (sin guiones ni espacios)",
                }
            },
            "required": ["dni"],
        },
    },
    {
        "type": "function",
        "name": "submit_claim",
        "description": (
            "Envía el parte de siniestro al pipeline multi-agente para "
            "evaluación. El importe en euros lo estima internamente el "
            "sistema a partir de la severidad subjetiva que el cliente "
            "describe (el cliente NO es perito y no sabe el coste real). "
            "Devuelve la decisión final (approve, reject, human_review) y "
            "un texto listo para leer al cliente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "policy_id": {"type": "string"},
                "incident_type": {
                    "type": "string",
                    "enum": ["collision", "theft", "fire", "vandalism", "weather", "other"],
                },
                "description": {
                    "type": "string",
                    "description": "Descripción libre del siniestro tal como la contó el cliente",
                },
                "damage_severity": {
                    "type": "string",
                    "enum": ["minor", "moderate", "severe", "total_loss"],
                    "description": (
                        "Severidad subjetiva de los daños tal como la "
                        "describe el cliente. minor = rasguños, marcas; "
                        "moderate = abolladuras, pieza a sustituir; "
                        "severe = varias piezas dañadas, no se puede "
                        "circular; total_loss = vehículo siniestro total."
                    ),
                },
            },
            "required": ["customer_id", "policy_id", "incident_type", "description", "damage_severity"],
        },
    },
    {
        "type": "function",
        "name": "end_call",
        "description": (
            "Cuelga la llamada cuando el cliente ha confirmado que no "
            "necesita nada más. Llamar SIEMPRE después de despedirse, no "
            "antes."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]

# ---------------------------------------------------------------------------
# Token + URL helpers
# ---------------------------------------------------------------------------
_cred: DefaultAzureCredential | None = None
_token: str | None = None
_token_expiry: float = 0


async def _get_token() -> str:
    global _cred, _token, _token_expiry
    if _token and time.time() < _token_expiry - 60:
        return _token
    if _cred is None:
        # process_timeout=60 sube el timeout interno de AzureCliCredential
        # (default 10s). Bajo carga concurrente con uvicorn el `az` puede
        # tardar más y el voice bridge no tiene fallback.
        _cred = DefaultAzureCredential(
            exclude_interactive_browser_credential=True,
            process_timeout=60,
        )
    access = await _cred.get_token("https://cognitiveservices.azure.com/.default")
    _token = access.token
    _token_expiry = access.expires_on
    return _token


def _realtime_url() -> str:
    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    # https -> wss
    endpoint = endpoint.replace("https://", "wss://").replace("http://", "ws://")
    return (
        f"{endpoint}/openai/realtime"
        f"?api-version={DEFAULT_API_VERSION}"
        f"&deployment={DEFAULT_DEPLOYMENT}"
    )


# ---------------------------------------------------------------------------
# The bridge
# ---------------------------------------------------------------------------
ToolFn = Callable[[dict], Awaitable[dict]]


class VoiceBridge:
    """Bridges one browser <-> one AOAI realtime session.

    Caller responsibility:
      - Provide a ``send_to_client`` coroutine that ships JSON events back
        to the browser WebSocket.
      - Provide tool implementations via ``tools`` (a dict of name -> coro).
      - Call ``run()`` to start the upstream connection.
      - Forward incoming browser messages to ``handle_client_event``.
      - Call ``close()`` on disconnect.

    Observer pattern:
      Other clients (e.g. the operator dashboard window) can subscribe to
      every event the bridge would normally only send to the customer by
      calling :meth:`add_observer` with their own ``send_to_client``-like
      coroutine. Observers receive a replay of the most recent buffered
      events on attach so they can render the call state immediately even
      if they connect mid-call.
    """

    # Replay buffer cap — enough to capture an entire call's transcript
    # plus tool results plus a few hundred audio.delta packets (we still
    # buffer audio so the operator view can show waveform/playback if it
    # ever wants to; for now it can ignore the audio.delta entries).
    _MAX_BUFFER = 400

    def __init__(
        self,
        session_id: str,
        tools: dict[str, ToolFn],
        send_to_client: Callable[[dict], Awaitable[None]],
    ) -> None:
        self.session_id = session_id
        self.tools = tools
        self._customer_send = send_to_client
        self._observers: list[Callable[[dict], Awaitable[None]]] = []
        self._event_buffer: list[dict] = []
        # Lock para que el par "snapshot+add_observer" sea atómico — sin él
        # un evento publicado entre replay_buffer() y add_observer() se
        # perdería para el observer recién enganchado.
        self._observer_lock: asyncio.Lock = asyncio.Lock()
        self.started_at: float = time.time()
        self._upstream: websockets.WebSocketClientProtocol | None = None
        self._upstream_reader_task: asyncio.Task | None = None
        self._closed = False
        # Tracks whether _delayed_close has already been scheduled so the
        # tool-call path and the goodbye-phrase fallback don't race and
        # cut audio mid-sentence.
        self._hangup_scheduled = False
        # Inactivity tracker: when the assistant finishes a turn we set
        # this; if the user doesn't speak within INACTIVITY_TIMEOUT_S we
        # trigger an automatic farewell instead of leaving the line dead.
        self._inactivity_task: asyncio.Task | None = None
        # Did the assistant's last finished response already contain a
        # goodbye phrase? If so, the end_call tool handler skips its
        # defensive "force a farewell" response.create so the customer
        # doesn't hear the same goodbye twice in a row.
        self._last_assistant_was_goodbye = False
        # Per-session state remembered between tool calls (e.g. the customer
        # identity once we have looked it up).
        self.state: dict[str, Any] = {}

    INACTIVITY_TIMEOUT_S = 20.0

    # Eventos que SÓLO interesan al cliente (audio en bruto). No los
    # guardamos en el buffer de replay ni los enviamos a observers — el
    # operador no reproduce audio y mantenerlos llenaría el buffer (~30
    # paquetes/s) expulsando eventos semánticos útiles como transcripts.
    _CUSTOMER_ONLY_EVENT_TYPES = frozenset({
        "audio.delta",
        "audio_chunk",
        "audio",
    })

    # Tope de tiempo que esperamos a que un observer drene un evento.
    # Una ventana operador congelada o lenta no debe ralentizar el bridge
    # principal (que mediación con AOAI realtime es muy sensible a back-
    # pressure). Si supera este TTL la quitamos de la lista.
    _OBSERVER_SEND_TIMEOUT_S = 2.0

    # ---------------------------------------------------------- observers
    async def send_to_client(self, payload: dict) -> None:
        """Send ``payload`` to the customer and every attached observer.

        Also stores the event in a bounded replay buffer so observers that
        attach mid-call can be primed with the conversation so far.
        """
        ptype = payload.get("type", "") if isinstance(payload, dict) else ""
        customer_only = ptype in self._CUSTOMER_ONLY_EVENT_TYPES

        # Bufferizamos sólo eventos semánticos (no audio crudo) — el
        # operador re-renderiza la conversación a partir del buffer en
        # attach. Para hacer la operación buffer-append + observer-add
        # atómica (evitando carrera "evento entre replay y add") usamos
        # el lock al añadir y los nuevos observers también lo toman.
        if not customer_only:
            async with self._observer_lock:
                self._event_buffer.append(payload)
                if len(self._event_buffer) > self._MAX_BUFFER:
                    self._event_buffer = self._event_buffer[-self._MAX_BUFFER:]

        # Fan out to the customer. The original send_to_client coroutine
        # owns its own error handling (it logs and swallows), but we still
        # guard here to avoid one failure killing the broadcast.
        try:
            await self._customer_send(payload)
        except Exception as e:  # noqa: BLE001
            logger.debug("[%s] customer send failed: %s", self.session_id, e)

        # No fan-out de audio crudo a observers.
        if customer_only or not self._observers:
            return

        # Snapshot the observer list because dead observers will be removed
        # from self._observers inside _safe_observer_send.
        observers = list(self._observers)
        await asyncio.gather(
            *(self._safe_observer_send(obs, payload) for obs in observers),
            return_exceptions=True,
        )

    async def _safe_observer_send(
        self,
        obs: Callable[[dict], Awaitable[None]],
        payload: dict,
    ) -> None:
        try:
            await asyncio.wait_for(obs(payload), timeout=self._OBSERVER_SEND_TIMEOUT_S)
        except asyncio.TimeoutError:
            logger.debug("[%s] observer send timed out, removing", self.session_id)
            try:
                self._observers.remove(obs)
            except ValueError:
                pass
        except Exception as e:  # noqa: BLE001
            logger.debug("[%s] observer send failed, removing: %s", self.session_id, e)
            try:
                self._observers.remove(obs)
            except ValueError:
                pass

    def add_observer(self, send_func: Callable[[dict], Awaitable[None]]) -> None:
        """Register ``send_func`` to receive every future event sent to
        the customer. Callers should pair this with :meth:`remove_observer`
        when the observer disconnects.

        Prefer :meth:`attach_observer_with_replay` for new observers — it
        does the replay + add atomically under the bridge lock so no events
        are lost in the gap between them.
        """
        self._observers.append(send_func)

    async def attach_observer_with_replay(
        self,
        send_func: Callable[[dict], Awaitable[None]],
    ) -> list[dict]:
        """Atomically take a snapshot of the buffered events and register
        ``send_func`` as an observer. Returns the snapshot so the caller
        can replay it to the new client. Holding the lock between the two
        operations guarantees that any event published after this call
        will also reach ``send_func`` via the live observer path.
        """
        async with self._observer_lock:
            snapshot = list(self._event_buffer)
            self._observers.append(send_func)
        return snapshot

    def remove_observer(self, send_func: Callable[[dict], Awaitable[None]]) -> None:
        try:
            self._observers.remove(send_func)
        except ValueError:
            pass

    def replay_buffer(self) -> list[dict]:
        """Return a copy of the buffered events so a freshly-attached
        observer can render the call state immediately.
        """
        return list(self._event_buffer)

    # ------------------------------------------------------------------ life
    async def run(self) -> None:
        """Open upstream WS and start the receive loop. Returns once the
        connection is established. The receive loop continues in the
        background until ``close()`` is called.
        """
        token = await _get_token()
        url = _realtime_url()
        headers = {
            "Authorization": f"Bearer {token}",
            "openai-beta": "realtime=v1",
        }
        logger.info("[%s] connecting to %s", self.session_id, url)
        # Keepalive: send a WS ping every 20 s so a 1011-keepalive-timeout
        # error doesn't kill the bridge mid-conversation while waiting for
        # the user or the multi-agent pipeline to finish.
        self._upstream = await websockets.connect(
            url,
            additional_headers=headers,
            max_size=16 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=60,
            close_timeout=10,
        )
        # Configure the session
        await self._send_upstream({
            "type": "session.update",
            "session": {
                "modalities": ["audio", "text"],
                "voice": DEFAULT_VOICE,
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    # gpt-realtime-whisper (May 2026) is the gpt-5 era
                    # transcription model, built on the gpt-realtime base.
                    # Strictly better than whisper-1 and gpt-4o-mini-
                    # transcribe at hallucination resistance and Spanish
                    # accuracy. If the realtime session refuses it
                    # (param-not-supported), fall back to
                    # "gpt-4o-mini-transcribe" by env override.
                    "model": os.environ.get(
                        "VOICE_TRANSCRIPTION_MODEL", "gpt-realtime-whisper"
                    ),
                    "language": "es",
                    # `prompt` only exists on the legacy whisper-1 model.
                    # gpt-realtime-whisper and gpt-4o-mini-transcribe reject
                    # it with "The 'prompt' parameter is not supported for
                    # this model.". We include the domain vocabulary prompt
                    # only when explicitly opted in (e.g. when the deployed
                    # transcription model is whisper-1).
                    **(
                        {
                            "prompt": (
                                f"Conversación telefónica en español de España entre {VOICE_ASSISTANT_NAME} "
                                f"(asistente virtual de seguros {BRAND_NAME}) y un cliente "
                                "que abre un parte de siniestro de coche. Vocabulario "
                                "habitual: DNI con ocho dígitos seguidos de una letra "
                                "(ej. 12345678A), matrículas con cuatro dígitos y tres "
                                "letras (ej. 1234ABC), nombres como Ana, Carlos, María, "
                                "Fernández, García, Ruiz, Martínez, Díaz. Términos "
                                "frecuentes: parachoques, amortiguador, retrovisor, "
                                "carrocería, puerta, capó, faro, parabrisas, alcance "
                                "trasero, colisión frontal, golpe lateral, atropello, "
                                "incendio, robo, vandalismo, granizo, daños propios, "
                                "tercero implicado, denuncia, atestado, póliza, "
                                "siniestro, peritaje, franquicia, todo riesgo, terceros, "
                                "leves, moderados, graves."
                            ),
                        }
                        if os.environ.get("VOICE_TRANSCRIPTION_PROMPT_ENABLED", "false").lower() == "true"
                        else {}
                    ),
                },
                "turn_detection": {
                    "type": "server_vad",
                    # Tuned for short Spanish utterances like "no gracias" or
                    # "sí, todo bien". A high threshold (0.55) was missing
                    # these short replies entirely after the decision was
                    # read out; 0.4 catches them reliably without producing
                    # false speech-starts from background noise (the client-
                    # side echo gate already filters speaker bleed).
                    "threshold": 0.4,
                    # Lower padding avoids clipping the leading "no" of
                    # "no gracias" while still catching the consonant onset.
                    "prefix_padding_ms": 250,
                    # Shorter tail makes Leo react to brief replies quickly
                    # without waiting almost a full second of silence.
                    "silence_duration_ms": 550,
                },
                "instructions": SYSTEM_PROMPT,
                "tools": TOOLS,
                "tool_choice": "auto",
                # Lower temperature reduces the unnatural pitch / cadence
                # drift the realtime model sometimes exhibits in Spanish.
                "temperature": 0.6,
            },
        })
        # Inject a synthetic "phone ringing" trigger so the model starts the
        # conversation IMMEDIATELY without waiting for the user to speak. The
        # bracketed text is treated as an internal cue (the user never hears
        # it — they hear the model's spoken response).
        await self._send_upstream({
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": (
                        "[Sistema: el cliente acaba de descolgar. Salúdale "
                        "INMEDIATAMENTE con la frase del PASO 1 de tus "
                        "instrucciones. No esperes a que el cliente hable."
                    )}],
            },
        })
        await self._send_upstream({
            "type": "response.create",
            "response": {
                "modalities": ["audio", "text"],
                "instructions": (
                    "Saluda al cliente AHORA mismo diciendo LITERALMENTE: "
                    f"\"Hola, soy {VOICE_ASSISTANT_NAME}, su asistente virtual de inteligencia "
                    f"artificial de {BRAND_NAME}. ¿En qué puedo "
                    "ayudarle hoy?\". No esperes a que el cliente hable "
                    "primero, no improvises otra fórmula."
                ),
            },
        })
        self._upstream_reader_task = asyncio.create_task(self._upstream_reader())

    async def close(self) -> None:
        self._closed = True
        if self._inactivity_task:
            self._inactivity_task.cancel()
            self._inactivity_task = None
        if self._upstream_reader_task:
            self._upstream_reader_task.cancel()
        if self._upstream:
            try:
                await self._upstream.close()
            except Exception:  # noqa: BLE001
                pass
            self._upstream = None

    # ----------------------------------------------------------------- send
    async def _send_upstream(self, payload: dict) -> None:
        if self._upstream is None:
            return
        try:
            await self._upstream.send(json.dumps(payload))
        except Exception as e:  # noqa: BLE001
            logger.warning("[%s] upstream send failed: %s", self.session_id, e)

    async def handle_client_event(self, raw: str | bytes) -> None:
        """Receive a JSON event from the browser and forward to upstream."""
        try:
            event = json.loads(raw) if isinstance(raw, (str, bytes, bytearray)) else raw
        except Exception:
            logger.warning("[%s] bad client event: %r", self.session_id, raw[:80])
            return
        kind = event.get("type", "")
        if kind == "audio.append":
            # Any incoming user audio resets the inactivity watchdog.
            self._cancel_inactivity_timer()
            # Browser sends base64 PCM16 chunks
            await self._send_upstream({
                "type": "input_audio_buffer.append",
                "audio": event.get("audio", ""),
            })
        elif kind == "audio.commit":
            await self._send_upstream({"type": "input_audio_buffer.commit"})
            await self._send_upstream({
                "type": "response.create",
                "response": {"modalities": ["audio", "text"]},
            })
        elif kind == "text":
            # Text input (fallback for testing without mic)
            await self._send_upstream({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": event.get("text", "")}],
                },
            })
            await self._send_upstream({
                "type": "response.create",
                "response": {"modalities": ["audio", "text"]},
            })
        elif kind == "ping":
            await self.send_to_client({"type": "pong"})
        elif kind == "interrupt":
            await self._send_upstream({"type": "response.cancel"})
        else:
            logger.debug("[%s] unknown client event %s", self.session_id, kind)

    # ----------------------------------------------------------------- recv
    async def _upstream_reader(self) -> None:
        """Pump events from AOAI realtime to the client, intercepting tool
        calls and executing them server-side.
        """
        assert self._upstream is not None
        try:
            async for msg in self._upstream:
                if self._closed:
                    break
                try:
                    event = json.loads(msg)
                except Exception:
                    continue
                etype = event.get("type", "")

                # 1) Audio out — forward verbatim
                if etype == "response.audio.delta":
                    await self.send_to_client({
                        "type": "audio.delta",
                        "audio": event.get("delta", ""),
                    })
                    continue

                # 2) Audio transcript (what the AI just said)
                if etype == "response.audio_transcript.delta":
                    await self.send_to_client({
                        "type": "transcript.assistant.delta",
                        "text": event.get("delta", ""),
                    })
                    continue
                if etype == "response.audio_transcript.done":
                    transcript_full = event.get("transcript", "") or ""
                    await self.send_to_client({
                        "type": "transcript.assistant.done",
                        "text": transcript_full,
                    })
                    is_goodbye = _looks_like_goodbye(transcript_full)
                    self._last_assistant_was_goodbye = is_goodbye
                    # Backup: if the model said goodbye but forgot to call
                    # the end_call tool, hang up anyway. Catches the common
                    # failure where the model produces a polished closing
                    # phrase but never emits a function call alongside it.
                    if is_goodbye:
                        logger.info(
                            "[%s] goodbye phrase detected, auto-closing: %r",
                            self.session_id, transcript_full[:100],
                        )
                        # 6 s aligns with the end_call path delay and the
                        # client waits for its audio queue to drain anyway,
                        # so this never cuts off the goodbye sentence.
                        asyncio.create_task(self._delayed_close(6.0))
                    continue

                # 3) User transcript (what the user said)
                if etype == "conversation.item.input_audio_transcription.completed":
                    user_text = event.get("transcript", "")
                    if is_user_transcript_hallucination(user_text):
                        # Whisper hallucinated from silence/noise. Defense
                        # in depth:
                        #   (a) cancel any in-flight assistant response that
                        #       was triggered by this bogus turn before it
                        #       reaches the user's speakers
                        #   (b) delete the user item from the conversation
                        #       so the model doesn't condition on it
                        await self._send_upstream({"type": "response.cancel"})
                        item_id = event.get("item_id")
                        if item_id:
                            await self._send_upstream({
                                "type": "conversation.item.delete",
                                "item_id": item_id,
                            })
                        logger.info(
                            "[%s] dropped hallucinated user transcript: %r",
                            self.session_id, user_text,
                        )
                        continue
                    await self.send_to_client({"type": "transcript.user", "text": user_text})
                    continue

                # 4) Tool calls — execute then send the result back upstream
                if etype == "response.function_call_arguments.done":
                    await self._handle_tool_call(event)
                    continue

                # 5) Speech detection events — useful for UI
                if etype in (
                    "input_audio_buffer.speech_started",
                    "input_audio_buffer.speech_stopped",
                    "response.created",
                ):
                    await self.send_to_client({"type": etype})
                    continue
                if etype == "response.done":
                    await self.send_to_client({"type": etype})
                    # Start the inactivity watchdog — if the user doesn't
                    # speak in the next N seconds we prompt the model to
                    # gracefully close the call.
                    self._arm_inactivity_timer()
                    continue

                if etype == "error":
                    err_msg = (event.get("error") or {}).get("message", "")
                    err_code = (event.get("error") or {}).get("code", "")
                    # Silence benign "no active response" errors that fire
                    # when we send response.cancel as a hallucination fence
                    # but there was nothing to cancel — those are expected
                    # and not user-visible failures.
                    benign = (
                        "no active response" in err_msg.lower()
                        or err_code == "response_cancel_not_active"
                    )
                    if benign:
                        logger.debug("[%s] benign upstream error: %s", self.session_id, err_msg)
                        continue
                    logger.error("[%s] upstream error: %s", self.session_id, event)
                    await self.send_to_client({"type": "error", "message": err_msg or "Error desconocido"})
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            logger.exception("[%s] upstream reader crashed: %s", self.session_id, e)
            await self.send_to_client({"type": "error", "message": str(e)})

    # ----------------------------------------------------------------- tools
    async def _handle_tool_call(self, event: dict) -> None:
        name = event.get("name", "")
        call_id = event.get("call_id", "")
        raw_args = event.get("arguments", "{}")
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except Exception:
            args = {}
        logger.info("[%s] tool call %s args=%s", self.session_id, name, args)

        # Special-case: end_call doesn't need pipeline execution. We must
        # GUARANTEE the user hears a goodbye before the line drops — the
        # realtime model sometimes calls end_call without speaking first,
        # which produces a jarring "silent hang-up". So after acknowledging
        # the tool call, we force a short farewell response.create with
        # explicit per-response instructions (overrides session prompt for
        # this response only), then schedule the close to fire after the
        # goodbye audio has had time to play out.
        if name == "end_call":
            await self.send_to_client({"type": "tool.result", "name": name, "result": {"ok": True}})
            await self._send_upstream({
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps({"ok": True}, ensure_ascii=False),
                },
            })
            # Only force a defensive farewell if the model HAS NOT already
            # said one in the same response. Without this guard the model
            # both speaks "Que tenga un buen día" AND we then ask it to
            # speak another farewell, producing two consecutive goodbyes
            # which sounds robotic and confusing.
            if not self._last_assistant_was_goodbye:
                await self._send_upstream({
                    "type": "response.create",
                    "response": {
                        "modalities": ["audio", "text"],
                        "instructions": (
                            "Despídete con UNA frase corta y cordial, sin llamar "
                            f"a ninguna otra función. Ejemplo: 'Muchas gracias por "
                            f"contactar con {BRAND_NAME}, que tenga un buen "
                            "día.' No añadas nada más."
                        ),
                    },
                })
                # 7 s gives the model time to finish the goodbye audio it
                # now produces in response to the response.create above
                # (typical length 2-3 s plus 1-2 s of upstream latency).
                delay = 7.0
            else:
                # The goodbye is already playing out on the client. Give
                # the audio queue enough time to drain before signalling
                # the hangup; the goodbye-phrase fallback in
                # response.audio_transcript.done has already scheduled a
                # 6 s close so this is mostly belt-and-braces.
                delay = 5.0
            # The client also waits for its playback queue to drain before
            # truly closing, so this is a soft signal not a hard cut.
            asyncio.create_task(self._delayed_close(delay))
            return

        fn = self.tools.get(name)
        if not fn:
            result: dict[str, Any] = {"error": f"unknown tool {name}"}
        else:
            # Hold-music for the long-running submit_claim
            if name == "submit_claim":
                await self.send_to_client({"type": "hold_music_start"})
            try:
                result = await fn(args)
            except Exception as e:  # noqa: BLE001
                logger.exception("[%s] tool %s failed", self.session_id, name)
                result = {"error": str(e)}
            finally:
                if name == "submit_claim":
                    await self.send_to_client({"type": "hold_music_stop"})
        # Notify the UI so the transcript pane can show "agent looking up
        # your DNI..." style hints.
        await self.send_to_client({
            "type": "tool.result",
            "name": name,
            "result": result,
        })
        # Persist key tool results in the bridge state so other endpoints
        # (e.g. the operator sessions list) can display call metadata
        # without re-doing the lookup.
        if name == "lookup_customer" and isinstance(result, dict) and result.get("customer_id"):
            self.state["customer"] = result
        elif name == "submit_claim" and isinstance(result, dict):
            self.state["last_decision"] = result
        # Push the result back to the realtime conversation
        await self._send_upstream({
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False),
            },
        })
        # Tell the model to continue speaking
        await self._send_upstream({
            "type": "response.create",
            "response": {"modalities": ["audio", "text"]},
        })

    async def _delayed_close(self, delay_s: float) -> None:
        """Wait for the goodbye audio to finish, then ask the client to hang up.

        We just signal the client; the client knows exactly how much audio
        is still queued in its playback buffer and will close the WS once
        the queue drains.
        """
        if self._hangup_scheduled:
            return
        self._hangup_scheduled = True
        try:
            await asyncio.sleep(delay_s)
            await self.send_to_client({"type": "hangup"})
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------- inactivity watchdog
    def _cancel_inactivity_timer(self) -> None:
        if self._inactivity_task and not self._inactivity_task.done():
            self._inactivity_task.cancel()
        self._inactivity_task = None

    def _arm_inactivity_timer(self) -> None:
        self._cancel_inactivity_timer()
        if self._closed or self._hangup_scheduled:
            return
        self._inactivity_task = asyncio.create_task(self._inactivity_watchdog())

    async def _inactivity_watchdog(self) -> None:
        try:
            await asyncio.sleep(self.INACTIVITY_TIMEOUT_S)
            if self._closed or self._hangup_scheduled:
                return
            logger.info(
                "[%s] no user audio in %.0fs, asking the model to close politely",
                self.session_id, self.INACTIVITY_TIMEOUT_S,
            )
            # Inject a system-style cue. The model will respond with a
            # short farewell + call end_call (which schedules the actual
            # close via _delayed_close).
            await self._send_upstream({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{
                        "type": "input_text",
                        "text": (
                            "[Sistema: el cliente lleva varios segundos sin responder. "
                            "Despídete brevemente con una frase amable y llama "
                            "INMEDIATAMENTE a la función end_call para colgar."
                        )}],
                },
            })
            await self._send_upstream({
                "type": "response.create",
                "response": {"modalities": ["audio", "text"]},
            })
        except asyncio.CancelledError:
            pass
        except Exception as e:  # noqa: BLE001
            logger.debug("[%s] inactivity watchdog failed: %s", self.session_id, e)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
def build_tools(*, lookup_customer_impl: Callable[[str], dict | None],
                submit_claim_impl: Callable[[dict], Awaitable[dict]]) -> dict[str, ToolFn]:
    """Factory that wires the realtime tools to concrete implementations.

    Allows the backend to pass in its own customer store and pipeline
    function (so this module stays decoupled from FastAPI / claims_store).
    """

    async def lookup_customer(args: dict) -> dict:
        dni = (args.get("dni") or "").upper().replace("-", "").replace(" ", "")
        found = lookup_customer_impl(dni)
        if not found:
            return {"found": False, "dni": dni}
        return {
            "found": True,
            "dni": dni,
            "customer_id": found.get("customer_id"),
            "name": found.get("name"),
            "policy_id": found.get("policy_id"),
            "vehicle": found.get("vehicle"),
            "coverage_type": found.get("coverage_type"),
        }

    async def submit_claim(args: dict) -> dict:
        return await submit_claim_impl(args)

    return {
        "lookup_customer": lookup_customer,
        "submit_claim": submit_claim,
    }


# ---------------------------------------------------------------------------
# Whisper hallucination filter
# ---------------------------------------------------------------------------
# Whisper is famous for "filling in" silence with phrases mined from its
# training data (YouTube subtitles, podcast outros, etc.). We drop any
# user transcript that matches one of these well-known invented strings
# (or is too short to be meaningful). List sourced from observed
# hallucinations + public Whisper-bug threads (openai/whisper#928, etc).
_HALLUCINATION_PATTERNS = {
    # Amara / open-subtitles signatures
    "subtítulos realizados por la comunidad de amara.org",
    "subtítulos por la comunidad de amara.org",
    "subtítulos por la comunidad amara.org",
    "subtitulos realizados por la comunidad de amara.org",
    "subtítulos en español",
    "amara.org",
    "subtitulado por la comunidad",
    "subtitulos por aramá.org",
    "transcripción realizada por aramá.org",
    # YouTube / podcast filler
    "gracias",
    "gracias por ver el video",
    "gracias por ver",
    "gracias a todos",
    "ahora vamos",
    "thank you for watching",
    "thanks for watching",
    "thank you",
    "subscríbete",
    "suscríbete",
    "muchas gracias",
    "hasta la próxima",
    "nos vemos en el próximo",
    # Random URL / spam phrases Whisper sometimes inserts on silence
    "más información www.alimmenta.com",
    "más información en alimmenta.com",
    "alimmenta.com",
    "para más información",
    "para más información visite",
    "para más información visite www",
    "para más información, visite www",
    "puedes encontrar más información",
    "puedes encontrar más información en",
    "visita www",
    "para más vídeos",
    "para más videos",
    "más videos en",
    "más vídeos en",
    "para más contenido",
    "como suscribirse",
    "como suscribirte",
    "subscríbete al canal",
    "suscríbete al canal",
    "comparte el vídeo",
    "comparte el video",
    "dale like",
    "dale me gusta",
    ".com",
    "www.",
}


# Spanish digit-words. When the user spells out a DNI / policy number / phone
# number, immediate word repetitions ("uno uno dos dos tres tres") are NORMAL
# and must not trigger the repetition heuristic. Same applies to spelled
# letters at the end of a DNI ("...cuatro C").
_DIGIT_WORDS = {
    "cero", "uno", "dos", "tres", "cuatro", "cinco",
    "seis", "siete", "ocho", "nueve", "diez",
}

# Strong "this is a real user identifier" markers. If a transcript contains
# any of these tokens we skip the repetition heuristic entirely, since the
# user is clearly providing structured data.
_IDENTIFIER_MARKERS = (
    "dni", "nie", "póliza", "poliza", "matrícula", "matricula",
    "teléfono", "telefono", "número", "numero", "código", "codigo",
    "cuenta", "iban", "expediente", "siniestro",
)


def is_user_transcript_hallucination(text: str) -> bool:
    """Return True if a Whisper transcript looks like a known hallucination
    pattern rather than real user speech. Filters very short/empty inputs,
    the well-known training-data filler phrases, and obvious repetition
    artefacts ("un saludo y un saludo").

    NOTE: short legitimate answers like "sí" / "no" / "vale" are NOT
    filtered, even though Whisper sometimes hallucinates them. The audio
    gates (echo + server VAD) are the first line of defence for those; if a
    real user really only said "sí" we want to act on it.

    NOTE: when the user is spelling a DNI/policy/phone/etc, immediate digit
    repetitions ("uno uno dos dos tres tres") are LEGITIMATE input and must
    not be treated as Whisper loops. We detect this by skipping the
    repetition heuristic whenever the transcript contains an identifier
    marker ("dni", "póliza", ...) or digit-words.
    """
    if not text:
        return True
    norm = text.strip().lower().rstrip(" .!?¡¿,;")
    if not norm:
        return True
    if len(norm) < 2:
        return True
    if norm in _HALLUCINATION_PATTERNS:
        return True
    # Substring match only for the long signature phrases (URLs, channel
    # promo lines, subtitle-credit boilerplate) — never short generic words.
    if any(p in norm for p in _HALLUCINATION_PATTERNS if len(p) > 10):
        return True
    words = norm.split()
    # Skip ALL the repetition heuristics if the user is spelling out a
    # structured identifier — DNIs, policy numbers, phone numbers, IBANs all
    # naturally produce immediate word repeats and unique-word ratios that
    # would otherwise be flagged. This is the highest-priority signal: a
    # mention of "DNI" + digit-words is almost certainly real user input.
    has_identifier_marker = any(m in norm for m in _IDENTIFIER_MARKERS)
    digit_word_count = sum(1 for w in words if w in _DIGIT_WORDS)
    if has_identifier_marker or digit_word_count >= 3:
        return False
    # Repetition artefact: Whisper sometimes loops on silence ("hola hola
    # hola hola" / "a todos a todos a todos"). We only flag the unambiguous
    # case: a high ratio of IMMEDIATE consecutive word repeats. Natural
    # Spanish descriptions reuse nouns ("el parachoques delantero ... el
    # parachoques trasero"), so generic bigram-duplicate detection produces
    # too many false positives and was previously dropping legitimate
    # accident descriptions wholesale.
    if len(words) >= 4:
        non_digit = [w for w in words if w not in _DIGIT_WORDS]
        if len(non_digit) >= 4:
            repeats = sum(
                1 for i in range(1, len(non_digit))
                if non_digit[i] == non_digit[i - 1]
            )
            if repeats / len(non_digit) > 0.30:
                return True
    # YouTube intro signatures (informal greetings of a streamer not a
    # claim caller). These almost never appear in a real claim call.
    intro_signatures = (
        "a todos los que",
        "para todos los que",
        "hola a todos",
        "hola chic",  # "chicos/chicas"
        "buenas a todos",
        "que están por",
        "y un saludo",
    )
    if any(sig in norm for sig in intro_signatures):
        return True
    return False


# ---------------------------------------------------------------------------
# Goodbye-phrase detector — backup for the end_call tool
# ---------------------------------------------------------------------------
# Sometimes the realtime model produces a polished closing phrase but forgets
# to invoke the end_call tool. We sniff the assistant's spoken transcript
# and auto-hangup when we see a clear goodbye signature so the customer
# isn't left holding an open line.
_GOODBYE_PHRASES = (
    "que tenga buen día",
    "que tenga un buen día",
    "que tenga buen dia",
    "que pase un buen día",
    "voy a finalizar la llamada",
    "voy a colgar",
    "muchas gracias por contactar",
    "gracias por contactar con",
    "un agente le contactará",
    "un agente le llamará",
    "un agente se pondrá en contacto",
    "le deseo un buen día",
    "hasta luego",
    "hasta pronto",
    "que tenga un buen resto de día",
)


def _looks_like_goodbye(text: str) -> bool:
    if not text:
        return False
    norm = text.strip().lower()
    return any(phrase in norm for phrase in _GOODBYE_PHRASES)


def format_spoken_decision(decision_dict: dict) -> str:
    """Compose the natural-language line the model will read out.

    Customer-facing — we deliberately strip all internal reasoning, risk
    score detail and amount thresholds from rejection messages so we don't
    leak business rules through the voice channel. Approvals can be
    explicit because the customer benefits from the information.
    """
    decision = (decision_dict.get("decision") or "").lower()
    if decision == "approve":
        return (
            "Su parte ha sido aprobado automáticamente. "
            "Recibirá una notificación por email en los próximos minutos con "
            "el desglose del pago y los siguientes pasos."
        )
    if decision == "reject":
        return (
            "Lo siento, su parte no ha podido ser aprobado en este momento. "
            "Si considera que es un error, por favor contacte con nuestro "
            "equipo de atención al cliente y un agente lo revisará en detalle."
        )
    if decision == "human_review":
        return (
            "Su caso requiere una revisión adicional por parte de un "
            "agente humano. Un especialista le contactará en menos de "
            "24 horas para revisar el caso en detalle."
        )
    return (
        "Hemos registrado su parte y estamos procesándolo. "
        "Le contactaremos pronto con la resolución."
    )
