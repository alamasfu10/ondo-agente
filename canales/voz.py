"""Habla con el agente de Ondo por voz: en el navegador o por teléfono.

    python -m canales.voz                      # navegador: abre http://localhost:7860 y pulsa Connect
    python -m canales.voz --como-chat          # el agente del chat, tal cual: redacta para leer y no avisa al esperar
    python -m canales.voz --voz elevenlabs     # la misma llamada con una voz de ElevenLabs (clave y voz en el .env)
    python -m canales.voz -t twilio -x xxxx.ngrok-free.dev    # teléfono con Twilio (demo del docente)

Es una cascada de Pipecat. El audio entra por el transporte, el STT lo
transcribe, el agregador decide cuándo ha terminado de hablar el cliente, el
agente de Ondo (el mismo grafo del chat) decide qué responder y el TTS lo
convierte en voz:

    transporte → STT → turno del cliente → AgenteOndo → TTS → transporte

El grafo no cambia: entra como un procesador más que recibe el texto del
cliente y devuelve el texto que se dice. Lo único que cambia con la voz es
cómo se redacta (el prompt de voz de agente/llm.py).

Cada llamada tiene su propio AgenteOndo, con su servidor MCP y su thread_id.
"""

import argparse
import asyncio
import os
import sys
import time
import uuid
from datetime import date

from agente.agente import AgenteOndo  # carga el .env antes que los servicios de voz
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TTSSpeakFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.runner.types import RunnerArguments, SmallWebRTCRunnerArguments
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.transcriptions.language import Language
from pipecat.workers.runner import WorkerRunner

from canales import persona

# Lo que el cliente oye si el agente tarda en responder (consultar una herramienta, dos llamadas al modelo...).
FRASE_DE_ESPERA = "Un momento, lo miro."
ESPERA_ANTES_DE_LA_FRASE = 2.0  # segundos; cada turno hace dos llamadas al modelo y suele tardar de 2 a 3

# Palabras que el reconocimiento de voz no conoce y tiene que acertar.
VOCABULARIO = ["Ondo", "Ondo Brisa", "Ondo Urbana", "Ondo Trail", "OND", "Brisa"]

SALUDO = "Hola"  # el agente saluda como si el cliente hubiera dicho «Hola» al descolgar

VOCES = ("openai", "elevenlabs")

# OpenAI retira gpt-4o-mini-tts, la voz por defecto, el 6/01/2027 (guía «Text to speech» de OpenAI).
RETIRADA_VOZ_OPENAI = date(2027, 1, 6)
AVISO_VOZ_OPENAI = (
    "OpenAI retira el 6/01/2027 la voz que usa el kit (gpt-4o-mini-tts). Usa la de ElevenLabs: "
    "cuenta gratuita en elevenlabs.io, ELEVENLABS_API_KEY y ELEVENLABS_VOICE_ID en el .env, y "
    "python -m canales.voz --voz elevenlabs"
)


def voz_retirada(voz: str, hoy: date | None = None) -> bool:
    """True si se pide la voz de OpenAI cuando ya está retirada."""
    return voz == "openai" and (hoy or date.today()) >= RETIRADA_VOZ_OPENAI


def falta_para_la_voz(voz: str) -> list[str]:
    """Variables del .env que faltan para usar esa voz."""
    necesarias = {"openai": ["OPENAI_API_KEY"], "elevenlabs": ["ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"]}[voz]
    return [v for v in necesarias if not os.getenv(v)]


def crear_tts(voz: str = "openai"):
    """La síntesis de voz: la pieza que convierte la respuesta en audio. Lo demás de la tubería no cambia."""
    if voz == "elevenlabs":
        # Voces de la biblioteca de ElevenLabs o una voz propia; flash es su modelo de menos latencia.
        return ElevenLabsTTSService(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            settings=ElevenLabsTTSService.Settings(
                voice=os.getenv("ELEVENLABS_VOICE_ID"),
                model=os.getenv("ELEVENLABS_MODEL", "eleven_flash_v2_5"),
            ),
        )
    return OpenAITTSService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAITTSService.Settings(
            voice="coral",
            instructions="Habla en español de España, con un tono cercano, claro y sin prisa.",
        ),
    )


class AgenteOndoVoz(FrameProcessor):
    """Mete el grafo de Ondo en el pipeline: recibe el turno del cliente y devuelve la respuesta en texto."""

    def __init__(self, agente: AgenteOndo, conversacion: str, como_chat: bool = False, al_escalar=None):
        super().__init__()
        self.agente = agente
        self.conversacion = conversacion
        self.canal = "chat" if como_chat else "voz"
        self.frase_de_espera = not como_chat
        self.al_escalar = al_escalar
        self._caso_avisado = None

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMContextFrame):
            texto = ultimo_mensaje_del_cliente(frame.context)
            await self.turno(texto, frase_de_espera=self.frase_de_espera and texto != SALUDO)
        else:
            await self.push_frame(frame, direction)

    async def turno(self, texto: str, frase_de_espera: bool = True):
        if not texto:
            return
        logger.info(f"Cliente: {texto}")
        inicio = time.perf_counter()
        tarea = asyncio.create_task(self.agente.responder(self.conversacion, texto, canal=self.canal))
        try:
            try:
                r = await asyncio.wait_for(asyncio.shield(tarea), ESPERA_ANTES_DE_LA_FRASE if frase_de_espera else None)
            except TimeoutError:
                logger.info(f"Frase de espera: {FRASE_DE_ESPERA}")
                await self.push_frame(TTSSpeakFrame(FRASE_DE_ESPERA))
                r = await tarea
        finally:
            if not tarea.done():  # el cliente ha interrumpido: el turno se descarta
                tarea.cancel()
        logger.info(f"Agente ({time.perf_counter() - inicio:.1f} s): {r.texto}")
        await self.push_frame(LLMFullResponseStartFrame())
        await self.push_frame(LLMTextFrame(r.texto))
        await self.push_frame(LLMFullResponseEndFrame())

        caso = r.estado.get("escalado")
        if caso and caso.get("id") != self._caso_avisado:
            self._caso_avisado = caso.get("id")
            logger.info(f"Caso {caso.get('id')} para una persona: {caso.get('resumen')}")
            if self.al_escalar:
                await self.al_escalar(caso)


class TrasHablar(FrameProcessor):
    """Ejecuta una acción cuando el agente termina de decir su respuesta (por ejemplo, transferir la llamada)."""

    def __init__(self):
        super().__init__()
        self.accion = None
        self._hablando = False

    def programar(self, accion):
        self.accion = accion
        self._hablando = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if self.accion and isinstance(frame, BotStartedSpeakingFrame):
            self._hablando = True
        elif self.accion and self._hablando and isinstance(frame, BotStoppedSpeakingFrame):
            accion, self.accion = self.accion, None
            await accion()
        await self.push_frame(frame, direction)


def ultimo_mensaje_del_cliente(context: LLMContext) -> str:
    """Lo que ha dicho el cliente desde la última respuesta que llegó a oír.

    Si el cliente hace una pausa a mitad de frase, el turno se cierra, el agente
    empieza a pensar y la segunda parte le interrumpe. La respuesta interrumpida
    no se llega a decir, así que las dos partes se juntan en un solo mensaje.
    """
    partes = []
    for m in reversed(context.get_messages()):
        if not isinstance(m, dict):
            continue
        if m.get("role") == "assistant":
            break
        if m.get("role") == "user":
            contenido = m.get("content")
            if isinstance(contenido, list):
                contenido = " ".join(p.get("text", "") for p in contenido if isinstance(p, dict))
            partes.append((contenido or "").strip())
    return " ".join(p for p in reversed(partes) if p)


async def crear_transporte(runner_args: RunnerArguments):
    """Navegador (WebRTC) o teléfono (Twilio por WebSocket). Devuelve el transporte y el id de la llamada."""
    if isinstance(runner_args, SmallWebRTCRunnerArguments):
        from pipecat.transports.base_transport import TransportParams
        from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

        params = TransportParams(audio_in_enabled=True, audio_out_enabled=True)
        return SmallWebRTCTransport(webrtc_connection=runner_args.webrtc_connection, params=params), None

    from pipecat.runner.utils import parse_telephony_websocket
    from pipecat.serializers.twilio import TwilioFrameSerializer
    from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams, FastAPIWebsocketTransport

    # Los dos primeros mensajes de Twilio dicen qué llamada es (callSid) y qué stream de audio (streamSid).
    _, llamada = await parse_telephony_websocket(runner_args.websocket)
    serializador = TwilioFrameSerializer(
        stream_sid=llamada["stream_id"],
        call_sid=llamada["call_id"],
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        # No colgar al terminar el pipeline: si la llamada pasa a una persona, tiene que seguir viva.
        params=TwilioFrameSerializer.InputParams(auto_hang_up=False),
    )
    params = FastAPIWebsocketParams(
        audio_in_enabled=True, audio_out_enabled=True, add_wav_header=False, serializer=serializador
    )
    return FastAPIWebsocketTransport(websocket=runner_args.websocket, params=params), llamada["call_id"]


async def bot(runner_args: RunnerArguments):
    """Una llamada: Pipecat la llama cada vez que alguien conecta desde el navegador o llama por teléfono."""
    cli = getattr(runner_args, "cli_args", None)
    como_chat = getattr(cli, "como_chat", False)
    voz = getattr(cli, "voz", "openai")
    transporte, call_sid = await crear_transporte(runner_args)
    conversacion = f"llamada-{call_sid or uuid.uuid4().hex[:8]}"

    stt = OpenAISTTService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAISTTService.Settings(language=Language.ES, keywords=VOCABULARIO),
    )
    tts = crear_tts(voz)

    contexto = LLMContext()
    turno_cliente, turno_agente = LLMContextAggregatorPair(
        contexto, user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer())
    )
    tras_hablar = TrasHablar()

    async def al_escalar(caso: dict):
        persona.registrar(call_sid or conversacion, caso)
        if call_sid and persona.configurada():
            tras_hablar.programar(lambda: persona.transferir(call_sid))

    async with AgenteOndo() as agente:
        ondo = AgenteOndoVoz(agente, conversacion, como_chat, al_escalar)
        pipeline = Pipeline([
            transporte.input(),   # audio del cliente
            stt,                  # voz → texto
            turno_cliente,        # espera a que el cliente termine su turno
            ondo,                 # el grafo de Ondo decide qué responder
            tts,                  # texto → voz
            transporte.output(),  # audio al cliente
            tras_hablar,          # cuando termina de hablar: transferir, si toca
            turno_agente,         # guarda lo que el agente ha dicho
        ])
        worker = PipelineWorker(pipeline, params=PipelineParams(enable_metrics=True))
        runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)
        await runner.add_workers(worker)

        @transporte.event_handler("on_client_connected")
        async def al_conectar(transport, client):
            logger.info(f"Llamada conectada ({conversacion}, {'como en el chat' if como_chat else 'prompt de voz'}, "
                        f"voz de {voz})")
            await ondo.queue_frame(LLMContextFrame(_contexto_saludo()))

        @transporte.event_handler("on_client_disconnected")
        async def al_colgar(transport, client):
            logger.info("Llamada terminada")
            await runner.cancel()

        await runner.run()


def _contexto_saludo() -> LLMContext:
    c = LLMContext()
    c.add_message({"role": "user", "content": SALUDO})
    return c


if __name__ == "__main__":
    from pipecat.runner.run import main

    parser = argparse.ArgumentParser(description="Agente de Ondo por voz")
    parser.add_argument("--como-chat", action="store_true",
                        help="el agente del chat tal cual: redacta para leer y no dice la frase de espera")
    parser.add_argument("--voz", choices=VOCES, default="openai",
                        help="quién genera la voz del agente: OpenAI (por defecto) o ElevenLabs")
    elegida = parser.parse_known_args()[0].voz
    if faltan := falta_para_la_voz(elegida):
        sys.exit(f"Para usar la voz de {elegida} faltan en el .env: {', '.join(faltan)}")
    if voz_retirada(elegida):
        logger.warning(AVISO_VOZ_OPENAI)
    persona.montar_rutas()
    main(parser)
