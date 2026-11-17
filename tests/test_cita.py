"""Pruebas del flujo de cita: la especificación de los pasos 4 y 5 (práctica del día 1).

    python -m pytest tests/test_cita.py

No necesitan clave de OpenAI: prueban la lógica del flujo con herramientas
simuladas, sin modelo ni servidor MCP. Al empezar la práctica fallan casi
todas; cuando el flujo esté completo, pasan todas.
"""

from langchain_core.messages import HumanMessage

from agente.flujos.cita import MAX_REINTENTOS, flujo_cita

TALLER = {"id": "T01", "nombre": "Ondo Taller Madrid Centro", "direccion": "Calle Ejemplo 1, Madrid"}
HUECOS = [
    {"hueco_id": f"H{i}", "fecha": f"2026-11-{24 + i}", "dia": "martes", "hora": "10:00"} for i in range(6)
]


class HerramientasFalsas:
    """Sustituye al servidor MCP: devuelve datos fijos y apunta cada llamada."""

    def __init__(self, reserva_ok: bool = True):
        self.llamadas: list[tuple[str, dict]] = []
        self.reserva_ok = reserva_ok

    async def llamar(self, nombre: str, **args) -> dict:
        self.llamadas.append((nombre, args))
        if nombre == "huecos_taller":
            return {"encontrado": True, "taller": TALLER, "huecos": HUECOS}
        if nombre == "reservar_cita":
            if not self.reserva_ok:
                return {"ok": False, "error": "Ese hueco ya no está libre."}
            return {"ok": True, "cita": {"id": "CIT-0001", "hueco_id": args["hueco_id"], "taller": TALLER}}
        raise AssertionError(f"El flujo de cita no debería llamar a {nombre}")

    def nombres(self) -> list[str]:
        return [n for n, _ in self.llamadas]


def estado(texto: str, pendiente: str, **extra) -> dict:
    """Estado de una conversación de Lucía (C001) que ya ha dado motivo y ciudad."""
    base = {
        "messages": [HumanMessage(texto)],
        "cliente": {"id": "C001", "nombre": "Lucía", "ciudad": "Madrid"},
        "datos": {"motivo": "revisión", "ciudad": "Madrid", "taller": TALLER},
        "huecos": HUECOS[:3],
        "opciones": ["Martes 24/11 a las 10:00", "Martes 25/11 a las 10:00", "Martes 26/11 a las 10:00"],
        "pendiente": pendiente,
        "intentos_fallidos": 0,
        "ultima": {"intencion": "continuar", "eleccion": None, "confirma": None},
    }
    base.update(extra)
    return base


# ---- Paso 4 · Elección del hueco -------------------------------------------------------------

async def test_elegir_un_hueco_pide_confirmacion_y_no_reserva():
    h = HerramientasFalsas()
    r = await flujo_cita(estado("Martes 25/11 a las 10:00", "hueco"), h)
    assert r["hueco_elegido"] == HUECOS[1]
    assert r["pendiente"] == "confirmar_cita"
    assert len(r["borrador"]["opciones"]) == 2, "Para confirmar se ofrecen dos opciones: sí o no"
    assert "reservar_cita" not in h.nombres(), "Reservar es una acción con efecto: antes hay que confirmar"


async def test_la_eleccion_que_entiende_el_modelo_tambien_vale():
    h = HerramientasFalsas()
    e = estado("el del tercer día", "hueco", ultima={"intencion": "continuar", "eleccion": 3, "confirma": None})
    r = await flujo_cita(e, h)
    assert r["hueco_elegido"] == HUECOS[2]
    assert r["pendiente"] == "confirmar_cita"


async def test_si_no_se_entiende_la_eleccion_vuelve_a_ofrecer_los_huecos():
    h = HerramientasFalsas()
    r = await flujo_cita(estado("asdf", "hueco"), h)
    assert r["intentos_fallidos"] == 1
    assert r.get("pendiente", "hueco") == "hueco"
    assert r.get("intencion") != "persona", "Al primer intento no se pasa a una persona"
    assert len(r["borrador"]["opciones"]) >= 3, "Hay que volver a mostrar los huecos como opciones"
    assert "reservar_cita" not in h.nombres()


async def test_al_superar_los_reintentos_pasa_a_una_persona():
    h = HerramientasFalsas()
    r = await flujo_cita(estado("zzz", "hueco", intentos_fallidos=MAX_REINTENTOS), h)
    assert r["intencion"] == "persona"
    assert "reservar_cita" not in h.nombres()


# ---- Paso 5 · Confirmación y reserva ----------------------------------------------------------

def estado_confirmar(texto: str, confirma):
    return estado(texto, "confirmar_cita", hueco_elegido=HUECOS[1],
                  ultima={"intencion": "continuar", "eleccion": None, "confirma": confirma})


async def test_con_un_si_claro_reserva_y_cierra_el_flujo():
    h = HerramientasFalsas()
    r = await flujo_cita(estado_confirmar("sí, adelante", True), h)
    reservas = [a for n, a in h.llamadas if n == "reservar_cita"]
    assert len(reservas) == 1
    assert reservas[0]["cliente_id"] == "C001"
    assert reservas[0]["hueco_id"] == "H1"
    assert reservas[0]["motivo"] == "revisión"
    assert r["pendiente"] is None and r["intencion"] is None, "Tras reservar, el flujo se cierra"
    assert "CIT-0001" in str(r["borrador"]), "El cliente recibe el código de la cita"


async def test_con_un_no_no_reserva_y_ofrece_otros_huecos():
    h = HerramientasFalsas()
    r = await flujo_cita(estado_confirmar("no, mejor otro día", False), h)
    assert "reservar_cita" not in h.nombres()
    assert r["pendiente"] == "hueco"
    assert len(r["borrador"]["opciones"]) >= 1


async def test_una_respuesta_ambigua_no_cuenta_como_si():
    h = HerramientasFalsas()
    r = await flujo_cita(estado_confirmar("bueno, no sé", None), h)
    assert "reservar_cita" not in h.nombres(), "El agente nunca reserva por defecto"
    assert r.get("pendiente", "confirmar_cita") == "confirmar_cita"


async def test_si_el_hueco_ya_no_esta_libre_no_da_la_cita_por_hecha():
    h = HerramientasFalsas(reserva_ok=False)
    r = await flujo_cita(estado_confirmar("sí", True), h)
    assert "reservar_cita" in h.nombres()
    assert "CIT-" not in str(r["borrador"]), "Si la reserva falla no hay código de cita"
    assert r.get("pendiente") != "confirmar_cita"
