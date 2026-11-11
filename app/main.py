"""API del agente de Ondo con FastAPI.

    uv run uvicorn app.main:app --reload --port 8000

- GET  /salud   comprueba que el servidor responde (no usa el agente).
- POST /chat    {"conversacion": "abc", "texto": "Hola"} → respuesta del agente.

El día 1 la usamos para probar ngrok. El día 2 esta misma aplicación recibe
el audio de las llamadas; el día 3, las conversaciones simuladas.
"""

import asyncio

from fastapi import FastAPI
from pydantic import BaseModel

from agente.agente import AgenteOndo

app = FastAPI(title="Agente de Ondo")
_agente: AgenteOndo | None = None
_cerrojo = asyncio.Lock()


async def agente() -> AgenteOndo:
    """Arranca el agente la primera vez que se necesita."""
    global _agente
    async with _cerrojo:
        if _agente is None:
            _agente = await AgenteOndo().__aenter__()
    return _agente


@app.on_event("shutdown")
async def cerrar() -> None:
    if _agente is not None:
        await _agente.__aexit__(None, None, None)


class Mensaje(BaseModel):
    conversacion: str
    texto: str


class Respuesta(BaseModel):
    texto: str
    opciones: list[str]


@app.get("/salud")
async def salud() -> dict:
    return {"ok": True, "servicio": "agente de Ondo"}


@app.post("/chat", response_model=Respuesta)
async def chat(m: Mensaje) -> Respuesta:
    r = await (await agente()).responder(m.conversacion, m.texto)
    return Respuesta(texto=r.texto, opciones=r.opciones)
