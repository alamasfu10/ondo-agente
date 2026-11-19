"""Flujo «Devolver un producto».

Todavía no está implementado: de momento, toda devolución pasa a una persona.
Se construye en la práctica del día 2.
"""


async def flujo_devolucion(estado: dict, h) -> dict:
    # TODO (práctica del día 2): pedir el pedido, consultar la política con buscar_conocimiento,
    # comprobar plazo e importe y crear la devolución o pasar a una persona.
    return {"intencion": "persona", "datos": {**(estado.get("datos") or {}), "motivo_escalado": "devolución"}}
