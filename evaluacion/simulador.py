"""El cliente simulado: un modelo que hace de cliente de Ondo siguiendo un escenario."""

from langchain_core.messages import HumanMessage, SystemMessage

from agente.llm import modelo

FIN = "[FIN]"

PROMPT_CLIENTE = """Eres un cliente de Ondo, una tienda online de bicicletas eléctricas, que escribe al chat de \
atención al cliente. No eres un asistente: eres la persona que pide ayuda.

Quién eres: {cliente}
Qué quieres conseguir: {objetivo}
Cómo escribes: {estilo}
Idioma en el que escribes siempre: {idioma}

Reglas:
- Escribe solo tu siguiente mensaje, corto, como en un chat. Sin comillas ni explicaciones.
- Da tus datos (email, número de pedido) solo cuando te los pidan.
- Si el asistente te ofrece botones y tu estilo lo permite, puedes escribir exactamente el texto de uno.
- Cuando hayas conseguido tu objetivo, o te digan que una persona se encargará, escribe solo {fin}.
- Si llevas varios mensajes sin avanzar, sigue tu estilo; no abandones antes de tiempo."""


async def siguiente_mensaje(escenario: dict, conversacion: list[tuple[str, str, list[str]]]) -> str:
    """Devuelve el siguiente mensaje del cliente, o FIN si ya ha terminado.

    conversacion es una lista de (quien, texto, botones), con quien = "cliente" o "agente".
    """
    sistema = PROMPT_CLIENTE.format(fin=FIN, **{k: escenario[k] for k in ("cliente", "objetivo", "estilo", "idioma")})
    if conversacion:
        lineas = []
        for quien, texto, botones in conversacion:
            nombre = "Tú" if quien == "cliente" else "Asistente"
            lineas.append(f"{nombre}: {texto}")
            if botones:
                lineas.append("   Botones: " + " | ".join(botones))
        tarea = "Conversación hasta ahora:\n" + "\n".join(lineas) + "\n\nEscribe tu siguiente mensaje."
    else:
        tarea = "Escribe tu primer mensaje al chat."
    res = await modelo(0.7).ainvoke([SystemMessage(sistema), HumanMessage(tarea)])
    return res.content.strip()
