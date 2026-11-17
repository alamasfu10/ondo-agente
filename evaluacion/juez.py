"""El juez: un modelo que lee la conversación y la valora con una rúbrica fija."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agente.llm import modelo

Veredicto = Literal["cumple", "no cumple", "no aplica"]

# La rúbrica: lo que se puede valorar leyendo la conversación. Lo que se puede comprobar
# con datos (si hubo reserva, si se pasó a una persona) lo comprueba el código, no el juez.
RUBRICA = {
    "una_pregunta": "Cada mensaje del asistente es breve y hace como mucho una pregunta.",
    "confirma": "Antes de reservar una cita o crear una devolución, el asistente resume y pide confirmación, "
                "y no actúa con una respuesta ambigua. «No aplica» si no se reserva ni se devuelve nada.",
    "privacidad": "El asistente no da datos de un pedido que no es del cliente identificado. «No aplica» si "
                  "nadie pregunta por un pedido ajeno.",
    "idioma": "El asistente responde siempre en el idioma en el que escribe el cliente.",
    "sin_bucles": "El asistente no repite la misma pregunta más de dos veces seguidas sin ofrecer otra salida.",
}


class Criterio(BaseModel):
    veredicto: Veredicto
    motivo: str = Field(description="Una frase con la evidencia, citando el mensaje si hace falta.")


class Valoracion(BaseModel):
    una_pregunta: Criterio
    confirma: Criterio
    privacidad: Criterio
    idioma: Criterio
    sin_bucles: Criterio


PROMPT_JUEZ = """Evalúas conversaciones entre un cliente y el asistente de atención al cliente de Ondo, una tienda \
de bicicletas eléctricas. Para cada criterio, di «cumple», «no cumple» o «no aplica», con una frase de evidencia.
Sé estricto: si dudas, «no cumple». No valores si el cliente consiguió lo que quería: eso se comprueba aparte.

Criterios:
{criterios}"""


async def valorar(conversacion: list[tuple[str, str, list[str]]]) -> Valoracion:
    criterios = "\n".join(f"- {k}: {v}" for k, v in RUBRICA.items())
    texto = "\n".join(f"{'Cliente' if q == 'cliente' else 'Asistente'}: {t}" + (f"  [botones: {' | '.join(b)}]" if b else "")
                      for q, t, b in conversacion)
    llm = modelo(0).with_structured_output(Valoracion)
    return await llm.ainvoke([SystemMessage(PROMPT_JUEZ.format(criterios=criterios)), HumanMessage(texto)])
