"""Habla con el agente de Ondo desde la terminal.

    python -m canales.consola
    python -m canales.consola --estado     # muestra el estado tras cada turno
    python -m canales.consola --traza      # muestra además el recorrido por el grafo en cada turno

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


def _corto(valor, n: int = 90) -> str:
    texto = valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False, default=str)
    return texto if len(texto) <= n else texto[: n - 1] + "…"


class Traza:
    """Imprime el recorrido de un turno: cada nodo del grafo, lo que cambia y las herramientas que llama."""

    def __init__(self):
        self.paso = 0
        self.llamadas: list[tuple] = []

    def herramienta(self, nombre: str, args: dict, resultado: dict) -> None:
        # Se llama mientras el nodo trabaja; se imprime debajo de su línea cuando el nodo termina.
        self.llamadas.append((nombre, args, resultado))

    def nodo(self, nombre: str, cambios: dict) -> None:
        self.paso += 1
        partes = []
        if cambios.get("ultima"):
            partes.append(f"entiende: {cambios['ultima']['intencion']}")
        for campo in ("intencion", "pendiente", "intentos_fallidos", "idioma"):
            if campo in cambios:
                partes.append(f"{campo}={cambios[campo]}")
        if "datos" in cambios:
            partes.append(f"datos={_corto(cambios['datos'], 60)}")
        if cambios.get("cliente"):
            partes.append(f"cliente={cambios['cliente']['id']}")
        if cambios.get("escalado"):
            partes.append(f"caso={cambios['escalado'].get('id')}")
        if cambios.get("borrador"):
            partes.append(f"borrador: «{_corto(cambios['borrador']['instruccion'], 70)}»")
        if nombre == "redactar":
            partes.append("escribe la respuesta")
        print(f"   {self.paso}. {nombre:<12} " + "; ".join(partes))
        for herramienta, args, resultado in self.llamadas:
            print(f"        herramienta {herramienta}({_corto(args, 60)}) -> {_corto(resultado)}")
        self.llamadas = []


async def main(ver_estado: bool, ver_traza: bool) -> None:
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
            traza = Traza() if ver_traza else None
            if traza:
                agente.herramientas.trazar = traza.herramienta
            r = await agente.responder("consola", texto, traza=traza and traza.nodo)
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
    p.add_argument("--traza", action="store_true",
                   help="muestra el recorrido por el grafo en cada turno (incluye el estado al final)")
    a = p.parse_args()
    asyncio.run(main(a.estado or a.traza, a.traza))
