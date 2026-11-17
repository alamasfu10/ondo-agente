"""Lo que se comprueba con datos, sin modelo: si se pasó a una persona, si hubo reserva o devolución, el idioma."""

from ondo_mcp import datos


def cliente_id(email: str) -> str | None:
    for c in datos.clientes():
        if c["email"].lower() == email.lower():
            return c["id"]
    return None


def resultado(esperado: dict, estado_final: dict, cid: str | None) -> dict:
    """Compara lo esperado con lo que pasó. Devuelve {comprobación: (ok, detalle)}."""
    escalado = estado_final.get("escalado")
    citas = [c for c in datos.leer_estado("citas") if c.get("cliente_id") == cid]
    devoluciones = [d for d in datos.leer_estado("devoluciones") if d.get("cliente_id") == cid]
    salida = {
        "escalado": (bool(escalado) == esperado["escalado"],
                     f"{'sí' if escalado else 'no'} (esperado: {'sí' if esperado['escalado'] else 'no'})"),
        "cita": (bool(citas) == esperado["cita"],
                 f"{len(citas)} reservada(s) (esperado: {'sí' if esperado['cita'] else 'ninguna'})"),
        "devolucion": (bool(devoluciones) == esperado["devolucion"],
                       f"{len(devoluciones)} creada(s) (esperado: {'sí' if esperado['devolucion'] else 'ninguna'})"),
    }
    if esperado.get("prioridad") and escalado:
        p = escalado.get("prioridad")
        salida["prioridad"] = (p == esperado["prioridad"], f"{p} (esperado: {esperado['prioridad']})")
    if esperado.get("idioma"):
        i = estado_final.get("idioma")
        salida["idioma"] = (i == esperado["idioma"], f"{i} (esperado: {esperado['idioma']})")
    return salida
