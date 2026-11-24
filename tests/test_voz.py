"""Pruebas del canal de voz que no necesitan audio, red ni clave de OpenAI."""

from langchain_core.messages import HumanMessage
from pipecat.processors.aggregators.llm_context import LLMContext

from agente import llm
from canales import persona
from datetime import date

from canales.voz import crear_tts, falta_para_la_voz, ultimo_mensaje_del_cliente, voz_retirada


def _contexto(*mensajes):
    c = LLMContext()
    for rol, texto in mensajes:
        c.add_message({"role": rol, "content": texto})
    return c


def test_turno_partido_se_junta_en_un_mensaje():
    c = _contexto(("user", "Hola"), ("assistant", "Hola, ¿en qué te ayudo?"),
                  ("user", "Quiero cita en Madrid."), ("user", "Mi email es lucia.martin@example.com"))
    assert ultimo_mensaje_del_cliente(c) == "Quiero cita en Madrid. Mi email es lucia.martin@example.com"


def test_sin_mensajes_del_cliente_no_hay_turno():
    assert ultimo_mensaje_del_cliente(_contexto(("assistant", "Hola"))) == ""


def test_la_transferencia_llama_a_la_persona_sin_llamada_saliente():
    twiml = persona.twiml_transferencia()
    assert f"<Client>{persona.IDENTIDAD}</Client>" in twiml
    assert "<Number>" not in twiml


async def test_el_canal_elige_el_prompt(monkeypatch):
    sistemas = []

    class ModeloFalso:
        def with_structured_output(self, _):
            return self

        async def ainvoke(self, mensajes):
            sistemas.append(mensajes[0].content)
            return llm.Respuesta(texto="ok", opciones=[])

    monkeypatch.setattr(llm, "modelo", lambda *a, **k: ModeloFalso())
    estado = {"messages": [HumanMessage("Hola")], "idioma": "es"}
    await llm.redactar({**estado, "canal": "chat"}, {"instruccion": "Saluda"})
    await llm.redactar({**estado, "canal": "voz"}, {"instruccion": "Saluda"})
    assert "Es un chat" in sistemas[0]
    assert "el cliente te oye" in sistemas[1]


def test_la_voz_de_elevenlabs_cambia_solo_el_tts(monkeypatch):
    from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
    from pipecat.services.openai.tts import OpenAITTSService

    monkeypatch.setenv("ELEVENLABS_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voz-de-prueba")
    assert isinstance(crear_tts("elevenlabs"), ElevenLabsTTSService)
    assert isinstance(crear_tts("openai"), OpenAITTSService)


def test_sin_clave_de_elevenlabs_dice_que_falta(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voz-de-prueba")
    assert falta_para_la_voz("elevenlabs") == ["ELEVENLABS_API_KEY"]


def test_avisa_cuando_openai_retira_su_voz():
    assert not voz_retirada("openai", date(2026, 11, 30))
    assert voz_retirada("openai", date(2027, 1, 6))
    assert not voz_retirada("elevenlabs", date(2027, 3, 1))


async def test_un_turno_que_no_acaba_se_corta_y_dice_la_frase():
    import asyncio

    from pipecat.frames.frames import TTSSpeakFrame

    from canales.voz import FRASE_TURNO_LARGO, CorteDeTurno, LimiteDeTurno

    limite = LimiteDeTurno(segundos=0.05)
    corte = CorteDeTurno(limite)
    empujados, cortes = [], []

    async def al_empujar(_, frame, direction):
        empujados.append(frame)

    async def al_cortar(_, *args, **kwargs):
        cortes.append(True)

    corte.add_event_handler("on_push_frame", al_empujar)
    corte.add_event_handler("on_user_turn_stopped", al_cortar)
    await corte.handle_user_turn_started()
    await asyncio.sleep(0.2)
    assert cortes and limite.silenciar and limite.cortes == 1
    assert isinstance(empujados[0], TTSSpeakFrame) and empujados[0].text == FRASE_TURNO_LARGO


async def test_un_turno_que_acaba_a_tiempo_no_se_corta():
    import asyncio

    from canales.voz import CorteDeTurno, LimiteDeTurno

    limite = LimiteDeTurno(segundos=0.1)
    corte = CorteDeTurno(limite)
    await corte.handle_user_turn_started()
    await asyncio.sleep(0.02)
    await corte.handle_user_turn_stopped()
    await asyncio.sleep(0.2)
    assert limite.cortes == 0 and not limite.silenciar


async def test_el_silencio_dura_hasta_que_el_agente_termina_la_frase():
    from pipecat.frames.frames import BotStartedSpeakingFrame, BotStoppedSpeakingFrame, InputAudioRawFrame

    from canales.voz import LimiteDeTurno, SilencioTrasCorte

    limite = LimiteDeTurno()
    silencio = SilencioTrasCorte(limite)
    audio = InputAudioRawFrame(audio=b"\x00" * 320, sample_rate=8000, num_channels=1)
    assert not await silencio.process_frame(audio)
    limite.silenciar = True
    assert await silencio.process_frame(audio)
    assert await silencio.process_frame(BotStartedSpeakingFrame())
    assert not await silencio.process_frame(BotStoppedSpeakingFrame())
    assert not limite.silenciar and not await silencio.process_frame(audio)


def test_mas_de_setenta_palabras_es_demasiado():
    from canales.voz import MAX_PALABRAS_TURNO, demasiado_largo

    assert not demasiado_largo("quiero cita en Madrid " * 5)
    assert demasiado_largo("bla " * (MAX_PALABRAS_TURNO + 1))
