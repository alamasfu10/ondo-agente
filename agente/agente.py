"""El agente de Ondo listo para usar desde cualquier canal.

    async with AgenteOndo() as agente:
        r = await agente.responder("telegram-1234", "¿Dónde está mi pedido?")
        print(r.texto, r.opciones)

Cada conversación es un thread_id: el checkpointer guarda su estado y lo
recupera en el siguiente mensaje. Telegram usa el id del chat; la consola,
un id fijo; el día 2, cada llamada tendrá el suyo.
"""

import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from .grafo import construir_grafo
from .herramientas import conectar_ondo


@dataclass
class RespuestaAgente:
    texto: str
    opciones: list[str] = field(default_factory=list)
    estado: dict = field(default_factory=dict)


class AgenteOndo:
    def __init__(self):
        self._pila = AsyncExitStack()
        self.grafo = None
        self.herramientas = None
        self._sesiones: dict[str, str] = {}

    async def __aenter__(self):
        self.herramientas = await self._pila.enter_async_context(conectar_ondo())
        self.grafo = construir_grafo(self.herramientas, checkpointer=InMemorySaver())
        return self

    async def __aexit__(self, *exc):
        await self._pila.aclose()

    def _thread(self, conversacion: str) -> str:
        return self._sesiones.setdefault(conversacion, f"{conversacion}-{uuid.uuid4().hex[:6]}")

    def reiniciar(self, conversacion: str) -> None:
        """Empieza una conversación nueva (el estado anterior se queda en el checkpointer)."""
        self._sesiones.pop(conversacion, None)

    async def responder(self, conversacion: str, texto: str) -> RespuestaAgente:
        config = {"configurable": {"thread_id": self._thread(conversacion)}}
        estado = await self.grafo.ainvoke({"messages": [HumanMessage(texto)]}, config)
        return RespuestaAgente(estado["messages"][-1].content, estado.get("opciones") or [], estado)
