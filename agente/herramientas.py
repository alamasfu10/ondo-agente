"""Conexión con el servidor MCP de Ondo.

Se abre una sola sesión MCP y se mantiene abierta mientras el agente funciona,
para no arrancar un proceso nuevo en cada llamada a una herramienta.
"""

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

RAIZ = Path(__file__).resolve().parents[1]


def _cliente_mcp() -> MultiServerMCPClient:
    return MultiServerMCPClient({
        "ondo": {
            "command": sys.executable,
            "args": ["-m", "ondo_mcp.server"],
            "transport": "stdio",
            "cwd": str(RAIZ),
            # El subproceso no hereda el entorno completo: le pasamos lo que necesita.
            "env": {k: v for k, v in os.environ.items() if k.startswith(("OPENAI_", "RAG_", "PATH", "HOME"))},
        }
    })


class Herramientas:
    """Las herramientas MCP de Ondo, con acceso por nombre y resultado ya convertido a dict."""

    def __init__(self, tools):
        self.tools = tools
        self.por_nombre = {t.name: t for t in tools}

    async def llamar(self, nombre: str, **args) -> dict:
        args = {k: v for k, v in args.items() if v is not None}
        res = await self.por_nombre[nombre].ainvoke(args)
        return _a_dict(res)


def _a_dict(res):
    if isinstance(res, dict):
        return res
    if isinstance(res, tuple):
        res = res[0]
    if isinstance(res, list):
        res = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in res)
    try:
        return json.loads(res)
    except (TypeError, ValueError):
        return {"texto": str(res)}


@asynccontextmanager
async def conectar_ondo():
    async with _cliente_mcp().session("ondo") as sesion:
        tools = await load_mcp_tools(sesion)
        yield Herramientas(tools)
