"""Flujo «Devolver un producto» (resuelto: es la práctica del día 2).

Pasos: pedido → comprobaciones (estado, plazo, importe) → motivo → confirmación → devolución.
Las reglas salen de la política de Ondo (data/conocimiento/devoluciones.md), que el agente
consulta con buscar_conocimiento para explicarlas al cliente con sus propias palabras.
"""

from datetime import date

from .comun import borrador, eleccion, fin_de_flujo

PLAZO_DIAS = 30           # devoluciones.md, «Plazo para devolver»
LIMITE_IMPORTE = 1500     # devoluciones.md, «Devoluciones que revisa una persona»
CONFIRMAR = ["Sí, solicita la devolución", "No, déjalo"]


async def _politica(h) -> list:
    r = await h.llamar("buscar_conocimiento", pregunta="plazo para devolver y devoluciones que revisa una persona")
    return r.get("resultados", [])


def _a_persona(datos: dict, motivo: str) -> dict:
    return {"intencion": "persona", "datos": {**datos, "motivo_escalado": motivo}}


async def flujo_devolucion(estado: dict, h) -> dict:
    cliente = estado["cliente"]
    datos = dict(estado.get("datos") or {})
    pendiente = estado.get("pendiente")
    ultima = estado.get("ultima") or {}
    texto = estado["messages"][-1].content.strip()

    # 1. Qué pedido quiere devolver (solo tienen sentido los entregados).
    entregados = [p for p in cliente.get("pedidos", []) if p["estado"] == "entregado"]
    if not datos.get("pedido_id") and pendiente == "pedido_id":
        i = eleccion(estado, entregados)
        if i is not None:
            datos["pedido_id"] = entregados[i]["id"]
    if not datos.get("pedido_id"):
        if len(entregados) == 1:
            datos["pedido_id"] = entregados[0]["id"]
        elif not entregados:
            return {**fin_de_flujo(), "borrador": borrador(
                "Dile que no tiene ningún pedido entregado que se pueda devolver y explícale que, si un pedido "
                "todavía no le ha llegado, puede rechazarlo en la entrega.")}
        else:
            return {"datos": datos, "pendiente": "pedido_id", "borrador": borrador(
                "Pregúntale qué pedido quiere devolver.", {"pedidos": entregados},
                [f"{p['id']} · {p['productos']}"[:60] for p in entregados][:4])}

    # 2. Comprobaciones: titular, estado, plazo e importe.
    pedido = await h.llamar("estado_pedido", pedido_id=datos["pedido_id"])
    if "error" in pedido or pedido.get("cliente_id") != cliente["id"]:
        return {"datos": {**datos, "pedido_id": None}, "pendiente": "pedido_id", "borrador": borrador(
            "Dile que ese pedido no está asociado a su cuenta, sin dar datos del pedido, y pídele que lo revise.")}
    if pedido.get("devolucion"):
        return {**fin_de_flujo(), "borrador": borrador(
            "Dile que ese pedido ya tiene una devolución en curso y dale sus datos.", pedido["devolucion"])}
    if pedido["estado"] != "entregado":
        return {**fin_de_flujo(), "borrador": borrador(
            "Explica que el pedido todavía no se ha entregado, así que aún no se puede devolver, y que puede "
            "rechazarlo en la entrega si lo prefiere.", {"pedido": pedido})}

    dias = (date.today() - date.fromisoformat(pedido["fecha_entrega"])).days
    politica = await _politica(h)
    if dias > PLAZO_DIAS:
        return {**_a_persona(datos, f"devolución fuera de plazo: han pasado {dias} días desde la entrega y el plazo es de {PLAZO_DIAS}"),
                "borrador": borrador("")}
    if pedido["total"] > LIMITE_IMPORTE:
        return {**_a_persona(datos, f"devolución de {pedido['total']} € (más de {LIMITE_IMPORTE} €)"),
                "borrador": borrador("")}

    # 3. Motivo de la devolución.
    if not datos.get("motivo_devolucion"):
        if pendiente == "motivo_devolucion":
            datos["motivo_devolucion"] = ultima.get("motivo") or texto
        else:
            return {"datos": datos, "pendiente": "motivo_devolucion", "borrador": borrador(
                "Dile que el pedido está dentro de plazo para devolverlo (di cuántos días le quedan) y pregúntale "
                "el motivo de la devolución. Es solo para mejorar, no tiene que justificarse.",
                {"pedido": pedido["id"], "dias_restantes": PLAZO_DIAS - dias, "politica": politica})}

    # 4. Confirmación.
    if pendiente != "confirmar_devolucion":
        return {"datos": datos, "pendiente": "confirmar_devolucion", "borrador": borrador(
            "Resume la devolución (pedido, productos, importe que se reembolsa) y cómo funciona: recogida sin coste "
            "en su dirección, caja original o equivalente, reembolso en un máximo de 14 días desde que el almacén lo "
            "revisa. Pide confirmación.", {"pedido": pedido, "politica": politica}, CONFIRMAR)}

    confirma = ultima.get("confirma")
    if texto.lower().startswith("sí, solicita"):
        confirma = True
    if confirma is not True:
        return {**fin_de_flujo(), "borrador": borrador("Dile que no tramitas la devolución y pregunta si necesita algo más.")}

    # 5. Devolución.
    r = await h.llamar("crear_devolucion", pedido_id=pedido["id"], cliente_id=cliente["id"],
                       motivo=datos["motivo_devolucion"])
    if not r.get("ok"):
        return _a_persona(datos, f"no se pudo crear la devolución: {r.get('error')}")
    return {**fin_de_flujo(), "borrador": borrador(
        "Confirma la devolución: código, fecha de recogida y plazo de reembolso. Pregunta si necesita algo más.",
        r["devolucion"])}
