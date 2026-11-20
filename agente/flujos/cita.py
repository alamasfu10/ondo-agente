"""Flujo «Cita en el taller» (resuelto: es la práctica del día 2).

Pasos: motivo → ciudad → huecos → elección → confirmación → reserva.
Cada paso pide un solo dato y guarda en el estado qué está esperando.
"""

from .comun import borrador, eleccion, fin_de_flujo

MOTIVOS = ["Revisión", "Avería"]
MAX_REINTENTOS = 2


def _etiqueta(hueco: dict) -> str:
    d = hueco["fecha"][8:10] + "/" + hueco["fecha"][5:7]
    return f"{hueco['dia'].capitalize()} {d} a las {hueco['hora']}"


async def flujo_cita(estado: dict, h) -> dict:
    cliente = estado["cliente"]
    datos = dict(estado.get("datos") or {})
    pendiente = estado.get("pendiente")
    ultima = estado.get("ultima") or {}

    # 1. Motivo de la cita.
    if not datos.get("motivo"):
        i = eleccion(estado, MOTIVOS) if pendiente == "motivo" else None
        if i is None and pendiente == "motivo" and ultima.get("motivo"):
            i = 1 if "aver" in ultima["motivo"].lower() else 0
        if i is None:
            return {
                "datos": datos,
                "pendiente": "motivo",
                "borrador": borrador("Pregunta si la cita es para una revisión o por una avería.", opciones=MOTIVOS),
            }
        datos["motivo"] = MOTIVOS[i].lower()

    # 2. Ciudad: proponemos la del cliente.
    if not datos.get("ciudad"):
        ops = [cliente["ciudad"], "Otra ciudad"]
        i = eleccion(estado, ops) if pendiente == "ciudad" else None
        if i == 0:
            datos["ciudad"] = cliente["ciudad"]
        else:
            return {
                "datos": datos,
                "pendiente": "ciudad",
                "borrador": borrador(
                    "Pregunta en qué ciudad quiere la cita. Propón su ciudad o que escriba otra.",
                    {"ciudad_del_cliente": cliente["ciudad"]},
                    ops,
                ),
            }

    # 3. Huecos libres del taller de esa ciudad.
    huecos = estado.get("huecos") or []
    if not huecos or pendiente not in ("hueco", "confirmar_cita"):
        r = await h.llamar("huecos_taller", ciudad=datos["ciudad"])
        if not r.get("encontrado"):
            return {
                "datos": {**datos, "ciudad": None},
                "pendiente": "ciudad",
                "borrador": borrador(
                    "Dile que no hay taller asociado en esa ciudad, enumera las ciudades donde sí hay y pregúntale si "
                    "prefiere otra o que una persona organice la recogida de la bicicleta.",
                    {"ciudad": datos["ciudad"], "ciudades_con_taller": r.get("ciudades_con_taller")},
                    ["Hablar con una persona"],
                ),
            }
        pagina = datos.get("pagina", 0)
        huecos = r["huecos"][pagina * 3:(pagina + 1) * 3]
        if not huecos:
            return {
                "datos": {**datos, "pagina": 0},
                "pendiente": None,
                "huecos": [],
                "borrador": borrador(
                    "Dile que no tienes más huecos libres que ofrecerle en las próximas dos semanas y pregúntale si "
                    "quiere que una persona del equipo le busque una fecha.",
                    opciones=["Hablar con una persona", "Volver a ver los primeros huecos"],
                ),
            }
        return {
            "datos": {**datos, "taller": r["taller"]},
            "huecos": huecos,
            "pendiente": "hueco",
            "intentos_fallidos": 0,
            "borrador": borrador(
                "Dile qué taller le corresponde (nombre y dirección) y pídele que elija uno de los huecos.",
                {"taller": r["taller"]},
                [_etiqueta(x) for x in huecos],
            ),
        }

    # 4. Elección del hueco, con reparación si no lo entendemos.
    texto = estado["messages"][-1].content.strip().lower()
    if texto.startswith("volver a ver los primeros"):
        nuevo = {**datos, "pagina": 0}
        return {"datos": nuevo, **(await flujo_cita({**estado, "datos": nuevo, "huecos": [], "pendiente": None}, h))}
    if pendiente == "hueco" and texto.startswith("ninguna"):
        return {"datos": {**datos, "pagina": datos.get("pagina", 0) + 1}, "huecos": [], "pendiente": None,
                **(await flujo_cita({**estado, "datos": {**datos, "pagina": datos.get("pagina", 0) + 1},
                                     "huecos": [], "pendiente": None}, h))}

    if pendiente == "hueco":
        i = eleccion(estado, huecos)
        if i is None:
            intentos = estado.get("intentos_fallidos", 0) + 1
            if intentos > MAX_REINTENTOS:
                return {"intentos_fallidos": intentos, "intencion": "persona",
                        "borrador": borrador("No consigue elegir hueco.")}
            return {
                "intentos_fallidos": intentos,
                "borrador": borrador(
                    "Dile con amabilidad que no has identificado qué hueco prefiere y pídele que pulse una de las "
                    "opciones. Si ninguna le va bien, que lo diga y le buscas otras fechas.",
                    opciones=[_etiqueta(x) for x in huecos] + ["Ninguna me va bien"],
                ),
            }
        elegido = huecos[i]
        return {
            "hueco_elegido": elegido,
            "pendiente": "confirmar_cita",
            "intentos_fallidos": 0,
            "borrador": borrador(
                "Resume la cita (taller, dirección, día, hora, motivo) y pide confirmación antes de reservar.",
                {"taller": datos.get("taller"), "hueco": elegido, "motivo": datos["motivo"]},
                ["Sí, resérvala", "No, ver otras fechas"],
            ),
        }

    # 5. Confirmación y reserva.
    if pendiente == "confirmar_cita":
        confirma = ultima.get("confirma")
        if texto.startswith("sí, resérvala") or texto.startswith("si, reservala"):
            confirma = True
        if confirma is True:
            r = await h.llamar("reservar_cita", cliente_id=cliente["id"],
                               hueco_id=estado["hueco_elegido"]["hueco_id"], motivo=datos["motivo"])
            if not r.get("ok"):
                return {
                    "huecos": [],
                    "pendiente": None,
                    "borrador": borrador("Dile que ese hueco se acaba de ocupar y que le muestras otros.", r),
                }
            return {
                **fin_de_flujo(),
                "borrador": borrador(
                    "Confirma la cita reservada con todos sus datos y el código de la cita, y recuerda que puede "
                    "cambiarla o cancelarla sin coste hasta 24 horas antes.",
                    r["cita"],
                ),
            }
        if confirma is False or texto.startswith("no, ver otras"):
            nuevo = {**datos, "pagina": datos.get("pagina", 0) + 1}
            return {"huecos": [], "hueco_elegido": None, "pendiente": None, "datos": nuevo,
                    **(await flujo_cita({**estado, "datos": nuevo, "huecos": [], "pendiente": None}, h))}
        return {
            "borrador": borrador(
                "Pregúntale de nuevo, de forma directa, si confirma la reserva.",
                {"hueco": estado["hueco_elegido"]},
                ["Sí, resérvala", "No, ver otras fechas"],
            ),
        }

    return {"pendiente": None, "huecos": [], "borrador": borrador("Pregunta en qué más puede ayudarle.")}
