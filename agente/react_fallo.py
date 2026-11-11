"""Demo del día 1: el agente ReAct genérico que falla.

Un agente ReAct con las herramientas de Ondo y un prompt genérico, sin estado
de conversación: cada mensaje llega solo, como si el canal no guardara nada.
Sirve para ver los fallos antes de construir el grafo.

    uv run python -m agente.react_fallo            # guion de la demo
    uv run python -m agente.react_fallo --libre    # escribe tú los mensajes
    uv run python -m agente.react_fallo --memoria  # con memoria: arregla una parte, no todo
"""

import argparse
import asyncio

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from .herramientas import conectar_ondo
from .llm import modelo

PROMPT_GENERICO = "Eres el asistente de atención al cliente de Ondo, una tienda de bicicletas eléctricas. Ayuda al cliente."

GUION = [
    "Hola, soy Lucía Martín, lucia.martin@example.com. ¿Dónde está mi pedido?",
    "Es el OND-10231",
    "¿Y cuándo me llega?",
    "Ya que estás, ¿cómo va el pedido OND-10235?",
    "Quiero cita en el taller de Madrid este sábado a las 18:00 para una revisión",
    "¿Cuántos días tengo para devolver una bici?",
    "Por cierto, la batería de la bici que compré huele un poco a quemado al cargarla, ¿es normal?",
]


async def main(libre: bool, memoria: bool) -> None:
    async with conectar_ondo() as h:
        # Sin buscar_conocimiento: el agente genérico no consulta la política de Ondo.
        tools = [t for t in h.tools if t.name != "buscar_conocimiento"]
        agente = create_agent(modelo(), tools, system_prompt=PROMPT_GENERICO,
                              checkpointer=InMemorySaver() if memoria else None)
        config = {"configurable": {"thread_id": "demo"}}
        mensajes = GUION if not libre else iter(lambda: input("Tú: ").strip(), "/salir")
        for texto in mensajes:
            if not libre:
                print(f"\nTú: {texto}")
            r = await agente.ainvoke({"messages": [HumanMessage(texto)]}, config)
            llamadas = [tc["name"] for m in r["messages"] for tc in (getattr(m, "tool_calls", None) or [])]
            if llamadas:
                print(f"   [herramientas: {', '.join(llamadas)}]")
            print(f"Agente: {r['messages'][-1].content}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--libre", action="store_true")
    p.add_argument("--memoria", action="store_true")
    a = p.parse_args()
    asyncio.run(main(a.libre, a.memoria))
