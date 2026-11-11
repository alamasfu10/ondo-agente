"""Las dos llamadas al modelo que hace el agente en cada turno.

- interpretar(): entiende el mensaje del cliente (salida estructurada).
- redactar(): escribe la respuesta con el tono de Ondo, en el idioma del
  cliente y con el formato del canal.

Entre una y otra, el grafo decide qué hacer con código normal: qué dato
falta, qué herramienta llamar, cuándo pasar a una persona.
"""

import json
import os

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .estado import Interpretacion
from .herramientas import RAIZ

load_dotenv(RAIZ / ".env")

MODELO = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def modelo(temperatura: float = 0.2) -> ChatOpenAI:
    return ChatOpenAI(model=MODELO, temperature=temperatura)


PROMPT_INTERPRETAR = """Eres el módulo que interpreta los mensajes que llegan al asistente de atención al cliente de \
Ondo, una tienda online de bicicletas eléctricas. No respondes al cliente: solo extraes lo que dice.

Contexto de la conversación:
- Lo que el asistente está esperando: {pendiente}
- Intención en curso: {intencion}
- Opciones que se acaban de mostrar al cliente (numeradas desde 1): {opciones}

Reglas:
- Si el mensaje contesta a lo que el asistente esperaba o elige una de las opciones, la intención es "continuar".
- Si el mensaje coincide con una opción mostrada o se refiere a ella ("la segunda", "el jueves"), rellena "eleccion".
- Cualquier señal de peligro (batería que se calienta, huele a quemado, humo, hinchada, frenos que fallan) es \
"seguridad", aunque el cliente lo cuente con calma o como una pregunta.
- Si el cliente pide hablar con una persona, la intención es "persona".
- Usa "no_entendido" solo si de verdad no se puede saber qué necesita."""


def _historial(messages, n=6):
    return [m for m in messages if isinstance(m, (HumanMessage, AIMessage))][-n:]


async def interpretar(estado: dict) -> Interpretacion:
    sistema = PROMPT_INTERPRETAR.format(
        pendiente=estado.get("pendiente") or "nada en concreto",
        intencion=estado.get("intencion") or "ninguna",
        opciones=json.dumps(estado.get("opciones") or [], ensure_ascii=False),
    )
    llm = modelo(0).with_structured_output(Interpretacion)
    return await llm.ainvoke([SystemMessage(sistema), *_historial(estado["messages"])])


class Respuesta(BaseModel):
    texto: str = Field(description="El mensaje para el cliente.")
    opciones: list[str] = Field(default_factory=list, description=(
        "Las opciones recibidas, traducidas al idioma del cliente si hace falta, en el mismo orden."
    ))


PERSONA_ONDO = """Eres el asistente virtual de Ondo, una tienda online de bicicletas eléctricas que vende en España, \
Francia, Italia y Portugal. Eres una inteligencia artificial y lo dices si te preguntan.

Cómo escribes:
- Respondes siempre en el idioma del cliente ({idioma}).
- Tuteas, con un tono cercano y profesional. Frases cortas. Una sola pregunta por mensaje.
- Es un chat: sin títulos, sin tablas y sin markdown. Como mucho, una lista corta con guiones.
- No inventas datos: usa solo los datos que te pasa el sistema. Si no tienes un dato, no lo supongas.
- No repitas los botones en el texto: el cliente ya los ve debajo del mensaje.
"""


async def redactar(estado: dict, borrador: dict) -> Respuesta:
    sistema = PERSONA_ONDO.format(idioma=estado.get("idioma") or "es")
    tarea = (
        "Escribe el siguiente mensaje del asistente.\n"
        f"Qué tiene que decir: {borrador['instruccion']}\n"
        f"Datos que puedes usar: {json.dumps(borrador.get('datos') or {}, ensure_ascii=False, default=str)}\n"
        f"Opciones (botones) que verá el cliente: {json.dumps(borrador.get('opciones') or [], ensure_ascii=False)}"
    )
    llm = modelo().with_structured_output(Respuesta)
    return await llm.ainvoke([SystemMessage(sistema), *_historial(estado["messages"]), HumanMessage(tarea)])


async def resumir(estado: dict, motivo: str) -> str:
    """Resumen para la persona que recibe el caso: que el cliente no tenga que repetir nada."""
    texto = "\n".join(
        f"{'Cliente' if isinstance(m, HumanMessage) else 'Asistente'}: {m.content}"
        for m in _historial(estado["messages"], 12)
    )
    sistema = (
        "Resume para una persona de atención al cliente de Ondo esta conversación con un asistente automático. "
        "En español, en 3 a 5 líneas: qué necesita el cliente, datos ya recogidos (cliente, pedido, ciudad...), "
        "qué se ha intentado y en qué estado de ánimo está el cliente."
    )
    datos = {"motivo": motivo, "cliente": estado.get("cliente"), "datos": estado.get("datos")}
    res = await modelo(0).ainvoke([SystemMessage(sistema), HumanMessage(f"{json.dumps(datos, ensure_ascii=False)}\n\n{texto}")])
    return res.content
