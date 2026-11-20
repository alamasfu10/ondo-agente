"""Pruebas del canal de voz que no necesitan audio, red ni clave de OpenAI."""

from langchain_core.messages import HumanMessage
from pipecat.processors.aggregators.llm_context import LLMContext

from agente import llm
from canales import persona
from canales.voz import ultimo_mensaje_del_cliente


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
