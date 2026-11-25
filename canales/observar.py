"""Mirar dentro de la tubería de voz: qué frames pasan en cada turno y en qué se va el tiempo.

Un observador de Pipecat ve cada frame que un procesador empuja al siguiente,
sin tocarlo ni retrasarlo. Los dos de este fichero sirven para entender la
tubería, no para producción:

    --traza    TrazaDeVoz: una línea por frame importante, con la hora y quién lo empuja a quién.
    --tiempos  tiempos_por_tramo(): al empezar a sonar cada respuesta, cuánto ha tardado cada tramo
               desde que el cliente dejó de hablar (usa el UserBotLatencyObserver de Pipecat).

Los usan canales/voz.py y practica/cascada_minima.py.
"""

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InterimTranscriptionFrame,
    InterruptionFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSSpeakFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    UserMuteStartedFrame,
    UserMuteStoppedFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.observers.user_bot_latency_observer import LatencyBreakdown, UserBotLatencyObserver
from pipecat.processors.frame_processor import FrameDirection

# Los frames que cuentan la historia de un turno, con lo que significan. El resto (sobre todo el audio,
# que pasa en trozos de 20 ms) no se imprime.
QUE_ES = {
    VADUserStartedSpeakingFrame: "el detector de voz oye hablar al cliente",
    UserStartedSpeakingFrame: "empieza el turno del cliente",
    InterimTranscriptionFrame: "transcripción provisional",
    TranscriptionFrame: "transcripción",
    VADUserStoppedSpeakingFrame: "el detector de voz deja de oír al cliente",
    UserStoppedSpeakingFrame: "termina el turno del cliente",
    LLMContextFrame: "la conversación entera va al cerebro",
    LLMFullResponseStartFrame: "empieza la respuesta",
    LLMTextFrame: "primer trozo de texto de la respuesta",
    LLMFullResponseEndFrame: "termina la respuesta",
    TTSSpeakFrame: "frase fija para decir, sin pasar por el cerebro",
    TTSStartedFrame: "la síntesis empieza",
    TTSAudioRawFrame: "primer audio de la respuesta",
    TTSStoppedFrame: "la síntesis termina",
    BotStartedSpeakingFrame: "el agente empieza a sonar",
    BotStoppedSpeakingFrame: "el agente termina de sonar",
    InterruptionFrame: "interrupción: si el agente estaba pensando o hablando, lo deja",
    UserMuteStartedFrame: "se deja de escuchar al cliente",
    UserMuteStoppedFrame: "se vuelve a escuchar al cliente",
}


def _imprimir(linea: str):
    print(linea, flush=True)  # sin esperar: la traza tiene que salir a la vez que pasa


def _nombre(procesador) -> str:
    return getattr(procesador, "name", type(procesador).__name__)


class TrazaDeVoz(BaseObserver):
    """Imprime los frames de QUE_ES la primera vez que pasan, con los segundos desde que empezó la llamada.

    Del texto y del audio de cada respuesta solo imprime el primer trozo: son decenas o cientos.
    """

    def __init__(self, imprimir=_imprimir):
        super().__init__()
        self.imprimir = imprimir
        self._vistos: set[int] = set()
        self._inicio: int | None = None
        self._anterior: int | None = None
        self._texto_dicho = False   # ya se ha impreso el primer LLMTextFrame de esta respuesta
        self._audio_dicho = False   # ya se ha impreso el primer TTSAudioRawFrame de esta respuesta
        self._trozos = 0

    async def on_push_frame(self, data: FramePushed):
        frame = data.frame
        tipo = type(frame)
        # Algunos frames de sistema viajan también hacia atrás (↑) como copia, y el último procesador los
        # entrega al final de la tubería: solo se imprime el viaje hacia delante, una vez por frame.
        if (tipo not in QUE_ES or frame.id in self._vistos or data.direction != FrameDirection.DOWNSTREAM
                or _nombre(data.destination).endswith("::Sink")):
            return
        self._vistos.add(frame.id)

        extra = ""
        if tipo is LLMFullResponseStartFrame:
            self._texto_dicho, self._trozos = False, 0
        elif tipo is LLMTextFrame:
            self._trozos += 1
            if self._texto_dicho:
                return
            self._texto_dicho = True
            extra = f"«{frame.text.strip()[:60]}»"
        elif tipo is LLMFullResponseEndFrame:
            extra = f"({self._trozos} trozos de texto)"
        elif tipo is TTSStartedFrame:
            self._audio_dicho = False
        elif tipo is TTSAudioRawFrame:
            if self._audio_dicho:
                return
            self._audio_dicho = True
        elif tipo in (TranscriptionFrame, InterimTranscriptionFrame, TTSSpeakFrame):
            extra = f"«{frame.text.strip()[:60]}»"

        ahora = data.timestamp
        self._inicio = self._inicio if self._inicio is not None else ahora
        desde_anterior = (ahora - self._anterior) / 1e6 if self._anterior is not None else 0.0
        self._anterior = ahora
        self.imprimir(
            f"[traza] {(ahora - self._inicio) / 1e9:7.3f} s (+{desde_anterior:5.0f} ms)  "
            f"{_nombre(data.source)} → {_nombre(data.destination)}  "
            f"{tipo.__name__}: {QUE_ES[tipo]} {extra}".rstrip()
        )


# Nombres en español de los tramos que mide Pipecat (LatencyContribution.key).
TRAMOS = {
    "endpointing_wait": "silencio que espera el detector de voz",
    "transcription": "transcripción (STT)",
    "turn_detection": "decidir que el turno ha terminado",
    "first_request": "primera petición",
    "llm_inference": "pensar la respuesta (LLM o grafo)",
    "awaiting_speakable_text": "esperar texto que se pueda decir",
    "sentence_aggregation": "juntar una frase entera para el TTS",
    "speech_synthesis": "síntesis de voz (TTS)",
    "output_transport": "mandar el audio",
    "turn_completion": "comprobar que el turno está completo",
    "waiting_for_user": "esperar a que el cliente termine",
    "llm_tool_call": "llamada a una herramienta",
    "function_handler": "ejecutar la herramienta",
    "pipeline": "resto de la tubería",
}


def lineas_de_tiempos(desglose: LatencyBreakdown) -> list[str]:
    """Una línea por tramo, en el orden en que pasaron, y el total."""
    lineas = [
        f"[tiempos] {c.duration_secs * 1000:6.0f} ms  {TRAMOS.get(c.key, c.label):40} {c.owner}"
        for c in desglose.contributions
    ]
    desde = "desde que el cliente conectó" if desglose.measured_from == "client_connected" else \
        "desde que el cliente dejó de hablar"
    lineas.append(f"[tiempos] {desglose.total_secs * 1000:6.0f} ms  TOTAL, {desde}, hasta que suena el agente")
    return lineas


def tiempos_por_tramo(imprimir=_imprimir) -> UserBotLatencyObserver:
    """El observador de latencia de Pipecat, que imprime el desglose de cada respuesta.

    Necesita PipelineParams(enable_metrics=True): los servicios solo miden su tiempo si las métricas están activas.
    """
    observador = UserBotLatencyObserver()

    @observador.event_handler("on_latency_breakdown")
    async def al_medir(_observador, desglose: LatencyBreakdown):
        for linea in lineas_de_tiempos(desglose):
            imprimir(linea)

    return observador


def observadores(traza: bool = False, tiempos: bool = False) -> list[BaseObserver]:
    """Los observadores que se piden por la línea de comandos."""
    lista: list[BaseObserver] = []
    if traza:
        lista.append(TrazaDeVoz())
    if tiempos:
        lista.append(tiempos_por_tramo())
    return lista
