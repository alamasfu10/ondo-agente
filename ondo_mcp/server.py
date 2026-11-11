"""Servidor MCP de Ondo: las herramientas que usa el agente.

Se da hecho. Lo arranca el agente como subproceso (transporte stdio), igual
que los servidores MCP que construisteis en el Tema 6. Para probarlo solo:

    uv run python -m ondo_mcp.server        # se queda esperando por stdio
    uv run mcp dev ondo_mcp/server.py       # inspector web de MCP (opcional)
"""

from datetime import date, datetime, time, timedelta

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from . import conocimiento, datos

load_dotenv(datos.RAIZ / ".env")

mcp = FastMCP("ondo", log_level="WARNING")

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _cliente_publico(c: dict) -> dict:
    return {k: c[k] for k in ("id", "nombre", "email", "ciudad", "pais", "idioma")}


@mcp.tool()
def buscar_cliente(email: str | None = None, pedido_id: str | None = None, telefono: str | None = None) -> dict:
    """Identifica a un cliente por su email, por un número de pedido (OND-12345) o por su teléfono.

    Devuelve el cliente y la lista resumida de sus pedidos, o encontrado=false.
    """
    cs = datos.clientes()
    c = None
    if email:
        c = next((x for x in cs if _norm(x["email"]) == _norm(email)), None)
    if c is None and pedido_id:
        p = next((x for x in datos.pedidos() if _norm(x["id"]) == _norm(pedido_id)), None)
        if p:
            c = next(x for x in cs if x["id"] == p["cliente_id"])
    if c is None and telefono:
        dig = "".join(ch for ch in telefono if ch.isdigit())[-9:]
        c = next((x for x in cs if "".join(ch for ch in x["telefono"] if ch.isdigit())[-9:] == dig), None)
    if c is None:
        return {"encontrado": False}
    ps = [
        {"id": p["id"], "estado": p["estado"], "fecha_pedido": p["fecha_pedido"],
         "productos": ", ".join(l["nombre"] for l in p["lineas"])}
        for p in datos.pedidos() if p["cliente_id"] == c["id"]
    ]
    return {"encontrado": True, "cliente": _cliente_publico(c), "pedidos": ps}


@mcp.tool()
def estado_pedido(pedido_id: str) -> dict:
    """Devuelve el estado de un pedido: productos, total, estado, fechas, transportista e incidencias.

    Incluye cliente_id: comprueba que coincide con el cliente identificado antes de dar datos.
    """
    p = next((x for x in datos.pedidos() if _norm(x["id"]) == _norm(pedido_id)), None)
    if p is None:
        return {"error": f"No existe ningún pedido {pedido_id}"}
    devs = [d for d in datos.leer_estado("devoluciones") if d["pedido_id"] == p["id"]]
    if devs:
        p = {**p, "devolucion": devs[-1]}
    return p


@mcp.tool()
def crear_devolucion(pedido_id: str, cliente_id: str, motivo: str) -> dict:
    """Registra la solicitud de devolución de un pedido entregado y programa la recogida.

    No comprueba la política (plazo, importe): eso lo decide el agente antes de llamarla.
    """
    p = next((x for x in datos.pedidos() if _norm(x["id"]) == _norm(pedido_id)), None)
    if p is None:
        return {"ok": False, "error": f"No existe ningún pedido {pedido_id}"}
    if p["cliente_id"] != cliente_id:
        return {"ok": False, "error": "El pedido no pertenece a ese cliente"}
    if p["estado"] != "entregado":
        return {"ok": False, "error": f"Solo se pueden devolver pedidos entregados (estado: {p['estado']})"}
    devs = datos.leer_estado("devoluciones")
    if any(d["pedido_id"] == p["id"] for d in devs):
        return {"ok": False, "error": "Ese pedido ya tiene una devolución registrada"}
    recogida = datos.hoy() + timedelta(days=2)
    while recogida.weekday() >= 5:
        recogida += timedelta(days=1)
    dev = {
        "id": f"DEV-{len(devs) + 1:04d}",
        "pedido_id": p["id"],
        "cliente_id": cliente_id,
        "motivo": motivo,
        "importe": p["total"],
        "recogida": recogida.isoformat(),
        "creada": datos.ahora(),
    }
    datos.guardar_estado("devoluciones", devs + [dev])
    return {"ok": True, "devolucion": dev}


def _huecos(taller: dict, dias: int) -> list[dict]:
    reservados = {c["hueco_id"] for c in datos.leer_estado("citas")}
    salida = []
    inicio = datos.hoy() + timedelta(days=1)
    for n in range(dias):
        d = inicio + timedelta(days=n)
        for h in taller["horario"].get(str(d.weekday()), []):
            hid = f"{taller['id']}-{d.isoformat()}-{h:02d}"
            if hid in reservados:
                continue
            salida.append({
                "hueco_id": hid,
                "fecha": d.isoformat(),
                "dia": DIAS[d.weekday()],
                "hora": f"{h:02d}:00",
            })
    return salida


@mcp.tool()
def huecos_taller(ciudad: str, dias: int = 14) -> dict:
    """Busca el taller asociado de una ciudad y sus huecos libres para los próximos días (citas de 60 minutos)."""
    t = next((x for x in datos.talleres() if _norm(x["ciudad"]) == _norm(ciudad)), None)
    if t is None:
        return {"encontrado": False, "ciudades_con_taller": [x["ciudad"] for x in datos.talleres()]}
    hs = _huecos(t, dias)
    return {
        "encontrado": True,
        "taller": {k: t[k] for k in ("id", "nombre", "ciudad", "direccion")},
        "huecos": hs[:6],
        "total_huecos": len(hs),
    }


@mcp.tool()
def reservar_cita(cliente_id: str, hueco_id: str, motivo: str) -> dict:
    """Reserva un hueco concreto (hueco_id devuelto por huecos_taller) para un cliente."""
    if not any(c["id"] == cliente_id for c in datos.clientes()):
        return {"ok": False, "error": f"No existe el cliente {cliente_id}"}
    t = next((x for x in datos.talleres() if hueco_id.startswith(x["id"] + "-")), None)
    if t is None:
        return {"ok": False, "error": f"Hueco {hueco_id} no válido"}
    libre = next((h for h in _huecos(t, 60) if h["hueco_id"] == hueco_id), None)
    if libre is None:
        return {"ok": False, "error": "Ese hueco ya no está libre. Vuelve a consultar huecos_taller."}
    citas = datos.leer_estado("citas")
    cita = {
        "id": f"CIT-{len(citas) + 1:04d}",
        "cliente_id": cliente_id,
        "hueco_id": hueco_id,
        "taller": t["nombre"],
        "direccion": t["direccion"],
        "fecha": libre["fecha"],
        "hora": libre["hora"],
        "motivo": motivo,
        "creada": datos.ahora(),
    }
    datos.guardar_estado("citas", citas + [cita])
    return {"ok": True, "cita": cita}


def _en_horario(ahora: datetime) -> bool:
    return ahora.weekday() < 5 and time(9) <= ahora.time() < time(19)


@mcp.tool()
def escalar_a_humano(motivo: str, resumen: str, prioridad: str = "normal",
                     cliente_id: str | None = None, canal: str = "chat") -> dict:
    """Pasa el caso a una persona del equipo de atención al cliente.

    prioridad: "normal" o "urgente" (seguridad). El resumen lo lee la persona: motivo, datos ya
    recogidos y lo que se ha intentado, para que el cliente no tenga que repetir nada.
    """
    casos = datos.leer_estado("escalados")
    ahora = datetime.now()
    caso = {
        "id": f"CASO-{len(casos) + 1:04d}",
        "cliente_id": cliente_id,
        "motivo": motivo,
        "resumen": resumen,
        "prioridad": "urgente" if prioridad == "urgente" else "normal",
        "canal": canal,
        "creado": datos.ahora(),
    }
    datos.guardar_estado("escalados", casos + [caso])
    if caso["prioridad"] == "urgente":
        espera = "Una persona del equipo de postventa contactará contigo por teléfono con prioridad."
    elif _en_horario(ahora):
        espera = "Una persona del equipo te atenderá en los próximos minutos."
    else:
        espera = "Una persona del equipo contactará contigo el siguiente día laborable, a partir de las 9:00."
    return {"ok": True, "caso": caso, "espera": espera, "en_horario": _en_horario(ahora)}


@mcp.tool()
def buscar_conocimiento(pregunta: str) -> dict:
    """Busca en la base de conocimiento de Ondo (devoluciones, garantía, envíos, seguridad, talleres,
    cuidado de la batería, pagos, privacidad y atención al cliente).

    Devuelve hasta 3 fragmentos con su documento y sección. Si no hay nada relevante, devuelve
    una lista vacía: en ese caso no hay que inventar la respuesta.
    """
    res = conocimiento.buscar(pregunta)
    if not res:
        return {"resultados": [], "mensaje": "sin resultados"}
    return {"resultados": res}


if __name__ == "__main__":
    mcp.run()
