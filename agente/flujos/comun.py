"""Piezas comunes a todos los flujos."""


def borrador(instruccion: str, datos: dict | None = None, opciones: list[str] | None = None) -> dict:
    """Qué tiene que decir el agente. El nodo redactar lo convierte en el mensaje final."""
    return {"instruccion": instruccion, "datos": datos or {}, "opciones": opciones or []}


MENU = ["Dónde está mi pedido", "Devolver un producto", "Cita en el taller", "Hablar con una persona"]


def fin_de_flujo() -> dict:
    """Cierra el flujo actual sin olvidar quién es el cliente."""
    return {"intencion": None, "pendiente": None, "huecos": [], "hueco_elegido": None,
            "datos": {}, "intentos_fallidos": 0}


def eleccion(estado: dict, lista: list) -> int | None:
    """Índice (base 0) de la opción que eligió el cliente, o None.

    Primero mira si el texto coincide con un botón; si no, usa lo que entendió el modelo.
    """
    texto = (estado["messages"][-1].content or "").strip().lower()
    for i, op in enumerate(estado.get("opciones") or []):
        if texto == op.strip().lower() and i < len(lista):
            return i
    n = (estado.get("ultima") or {}).get("eleccion")
    if n and 1 <= n <= len(lista):
        return n - 1
    return None
