"""El estado de la conversación: lo que el agente sabe en cada turno.

Esta es la diferencia con un agente ReAct genérico. El estado no es solo la
lista de mensajes: guarda de forma explícita quién es el cliente, qué quiere,
qué datos tenemos ya, qué dato estamos esperando y cuántas veces no le hemos
entendido. El checkpointer de LangGraph lo conserva entre turnos.
"""

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

Intencion = Literal[
    "pedido", "devolucion", "cita", "informacion", "seguridad", "persona", "saludo", "continuar", "no_entendido"
]


class Interpretacion(BaseModel):
    """Lo que el modelo entiende del último mensaje del cliente."""

    intencion: Intencion = Field(description=(
        "pedido: dónde está o cómo va un pedido. devolucion: quiere devolver algo. cita: cita en un taller "
        "(revisión o avería). informacion: duda general sobre Ondo (garantía, envíos, pagos, cuidados). "
        "seguridad: batería que se calienta, huele a quemado, humo, hinchada, frenos que no frenan. "
        "persona: pide hablar con una persona. saludo: solo saluda o da las gracias. continuar: responde a lo "
        "que el asistente acaba de preguntar. no_entendido: no se entiende qué necesita."
    ))
    idioma: str = Field(description="Código ISO 639-1 del idioma del mensaje: es, en, fr, it, pt...")
    email: str | None = Field(default=None, description="Email del cliente si aparece.")
    pedido_id: str | None = Field(default=None, description="Número de pedido en formato OND-12345 si aparece.")
    ciudad: str | None = Field(default=None, description="Ciudad si el cliente la menciona.")
    motivo: str | None = Field(default=None, description=(
        "Para citas: 'revisión' o 'avería' (con detalle si lo da). Para devoluciones: el motivo que da."
    ))
    eleccion: int | None = Field(default=None, description=(
        "Si el cliente elige una de las opciones que se le ofrecieron, su número (empezando en 1)."
    ))
    confirma: bool | None = Field(default=None, description=(
        "True si acepta o confirma lo que se le propuso, False si lo rechaza, null si no aplica."
    ))


class Estado(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    idioma: str
    intencion: str | None
    cliente: dict | None          # cliente identificado (id, nombre, email, ciudad...)
    datos: dict                   # datos recogidos: email, pedido_id, ciudad, motivo
    pendiente: str | None         # qué estamos esperando que conteste el cliente
    opciones: list[str]           # opciones que se le muestran (botones en Telegram)
    huecos: list[dict]            # huecos de taller ofrecidos
    hueco_elegido: dict | None
    intentos_fallidos: int        # turnos seguidos sin entender al cliente
    escalado: dict | None         # caso abierto con una persona
    ultima: dict                  # Interpretacion del último mensaje
    borrador: dict                # qué hay que decir (lo redacta el nodo redactar)
