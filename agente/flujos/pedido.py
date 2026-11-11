"""Flujo «¿Dónde está mi pedido?»."""

from .comun import borrador, eleccion, fin_de_flujo


async def flujo_pedido(estado: dict, h) -> dict:
    cliente = estado["cliente"]
    datos = estado.get("datos") or {}
    pedido_id = datos.get("pedido_id")

    # El cliente elige entre sus pedidos con un botón.
    if not pedido_id and estado.get("pendiente") == "pedido_id":
        ids = [p["id"] for p in cliente.get("pedidos", [])]
        i = eleccion(estado, ids)
        if i is not None:
            pedido_id = ids[i]

    if not pedido_id:
        todos = cliente.get("pedidos", [])
        activos = [p for p in todos if p["estado"] in ("preparando", "enviado", "incidencia")]
        if len(activos) == 1 or len(todos) == 1:
            pedido_id = (activos or todos)[0]["id"]
        else:
            ops = [p["id"] for p in (activos or cliente.get("pedidos", []))][:4]
            return {
                "pendiente": "pedido_id",
                "borrador": borrador(
                    "Pregunta de qué pedido se trata. Puede elegir uno de sus pedidos.",
                    {"pedidos": cliente.get("pedidos", [])},
                    ops,
                ),
            }

    pedido = await h.llamar("estado_pedido", pedido_id=pedido_id)
    if "error" in pedido:
        return {
            "pendiente": "pedido_id",
            "datos": {**datos, "pedido_id": None},
            "borrador": borrador(f"Dile que no encuentras el pedido {pedido_id} y pídele que revise el número."),
        }
    # Nunca damos datos de un pedido que no es del cliente identificado.
    if pedido["cliente_id"] != cliente["id"]:
        return {
            "pendiente": "pedido_id",
            "datos": {**datos, "pedido_id": None},
            "borrador": borrador(
                "Dile que ese pedido no está asociado a su cuenta, sin dar ningún dato del pedido, y pregúntale "
                "si ha podido equivocarse de número."
            ),
        }
    return {
        **fin_de_flujo(),
        "borrador": borrador(
            "Explica el estado del pedido en 2 o 3 frases: estado, fecha de entrega (real o estimada), "
            "transportista y número de seguimiento si los hay, e incidencia si la hay con lo que debe hacer. "
            "Termina preguntando si necesita algo más.",
            {"pedido": pedido},
        ),
    }
