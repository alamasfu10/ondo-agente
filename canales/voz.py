"""Habla con el agente de Ondo por voz, en el navegador.

    python -m canales.voz                      # abre http://localhost:7860/client y pulsa Connect
    python -m canales.voz --traza              # los frames de cada turno, con su hora (canales/observar.py)
    python -m canales.voz --tiempos            # en qué se va el tiempo de cada respuesta
    python -m canales.voz --como-chat          # el agente del chat, tal cual: redacta para leer y no avisa al esperar
    python -m canales.voz --voz elevenlabs     # la misma conversación con una voz de ElevenLabs (clave y voz en el .env)

Es una cascada de Pipecat. El audio entra por el transporte, el STT lo
transcribe, el agregador decide cuándo ha terminado de hablar el cliente, el
agente de Ondo (el mismo grafo del chat) decide qué responder y el TTS lo
convierte en voz:

    transporte → STT → turno del cliente → AgenteOndo → TTS → transporte

El grafo no cambia: entra como un procesador más que recibe el texto del
cliente y devuelve el texto que se dice. Lo único que cambia con la voz es
cómo se redacta (el prompt de voz de agente/llm.py).

Es la cascada de practica/cascada_minima.py con dos cambios: en lugar del LLM
va AgenteOndoVoz, y el turno del cliente lleva el detector de fin de turno por
significado y el límite de lo que el cliente puede decir sin dejar contestar.

Cada conversación tiene su propio AgenteOndo, con su servidor MCP y su thread_id.
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
from pipecat.audio.vad.vad_analyzer import VADParams
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
from pipecat.runner.types import RunnerArguments
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.turns.user_mute.base_user_mute_strategy import BaseUserMuteStrategy
from pipecat.turns.user_stop.base_user_turn_stop_strategy import BaseUserTurnStopStrategy
from pipecat.turns.user_stop.speech_timeout_user_turn_stop_strategy import SpeechTimeoutUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import (
    StrategyMode,
    UserTurnStrategies,
    UserTurnStrategiesParams,
    default_user_turn_stop_strategies,
)
from pipecat.workers.runner import WorkerRunner

from canales.observar import observadores

# Lo que el cliente oye si el agente tarda en responder (consultar una herramienta, dos llamadas al modelo...).
FRASE_DE_ESPERA = "Un momento, lo miro."
ESPERA_ANTES_DE_LA_FRASE = 2.0  # segundos; cada turno hace dos llamadas al modelo y suele tardar de 2 a 3

# Palabras que el reconocimiento de voz no conoce y tiene que acertar.
VOCABULARIO = ["Ondo", "Ondo Brisa", "Ondo Urbana", "Ondo Trail", "OND", "Brisa"]

SALUDO = "Hola"  # el agente saluda como si el cliente hubiera dicho «Hola» al conectar

# Cuándo termina el turno del cliente. El detector de voz (Silero) marca que ha dejado de oír voz tras
# SILENCIO_DETECTOR segundos de silencio. Después decide la estrategia de fin de turno:
#   "significado": el modelo smart turn v3 escucha el final de la frase y decide si suena a terminada
#                  (una pausa tras «quiero cambiar la cita del...» no cierra el turno).
#   "silencio":    el turno se cierra tras SILENCIO_FIN_DE_TURNO segundos sin voz nueva, diga lo que diga.
SILENCIO_DETECTOR = 0.2
FIN_DE_TURNO = "significado"
SILENCIO_FIN_DE_TURNO = 0.6

# Límite de lo que el cliente puede decir sin dejar contestar al agente. Con un podcast o una tele de fondo
# no hay un turno de diez minutos: hay muchos turnos cortos que interrumpen al agente una y otra vez.
# Por eso se cuentan dos cosas: un turno de más de 30 s seguidos, o más de 70 palabras acumuladas desde la
# última respuesta que el cliente llegó a oír. Al pasarse, el agente corta, pide que se lo resuman, no
# manda ese texto al grafo (ni gasta tokens en él) y no se deja interrumpir mientras lo dice.
MAX_SEGUNDOS_TURNO = 30
MAX_PALABRAS_TURNO = 70
FRASE_TURNO_LARGO = "Perdona, me he perdido: es mucho a la vez. ¿Me lo cuentas en una frase?"

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


class LimiteDeTurno:
    """Estado compartido entre el corte del turno y el silencio que lo sigue."""

    def __init__(self, segundos: float = MAX_SEGUNDOS_TURNO, palabras: int = MAX_PALABRAS_TURNO):
        self.segundos = segundos
        self.palabras = palabras
        self.silenciar = False   # True desde el corte hasta que el agente termina de decir la frase
        self.cortes = 0


class CorteDeTurno(BaseUserTurnStopStrategy):
    """Cierra el turno del cliente si dura más de `limite.segundos`, aunque no haya terminado de hablar.

    Se suma a la estrategia normal (el detector de fin de turno): el turno acaba con la primera que decida.
    Al cortar, el agente dice FRASE_TURNO_LARGO y la entrada se silencia mientras la dice.
    """

    def __init__(self, limite: LimiteDeTurno):
        super().__init__()
        self.limite = limite
        self._tarea: asyncio.Task | None = None

    async def handle_user_turn_started(self):
        self._cancelar()
        self._tarea = asyncio.create_task(self._esperar())

    async def handle_user_turn_stopped(self):
        self._cancelar()

    async def cleanup(self):
        self._cancelar()

    def _cancelar(self):
        if self._tarea and not self._tarea.done() and self._tarea is not asyncio.current_task():
            self._tarea.cancel()
        self._tarea = None

    async def _esperar(self):
        await asyncio.sleep(self.limite.segundos)
        self.limite.cortes += 1
        self.limite.silenciar = True
        logger.info(f"Turno cortado: el cliente lleva más de {self.limite.segundos:.0f} s hablando")
        await self.push_frame(TTSSpeakFrame(FRASE_TURNO_LARGO))
        await self.report_user_turn_stopped()


class SilencioTrasCorte(BaseUserMuteStrategy):
    """Ignora la entrada desde el corte hasta que el agente termina de decir la frase."""

    def __init__(self, limite: LimiteDeTurno):
        super().__init__()
        self.limite = limite
        self._hablando = False

    async def process_frame(self, frame: Frame) -> bool:
        await super().process_frame(frame)
        if not self.limite.silenciar:
            return False
        if isinstance(frame, BotStartedSpeakingFrame):
            self._hablando = True
        elif isinstance(frame, BotStoppedSpeakingFrame) and self._hablando:
            self._hablando = False
            self.limite.silenciar = False
            return False
        return True


def estrategias_de_fin_de_turno(fin_de_turno: str = FIN_DE_TURNO) -> list[BaseUserTurnStopStrategy]:
    """Quién decide que el cliente ha terminado: el modelo de fin de turno o un temporizador de silencio."""
    if fin_de_turno == "silencio":
        return [SpeechTimeoutUserTurnStopStrategy(user_speech_timeout=SILENCIO_FIN_DE_TURNO)]
    return default_user_turn_stop_strategies()  # smart turn v3, en local


def parametros_de_turno(limite: LimiteDeTurno, fin_de_turno: str = FIN_DE_TURNO) -> LLMUserAggregatorParams:
    """Detector de voz, fin de turno (por significado o por silencio) más el corte por duración, y el silencio
    que sigue al corte."""
    return LLMUserAggregatorParams(
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=SILENCIO_DETECTOR)),
        user_turn_strategies=UserTurnStrategies(stop=[*estrategias_de_fin_de_turno(fin_de_turno), CorteDeTurno(limite)]),
        user_turn_strategies_params=UserTurnStrategiesParams(stop_mode=StrategyMode.FIRST),
        user_mute_strategies=[SilencioTrasCorte(limite)],
    )


def demasiado_largo(texto: str, palabras: int = MAX_PALABRAS_TURNO) -> bool:
    return len(texto.split()) > palabras


class AgenteOndoVoz(FrameProcessor):
    """Mete el grafo de Ondo en el pipeline: recibe el turno del cliente y devuelve la respuesta en texto."""

    def __init__(self, agente: AgenteOndo, conversacion: str, como_chat: bool = False,
                 limite: LimiteDeTurno | None = None):
        super().__init__()
        self.limite = limite or LimiteDeTurno()
        self.agente = agente
        self.conversacion = conversacion
        self.canal = "chat" if como_chat else "voz"
        self.frase_de_espera = not como_chat
        self._caso_avisado = None

    def can_generate_metrics(self) -> bool:
        return True  # mide lo que tarda el grafo, como mide el LLM de la cascada mínima (--tiempos)

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
        if demasiado_largo(texto, self.limite.palabras):  # lo que no deja contestar no llega al grafo
            logger.info(f"Turno cortado: {len(texto.split())} palabras sin dejar contestar; no se manda al grafo")
            self.limite.cortes += 1
            self.limite.silenciar = True
            await self.push_frame(TTSSpeakFrame(FRASE_TURNO_LARGO))
            return
        logger.info(f"Cliente: {texto}")
        inicio = time.perf_counter()
        # Como un LLM: se anuncia que empieza la respuesta y se mide hasta que el texto está listo. El grafo
        # devuelve la respuesta entera de una vez (un solo LLMTextFrame), no trozo a trozo.
        await self.push_frame(LLMFullResponseStartFrame())
        await self.start_ttfb_metrics()
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
        await self.stop_ttfb_metrics()
        logger.info(f"Agente ({time.perf_counter() - inicio:.1f} s): {r.texto}")
        await self.push_frame(LLMTextFrame(r.texto))
        await self.push_frame(LLMFullResponseEndFrame())

        caso = r.estado.get("escalado")
        if caso and caso.get("id") != self._caso_avisado:
            self._caso_avisado = caso.get("id")
            logger.info(f"Caso {caso.get('id')} para una persona: {caso.get('resumen')}")


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


async def bot(runner_args: RunnerArguments):
    """Una conversación: Pipecat la llama cada vez que alguien pulsa Connect en el navegador."""
    cli = runner_args.cli_args
    transporte = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    conversacion = f"voz-{uuid.uuid4().hex[:8]}"

    stt = OpenAISTTService(
        api_key=os.getenv("OPENAI_API_KEY"),
        settings=OpenAISTTService.Settings(language=Language.ES, keywords=VOCABULARIO),
    )
    tts = crear_tts(cli.voz)

    limite = LimiteDeTurno()
    contexto = LLMContext()
    turno_cliente, turno_agente = LLMContextAggregatorPair(contexto, user_params=parametros_de_turno(limite))

    async with AgenteOndo() as agente:
        ondo = AgenteOndoVoz(agente, conversacion, cli.como_chat, limite)
        pipeline = Pipeline([
            transporte.input(),   # audio del cliente
            stt,                  # voz → texto
            turno_cliente,        # espera a que el cliente termine su turno
            ondo,                 # el grafo de Ondo decide qué responder
            tts,                  # texto → voz
            transporte.output(),  # audio al cliente
            turno_agente,         # guarda lo que el agente ha dicho
        ])
        worker = PipelineWorker(
            pipeline,
            params=PipelineParams(enable_metrics=True),
            observers=observadores(traza=cli.traza, tiempos=cli.tiempos),
        )
        runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)
        await runner.add_workers(worker)

        @transporte.event_handler("on_client_connected")
        async def al_conectar(transport, client):
            logger.info(f"Conectado ({conversacion}, {'como en el chat' if cli.como_chat else 'prompt de voz'}, "
                        f"voz de {cli.voz}, fin de turno por {FIN_DE_TURNO})")
            await ondo.queue_frame(LLMContextFrame(_contexto_saludo()))

        @transporte.event_handler("on_client_disconnected")
        async def al_colgar(transport, client):
            logger.info("Conversación terminada")
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
    parser.add_argument("--traza", action="store_true", help="imprime los frames de cada turno")
    parser.add_argument("--tiempos", action="store_true", help="imprime en qué se va el tiempo de cada respuesta")
    elegida = parser.parse_known_args()[0].voz
    if faltan := falta_para_la_voz(elegida):
        sys.exit(f"Para usar la voz de {elegida} faltan en el .env: {', '.join(faltan)}")
    if voz_retirada(elegida):
        logger.warning(AVISO_VOZ_OPENAI)
    main(parser)
