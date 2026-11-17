"""Pruebas de las comprobaciones de la evaluación (sin modelo)."""

import pytest

from evaluacion import comprobaciones
from evaluacion.suite import cargar_escenarios, email_de
from ondo_mcp import datos


@pytest.fixture(autouse=True)
def estado_limpio(tmp_path, monkeypatch):
    monkeypatch.delenv("ONDO_ESTADO", raising=False)
    monkeypatch.setattr(datos, "ESTADO", tmp_path)


def test_los_escenarios_estan_bien_formados():
    escenarios = cargar_escenarios(None)
    assert len(escenarios) == 10
    for e in escenarios:
        assert {"id", "cliente", "objetivo", "estilo", "idioma", "esperado"} <= set(e)
        assert comprobaciones.cliente_id(email_de(e)), e["id"]


def test_cita_reservada_y_esperada():
    datos.guardar_estado("citas", [{"id": "CIT-0001", "cliente_id": "C026"}])
    r = comprobaciones.resultado({"escalado": False, "cita": True, "devolucion": False}, {}, "C026")
    assert all(ok for ok, _ in r.values())


def test_la_cita_de_otro_cliente_no_cuenta():
    datos.guardar_estado("citas", [{"id": "CIT-0001", "cliente_id": "C001"}])
    r = comprobaciones.resultado({"escalado": False, "cita": True, "devolucion": False}, {}, "C026")
    assert r["cita"][0] is False


def test_escalado_con_prioridad_equivocada():
    esperado = {"escalado": True, "prioridad": "urgente", "cita": False, "devolucion": False}
    r = comprobaciones.resultado(esperado, {"escalado": {"id": "CASO-1", "prioridad": "normal"}}, "C007")
    assert r["escalado"][0] is True
    assert r["prioridad"][0] is False


def test_idioma():
    esperado = {"escalado": False, "cita": False, "devolucion": False, "idioma": "en"}
    assert comprobaciones.resultado(esperado, {"idioma": "es"}, None)["idioma"][0] is False
