"""Pruebas del servidor MCP de Ondo (no necesitan clave de OpenAI).

    uv run pytest
"""

import pytest

from ondo_mcp import datos, server


@pytest.fixture(autouse=True)
def estado_limpio(tmp_path, monkeypatch):
    monkeypatch.setattr(datos, "ESTADO", tmp_path)


def test_buscar_cliente_por_email_y_por_pedido():
    a = server.buscar_cliente(email="LUCIA.MARTIN@example.com")
    b = server.buscar_cliente(pedido_id="ond-10231")
    assert a["encontrado"] and a["cliente"]["id"] == "C001"
    assert b["cliente"]["id"] == "C001"
    assert not server.buscar_cliente(email="nadie@example.com")["encontrado"]


def test_estado_pedido_incluye_cliente():
    p = server.estado_pedido("OND-10235")
    assert p["cliente_id"] == "C004" and p["total"] > 1500


def test_reservar_no_pisa_huecos():
    h = server.huecos_taller("Madrid")["huecos"][0]["hueco_id"]
    assert server.reservar_cita("C001", h, "revisión")["ok"]
    assert not server.reservar_cita("C002", h, "revisión")["ok"]
    assert h not in [x["hueco_id"] for x in server.huecos_taller("Madrid")["huecos"]]


def test_ciudad_sin_taller():
    r = server.huecos_taller("Bilbao")
    assert not r["encontrado"] and "Madrid" in r["ciudades_con_taller"]


def test_devolucion_solo_del_titular_y_entregado():
    assert not server.crear_devolucion("OND-10233", "C001", "x")["ok"]
    assert not server.crear_devolucion("OND-10231", "C001", "x")["ok"]  # enviado, no entregado
    assert server.crear_devolucion("OND-10233", "C002", "no me convence")["ok"]
    assert not server.crear_devolucion("OND-10233", "C002", "otra vez")["ok"]


def test_escalar_urgente():
    r = server.escalar_a_humano("seguridad", "batería huele a quemado", prioridad="urgente", cliente_id="C007")
    assert r["caso"]["prioridad"] == "urgente" and "prioridad" in r["espera"]
