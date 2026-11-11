"""Comprueba que tu entorno está listo para el Tema 10.

    uv run python scripts/comprobar_entorno.py

Revisa: versión de Python, dependencias, fichero .env, clave de OpenAI
(con una llamada mínima que cuesta una fracción de céntimo), servidor MCP de
Ondo y ngrok. No imprime nunca tus claves.
"""

import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
OK, KO, AVISO = "  ✔", "  ✘", "  !"
fallos = 0


def mal(msg):
    global fallos
    fallos += 1
    print(f"{KO} {msg}")


def comprobar_python():
    v = sys.version_info
    if v >= (3, 11):
        print(f"{OK} Python {v.major}.{v.minor}")
    else:
        mal(f"Python {v.major}.{v.minor}: necesitas 3.11 o superior (uv lo instala solo con «uv sync»)")


def comprobar_dependencias():
    try:
        import fastapi, langchain_openai, langgraph, mcp, telegram  # noqa: F401
        print(f"{OK} Dependencias instaladas")
    except ImportError as e:
        mal(f"Falta una dependencia ({e.name}). Ejecuta «uv sync» en la carpeta del proyecto")


def comprobar_env():
    from dotenv import load_dotenv
    if not (RAIZ / ".env").exists():
        mal("No existe el fichero .env. Cópialo de .env.example y rellena tu clave")
        return False
    load_dotenv(RAIZ / ".env")
    clave = os.getenv("OPENAI_API_KEY", "")
    if not clave.startswith("sk-"):
        mal("OPENAI_API_KEY no está en el .env o no empieza por «sk-»")
        return False
    print(f"{OK} Fichero .env con OPENAI_API_KEY")
    return True


def comprobar_openai():
    try:
        from langchain_openai import ChatOpenAI
        from agente.llm import MODELO
        r = ChatOpenAI(model=MODELO, max_tokens=5).invoke("Responde solo: ok")
        print(f"{OK} OpenAI responde con el modelo {MODELO} ({r.content.strip()!r})")
    except Exception as e:  # noqa: BLE001
        mal(f"La llamada a OpenAI falla: {type(e).__name__}: {str(e)[:160]}")


async def _mcp():
    from agente.herramientas import conectar_ondo
    async with conectar_ondo() as h:
        r = await h.llamar("buscar_cliente", email="lucia.martin@example.com")
        assert r.get("encontrado"), r
        return len(h.tools)


def comprobar_mcp():
    try:
        n = asyncio.run(_mcp())
        print(f"{OK} Servidor MCP de Ondo con {n} herramientas")
    except Exception as e:  # noqa: BLE001
        mal(f"El servidor MCP de Ondo no arranca: {type(e).__name__}: {str(e)[:160]}")


def comprobar_ngrok():
    if not shutil.which("ngrok"):
        mal("ngrok no está instalado (lo necesitas a partir del día 2: guía de preparación, paso 6)")
        return
    r = subprocess.run(["ngrok", "config", "check"], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"{OK} ngrok instalado y configurado")
    else:
        print(f"{AVISO} ngrok instalado pero sin configurar: «ngrok config add-authtoken TU_TOKEN»")


if __name__ == "__main__":
    print("Comprobando el entorno del Tema 10...\n")
    comprobar_python()
    comprobar_dependencias()
    if comprobar_env():
        comprobar_openai()
    comprobar_mcp()
    comprobar_ngrok()
    print()
    print("Todo listo." if not fallos else f"Hay {fallos} cosa(s) por arreglar: revisa la guía de preparación.")
    sys.exit(1 if fallos else 0)
