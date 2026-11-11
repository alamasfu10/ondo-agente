"""Flujo «Cita en el taller».

Pasos: motivo → ciudad → huecos → elección → confirmación → reserva.
Cada paso pide un solo dato y guarda en el estado qué está esperando.

Los pasos 1 a 3 están hechos. Los pasos 4 y 5 son la práctica del día 1.
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
                "intencion": "persona",
                "borrador": borrador("No quedan huecos libres que ofrecer en las próximas dos semanas."),
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
    # 4. Elección del hueco.
    # TODO (práctica del día 1, parte 2):
    #   - Usa eleccion(estado, huecos) para saber qué hueco ha elegido el cliente.
    #   - Si no lo sabes: suma un intento fallido, vuelve a mostrar los huecos como opciones y,
    #     si supera MAX_REINTENTOS, devuelve {"intencion": "persona"} para pasarle con una persona.
    #   - Si lo sabes: guarda "hueco_elegido", pon pendiente = "confirmar_cita" y pide confirmación
    #     con las opciones ["Sí, resérvala", "No, ver otras fechas"].

    # 5. Confirmación y reserva.
    # TODO (práctica del día 1, parte 2):
    #   - Si confirma (estado["ultima"]["confirma"] es True), llama a la herramienta reservar_cita
    #     con h.llamar("reservar_cita", cliente_id=..., hueco_id=..., motivo=...).
    #   - Si la reserva sale bien, cierra el flujo con fin_de_flujo() y confirma la cita con sus datos.
    #   - Si no confirma, ofrece otros huecos.

    return {
        "borrador": borrador(
            "Dile que la reserva de citas todavía está en construcción y que de momento no puedes reservar."
        ),
    }
