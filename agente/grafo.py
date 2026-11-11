"""El grafo del agente de Ondo.

    interpretar ─┬─ seguridad / persona ─────────────────────► escalar ──┐
                 ├─ no entendido ──► reparar ──(3.º intento)──► escalar ──┤
                 ├─ información / saludo ──► informar / saludar ──────────┤
                 └─ pedido / devolución / cita                            │
                        └─► identificar ──► flujo_* ──(persona)──► escalar┤
                                                                          ▼
                                                                      redactar ──► FIN

Los nodos deciden QUÉ hay que decir (dejan un "borrador"); el nodo redactar
decide CÓMO decirlo (tono, idioma, formato del canal).
"""

import re

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from . import llm
from .estado import Estado
from .flujos.cita import flujo_cita
from .flujos.comun import MENU, borrador, fin_de_flujo
from .flujos.devolucion import flujo_devolucion
from .flujos.pedido import flujo_pedido

MAX_INTENTOS = 3  # al tercer mensaje seguido sin entender al cliente, pasa a una persona
FLUJOS = {"pedido": "flujo_pedido", "devolucion": "flujo_devolucion", "cita": "flujo_cita"}

# Red de seguridad que no depende del modelo: estas palabras siempre son un caso de seguridad.
PELIGRO = re.compile(
    r"quemad|humo|fuego|se calienta|muy caliente|hinchad|chispa|los frenos no|no frena|sin frenos|"
    r"burning|smoke|brûl|fumée|bruciat|fumo|queimad|fumo",
    re.IGNORECASE,
)


def construir_grafo(h, checkpointer=None):
    async def interpretar(e: Estado) -> dict:
        texto = e["messages"][-1].content
        it = await llm.interpretar(e)
        if PELIGRO.search(texto):
            it.intencion = "seguridad"
        datos = dict(e.get("datos") or {})
        for campo in ("email", "pedido_id", "ciudad", "motivo"):
            valor = getattr(it, campo)
            if valor and not (campo == "motivo" and e.get("pendiente") not in (None, "motivo")):
                datos[campo] = valor.upper() if campo == "pedido_id" else valor
        cambios = {"ultima": it.model_dump(), "idioma": it.idioma or e.get("idioma", "es"), "datos": datos}
        nueva = it.intencion
        if nueva in ("pedido", "devolucion", "cita", "informacion") and nueva != e.get("intencion"):
            # Cambio de tema: empezamos el flujo nuevo con los datos de este mensaje.
            cambios.update(fin_de_flujo())
            cambios["datos"] = {k: v for k, v in datos.items() if getattr(it, k, None)}
            cambios["intencion"] = nueva
        elif nueva not in ("continuar", "no_entendido"):
            cambios["intencion"] = nueva
        if nueva != "no_entendido":
            cambios["intentos_fallidos"] = 0 if nueva != "continuar" else e.get("intentos_fallidos", 0)
        return cambios

    def ruta(e: Estado) -> str:
        it = e["ultima"]["intencion"]
        intencion = e.get("intencion")
        if intencion == "seguridad" or it == "seguridad":
            return "escalar"
        if e.get("escalado"):
            return "ya_escalado"
        if intencion == "persona":
            return "escalar"
        if it == "no_entendido":
            return "reparar"
        if intencion in FLUJOS:
            return "flujo" if e.get("cliente") else "identificar"
        if intencion == "informacion":
            return "informar"
        return "saludar"

    async def reparar(e: Estado) -> dict:
        intentos = e.get("intentos_fallidos", 0) + 1
        if intentos >= MAX_INTENTOS:
            return {"intentos_fallidos": intentos, "intencion": "persona"}
        if intentos == 1:
            b = borrador("Dile que no le has entendido bien y pídele que te lo cuente de otra forma. "
                         "Recuérdale brevemente en qué puedes ayudarle.", opciones=MENU)
        else:
            b = borrador("Dile que sigues sin entenderle y pídele que elija una de las opciones. "
                         "Si ninguna encaja, que pulse la de hablar con una persona.", opciones=MENU)
        return {"intentos_fallidos": intentos, "borrador": b}

    async def identificar(e: Estado) -> dict:
        datos = e.get("datos") or {}
        email, pedido_id = datos.get("email"), datos.get("pedido_id")
        if not email:
            pide = "su email de compra" + (" para comprobar que el pedido es suyo" if pedido_id else "")
            return {"pendiente": "email", "borrador": borrador(
                f"Para ayudarle necesitas identificarle: pídele {pide}.")}
        r = await h.llamar("buscar_cliente", email=email)
        if not r.get("encontrado"):
            intentos = e.get("intentos_fallidos", 0) + 1
            if intentos >= MAX_INTENTOS:
                return {"intentos_fallidos": intentos, "intencion": "persona"}
            return {"intentos_fallidos": intentos, "datos": {**datos, "email": None}, "pendiente": "email",
                    "borrador": borrador("Dile que no encuentras ninguna compra con ese email y pídele que lo "
                                         "revise o que te dé el email con el que hizo la compra.")}
        cliente = {**r["cliente"], "pedidos": r["pedidos"]}
        return {"cliente": cliente, "pendiente": None, "intentos_fallidos": 0}

    async def flujo(e: Estado) -> dict:
        nodo = {"pedido": flujo_pedido, "devolucion": flujo_devolucion, "cita": flujo_cita}[e["intencion"]]
        return await nodo(e, h)

    async def informar(e: Estado) -> dict:
        r = await h.llamar("buscar_conocimiento", pregunta=e["messages"][-1].content)
        cambios = {"intencion": None, "pendiente": None}
        if not r.get("resultados"):
            return {**cambios, "borrador": borrador(
                "Dile que no tienes información fiable sobre eso y ofrécele pasarle con una persona.",
                opciones=["Hablar con una persona", "Otra consulta"])}
        return {**cambios, "borrador": borrador(
            "Responde a su pregunta usando solo la información de estos fragmentos, en 2 o 3 frases. "
            "Si no responden del todo a la pregunta, dilo.", {"fragmentos": r["resultados"]})}

    async def saludar(e: Estado) -> dict:
        nombre = (e.get("cliente") or {}).get("nombre")
        return {"intencion": None, "pendiente": None, "borrador": borrador(
            "Saluda o responde al agradecimiento, recuerda que eres el asistente virtual de Ondo (una IA) y "
            "pregunta en qué puedes ayudarle.", {"nombre_cliente": nombre}, MENU[:3])}

    async def escalar(e: Estado) -> dict:
        seguridad = e.get("intencion") == "seguridad" or e["ultima"]["intencion"] == "seguridad"
        if seguridad:
            motivo = "seguridad"
        elif (e.get("datos") or {}).get("motivo_escalado"):
            motivo = e["datos"]["motivo_escalado"]
        elif e["ultima"]["intencion"] == "persona":
            motivo = "el cliente pide hablar con una persona"
        else:
            motivo = "el asistente no consigue resolver la consulta"
        resumen = await llm.resumir(e, motivo)
        cliente = e.get("cliente") or {}
        r = await h.llamar("escalar_a_humano", motivo=motivo, resumen=resumen,
                           prioridad="urgente" if seguridad else "normal", cliente_id=cliente.get("id"))
        if seguridad:
            b = borrador(
                "Es un caso de seguridad. Pídele que deje de usar la bicicleta y no cargue la batería, que "
                "desconecte el cargador y deje la batería en un lugar exterior lejos de materiales inflamables si "
                "puede hacerlo sin riesgo, y que si hay humo o fuego se aleje y llame al 112. Dile que una persona "
                "de Ondo le llamará por teléfono con prioridad y dale el número de caso.",
                {"caso": r["caso"]["id"], "espera": r["espera"]})
        else:
            b = borrador("Dile que pasas su consulta a una persona del equipo, que no tendrá que repetir nada, "
                         "cuándo le atenderán y su número de caso.",
                         {"caso": r["caso"]["id"], "espera": r["espera"]})
        return {"escalado": r["caso"], "intencion": None, "pendiente": None, "borrador": b}

    async def ya_escalado(e: Estado) -> dict:
        return {"borrador": borrador(
            "Recuérdale que su consulta ya está en manos de una persona del equipo y su número de caso. "
            "Si quiere añadir algo, que lo escriba y se lo harás llegar.", {"caso": e["escalado"]})}

    async def redactar(e: Estado) -> dict:
        b = e.get("borrador") or borrador("Pregunta en qué puedes ayudarle.")
        res = await llm.redactar(e, b)
        opciones = res.opciones if len(res.opciones) == len(b.get("opciones") or []) else b.get("opciones") or []
        return {"messages": [AIMessage(res.texto)], "opciones": opciones, "borrador": {}}

    def tras_nodo(e: Estado) -> str:
        return "escalar" if e.get("intencion") == "persona" and not e.get("escalado") else "redactar"

    def tras_identificar(e: Estado) -> str:
        if e.get("intencion") == "persona":
            return "escalar"
        return "flujo" if e.get("cliente") else "redactar"

    g = StateGraph(Estado)
    for nombre, fn in [("interpretar", interpretar), ("reparar", reparar), ("identificar", identificar),
                       ("flujo", flujo), ("informar", informar), ("saludar", saludar), ("escalar", escalar),
                       ("ya_escalado", ya_escalado), ("redactar", redactar)]:
        g.add_node(nombre, fn)
    g.add_edge(START, "interpretar")
    g.add_conditional_edges("interpretar", ruta,
                            ["escalar", "ya_escalado", "reparar", "flujo", "identificar", "informar", "saludar"])
    g.add_conditional_edges("reparar", tras_nodo, ["escalar", "redactar"])
    g.add_conditional_edges("identificar", tras_identificar, ["flujo", "redactar", "escalar"])
    g.add_conditional_edges("flujo", tras_nodo, ["escalar", "redactar"])
    for n in ("informar", "saludar", "escalar", "ya_escalado"):
        g.add_edge(n, "redactar")
    g.add_edge("redactar", END)
    return g.compile(checkpointer=checkpointer)
