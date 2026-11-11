"""Flujo «Devolver un producto».

Todavía no está implementado: de momento, toda devolución pasa a una persona.
Es el ejercicio complementario 1 del día 1.
"""


async def flujo_devolucion(estado: dict, h) -> dict:
    # TODO (complementario 1): pedir el pedido, consultar la política con buscar_conocimiento,
    # comprobar plazo e importe y crear la devolución o pasar a una persona.
    return {"intencion": "persona", "datos": {**(estado.get("datos") or {}), "motivo_escalado": "devolución"}}
