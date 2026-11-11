"""Acceso a los datos ficticios de Ondo.

Los pedidos guardan sus fechas como "hace N días" y aquí se convierten a
fechas reales a partir de hoy, para que el kit funcione igual sea cual sea el
día en que lo pruebes. Lo que crea el agente (citas, devoluciones, casos
pasados a una persona) se guarda en data/estado/, que puedes borrar para
empezar de cero.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
ESTADO = DATA / "estado"


def _leer(nombre):
    return json.loads((DATA / f"{nombre}.json").read_text(encoding="utf-8"))


def hoy() -> date:
    return date.today()


def clientes() -> list[dict]:
    return _leer("clientes")


def catalogo() -> list[dict]:
    return _leer("catalogo")


def talleres() -> list[dict]:
    return _leer("talleres")


def _fecha(hace_dias):
    return None if hace_dias is None else (hoy() - timedelta(days=hace_dias)).isoformat()


def pedidos() -> list[dict]:
    salida = []
    for p in _leer("pedidos"):
        q = {k: v for k, v in p.items() if not k.startswith("hace_") and k != "entrega_estimada_en_dias"}
        q["fecha_pedido"] = _fecha(p["hace_dias_pedido"])
        q["fecha_entrega"] = _fecha(p["hace_dias_entrega"])
        if p.get("entrega_estimada_en_dias") is not None:
            q["entrega_estimada"] = (hoy() + timedelta(days=p["entrega_estimada_en_dias"])).isoformat()
        salida.append(q)
    return salida


def leer_estado(nombre: str) -> list[dict]:
    f = ESTADO / f"{nombre}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def guardar_estado(nombre: str, filas: list[dict]) -> None:
    ESTADO.mkdir(parents=True, exist_ok=True)
    (ESTADO / f"{nombre}.json").write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")
