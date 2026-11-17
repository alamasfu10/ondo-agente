"""La suite de evaluación: conversaciones simuladas contra el agente, comprobaciones y juez.

    python -m evaluacion.suite                       # los diez escenarios
    python -m evaluacion.suite --solo cita_en_ingles # uno o varios, separados por comas
    python -m evaluacion.suite --sin-juez            # solo las comprobaciones con datos

Cada ejecución usa su propia carpeta de estado (no toca data/estado/) y deja el informe
y las conversaciones en evaluacion/salidas/<fecha y hora>/. Cuesta unos céntimos.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SALIDAS = RAIZ / "evaluacion" / "salidas"


def cargar_escenarios(solo: str | None) -> list[dict]:
    escenarios = json.loads((RAIZ / "evaluacion" / "escenarios.json").read_text(encoding="utf-8"))
    if solo:
        ids = [x.strip() for x in solo.split(",")]
        desconocidos = set(ids) - {e["id"] for e in escenarios}
        if desconocidos:
            sys.exit(f"No hay escenarios con id: {', '.join(sorted(desconocidos))}")
        escenarios = [e for e in escenarios if e["id"] in ids]
    return escenarios


def email_de(escenario: dict) -> str:
    """El email del cliente del escenario, sin el punto con el que acaba la frase."""
    return re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", escenario["cliente"]).group(0)


async def jugar(agente, escenario: dict, max_turnos: int) -> dict:
    from evaluacion.simulador import FIN, siguiente_mensaje

    conversacion, estado = [], {}
    for _ in range(max_turnos):
        texto = await siguiente_mensaje(escenario, conversacion)
        if FIN in texto or not texto:
            break
        conversacion.append(("cliente", texto, []))
        r = await agente.responder(escenario["id"], texto)
        estado = r.estado
        conversacion.append(("agente", r.texto, r.opciones))
        if estado.get("escalado") and len([c for c in conversacion if c[0] == "agente"]) > 1:
            # Tras pasar a una persona, el cliente ya no tiene nada que hacer con el agente.
            break
    return {"conversacion": conversacion, "estado": estado,
            "turnos": len([c for c in conversacion if c[0] == "cliente"])}


async def evaluar(escenarios: list[dict], max_turnos: int, con_juez: bool, paralelo: int) -> list[dict]:
    from agente.agente import AgenteOndo
    from evaluacion.comprobaciones import cliente_id, resultado
    from evaluacion.juez import valorar

    limite = asyncio.Semaphore(paralelo)
    async with AgenteOndo() as agente:
        async def uno(e):
            async with limite:
                partida = await jugar(agente, e, max_turnos)
                comprob = resultado(e["esperado"], partida["estado"], cliente_id(email_de(e)))
                juez = (await valorar(partida["conversacion"])).model_dump() if con_juez else {}
                print(f"   terminado: {e['id']} ({partida['turnos']} turnos)", flush=True)
                return {"id": e["id"], **partida, "comprobaciones": comprob, "juez": juez}
        return await asyncio.gather(*(uno(e) for e in escenarios))


def informe(resultados: list[dict]) -> str:
    lineas = ["# Informe de evaluación", "", f"Fecha: {datetime.now():%Y-%m-%d %H:%M}", "",
              "| Escenario | Comprobaciones | Juez | Turnos |", "|---|---|---|---|"]
    superados = escalado_ok = escalado_n = 0
    juez_ok = juez_n = 0
    for r in resultados:
        fallos = [k for k, (ok, _) in r["comprobaciones"].items() if not ok]
        if not fallos:
            superados += 1
        escalado_n += 1
        escalado_ok += r["comprobaciones"]["escalado"][0]
        malos = [k for k, v in r["juez"].items() if v["veredicto"] == "no cumple"]
        aplican = [k for k, v in r["juez"].items() if v["veredicto"] != "no aplica"]
        juez_n += len(aplican)
        juez_ok += len(aplican) - len(malos)
        comp = "✔" if not fallos else "✘ " + ", ".join(fallos)
        jz = "" if not r["juez"] else ("✔" if not malos else "✘ " + ", ".join(malos))
        lineas.append(f"| {r['id']} | {comp} | {jz} | {r['turnos']} |")
    n = len(resultados)
    lineas += ["", "## Métricas", "",
               f"- Escenarios superados (todas las comprobaciones): {superados} de {n}",
               f"- Paso a persona correcto (cuando tocaba, y solo entonces): {escalado_ok} de {escalado_n}",
               f"- Turnos del cliente, de media: {sum(r['turnos'] for r in resultados) / max(n, 1):.1f}"]
    if juez_n:
        lineas.append(f"- Criterios del juez cumplidos: {juez_ok} de {juez_n} ({100 * juez_ok / juez_n:.0f} %)")
    lineas += ["", "## Detalle", ""]
    for r in resultados:
        lineas += [f"### {r['id']}", ""]
        for k, (ok, detalle) in r["comprobaciones"].items():
            lineas.append(f"- {'✔' if ok else '✘'} {k}: {detalle}")
        for k, v in r["juez"].items():
            if v["veredicto"] != "no aplica":
                lineas.append(f"- {'✔' if v['veredicto'] == 'cumple' else '✘'} juez · {k}: {v['motivo']}")
        lineas.append("")
    return "\n".join(lineas)


def main() -> None:
    p = argparse.ArgumentParser(description="Evalúa el agente de Ondo con conversaciones simuladas.")
    p.add_argument("--solo", help="ids de escenario separados por comas")
    p.add_argument("--max-turnos", type=int, default=10)
    p.add_argument("--sin-juez", action="store_true")
    p.add_argument("--paralelo", type=int, default=4)
    a = p.parse_args()

    carpeta = SALIDAS / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    os.environ["ONDO_ESTADO"] = str(carpeta / "estado")  # el servidor MCP escribe aquí, no en data/estado/
    escenarios = cargar_escenarios(a.solo)
    print(f"Evaluando {len(escenarios)} escenario(s)...", flush=True)
    resultados = asyncio.run(evaluar(escenarios, a.max_turnos, not a.sin_juez, a.paralelo))

    carpeta.mkdir(parents=True, exist_ok=True)
    texto = informe(resultados)
    (carpeta / "informe.md").write_text(texto, encoding="utf-8")
    (carpeta / "conversaciones.json").write_text(json.dumps(
        [{"id": r["id"], "conversacion": r["conversacion"]} for r in resultados], ensure_ascii=False, indent=2),
        encoding="utf-8")
    print()
    print(texto.split("## Detalle")[0].strip())
    print(f"\nInforme completo y conversaciones en {carpeta.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
