"""Habla con el agente de Ondo desde la terminal.

    uv run python -m canales.consola
    uv run python -m canales.consola --estado     # muestra el estado tras cada turno

Escribe el número de una opción para pulsar ese botón. /reset empieza una
conversación nueva y /salir termina.
"""

import argparse
import asyncio
import json

from agente.agente import AgenteOndo

CAMPOS = ("intencion", "cliente", "datos", "pendiente", "intentos_fallidos", "escalado", "idioma")


def mostrar_estado(estado: dict) -> None:
    resumen = {k: estado.get(k) for k in CAMPOS}
    if resumen.get("cliente"):
        resumen["cliente"] = {k: resumen["cliente"][k] for k in ("id", "nombre")}
    print("   [estado] " + json.dumps(resumen, ensure_ascii=False, default=str))


async def main(ver_estado: bool) -> None:
    print("Agente de Ondo en la terminal. /reset para empezar de nuevo, /salir para terminar.\n")
    async with AgenteOndo() as agente:
        opciones: list[str] = []
        while True:
            try:
                texto = input("Tú: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not texto:
                continue
            if texto == "/salir":
                break
            if texto == "/reset":
                agente.reiniciar("consola")
                opciones = []
                print("   (conversación nueva)\n")
                continue
            if texto.isdigit() and 1 <= int(texto) <= len(opciones):
                texto = opciones[int(texto) - 1]
                print(f"   (pulsas «{texto}»)")
            r = await agente.responder("consola", texto)
            print(f"Ondo: {r.texto}")
            opciones = r.opciones
            for i, op in enumerate(opciones, start=1):
                print(f"   [{i}] {op}")
            if ver_estado:
                mostrar_estado(r.estado)
            print()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--estado", action="store_true", help="muestra el estado del grafo tras cada turno")
    asyncio.run(main(p.parse_args().estado))
