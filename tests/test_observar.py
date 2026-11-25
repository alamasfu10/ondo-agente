"""Pruebas de los observadores de voz (--traza y --tiempos) y de los ajustes del turno. Sin audio ni red."""

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TranscriptionFrame,
)
from pipecat.observers.base_observer import FramePushed
from pipecat.observers.user_bot_latency_observer import LatencyBreakdown, LatencyContribution
from pipecat.processors.frame_processor import FrameDirection

from canales.observar import TrazaDeVoz, lineas_de_tiempos


class Pieza:
    def __init__(self, name):
        self.name = name


async def _empujar(traza, frame, origen="A", destino="B", direccion=FrameDirection.DOWNSTREAM, ms=0):
    await traza.on_push_frame(FramePushed(source=Pieza(origen), destination=Pieza(destino), frame=frame,
                                          direction=direccion, timestamp=ms * 1_000_000))


async def test_la_traza_cuenta_la_respuesta_sin_repetir_trozos():
    lineas = []
    traza = TrazaDeVoz(imprimir=lineas.append)
    transcripcion = TranscriptionFrame("quiero una cita", user_id="", timestamp="")
    await _empujar(traza, transcripcion, "OpenAISTTService#0", "LLMUserAggregator#0", ms=0)
    await _empujar(traza, transcripcion, "LLMUserAggregator#0", "OpenAILLMService#0", ms=1)  # mismo frame: no
    await _empujar(traza, LLMFullResponseStartFrame(), ms=10)
    for i, trozo in enumerate(["Claro", ", dime", " la ciudad."]):
        await _empujar(traza, LLMTextFrame(trozo), ms=600 + i)
    await _empujar(traza, LLMFullResponseEndFrame(), ms=700)
    await _empujar(traza, BotStartedSpeakingFrame(), direccion=FrameDirection.UPSTREAM, ms=900)  # copia: no
    assert len(lineas) == 4
    assert "«quiero una cita»" in lineas[0] and "OpenAISTTService#0 → LLMUserAggregator#0" in lineas[0]
    assert "«Claro»" in lineas[2] and "(+  590 ms)" in lineas[2]
    assert "(3 trozos de texto)" in lineas[3]


def test_los_tiempos_salen_en_espanol_y_con_total():
    desglose = LatencyBreakdown(
        contributions=[
            LatencyContribution(key="transcription", label="transcription", owner="OpenAISTTService#0",
                                owner_kind="service", start_time=0, duration_secs=0.6),
            LatencyContribution(key="speech_synthesis", label="speech synthesis", owner="OpenAITTSService#0",
                                owner_kind="service", start_time=0.6, duration_secs=0.8),
        ],
        measured_from="user_silence",
        total_secs=1.4,
    )
    lineas = lineas_de_tiempos(desglose)
    assert "transcripción (STT)" in lineas[0] and "600 ms" in lineas[0]
    assert "síntesis de voz (TTS)" in lineas[1]
    assert "1400 ms  TOTAL, desde que el cliente dejó de hablar" in lineas[2]


def test_el_fin_de_turno_puede_ser_por_significado_o_por_silencio():
    from pipecat.turns.user_stop.speech_timeout_user_turn_stop_strategy import SpeechTimeoutUserTurnStopStrategy
    from pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy import TurnAnalyzerUserTurnStopStrategy

    from canales.voz import estrategias_de_fin_de_turno

    assert isinstance(estrategias_de_fin_de_turno("silencio")[0], SpeechTimeoutUserTurnStopStrategy)
    assert isinstance(estrategias_de_fin_de_turno("significado")[0], TurnAnalyzerUserTurnStopStrategy)


def test_la_practica_y_su_solucion_se_importan():
    from practica import cascada_minima
    from practica.solucion import cascada_minima as solucion

    assert callable(cascada_minima.bot) and callable(solucion.bot)
