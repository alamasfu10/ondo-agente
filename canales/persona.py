"""Pasar una llamada de teléfono a una persona de Ondo, con el resumen del caso.

Cuando el grafo decide escalar, el canal de voz:
1. guarda el caso (con el resumen que ha escrito el nodo escalar);
2. espera a que el agente termine de despedirse;
3. cambia la TwiML de la llamada en curso por <Dial><Client>: Twilio deja de
   mandar el audio al agente y conecta al cliente con la página de la persona.

La persona atiende desde el navegador en http://localhost:7860/humano: la página
usa el Voice SDK de Twilio con la identidad PERSONA_ONDO y muestra el resumen
del caso cuando entra la llamada. Así no hace falta ninguna llamada saliente.

Variables del .env (solo para el teléfono):
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN   transferir la llamada (API de Twilio)
    TWILIO_API_KEY, TWILIO_API_SECRET       token de la página de la persona
    PERSONA_ONDO                            identidad de la persona (por defecto, persona-ondo)
"""

import asyncio
import os
from pathlib import Path

from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger

IDENTIDAD = os.getenv("PERSONA_ONDO", "persona-ondo")
PAGINA = Path(__file__).with_name("persona.html")

# Casos pasados a una persona en esta sesión del servidor, por llamada.
CASOS: dict[str, dict] = {}


def registrar(llamada: str, caso: dict) -> None:
    CASOS[llamada] = caso


def configurada() -> bool:
    return all(os.getenv(v) for v in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"))


def twiml_transferencia() -> str:
    return (
        '<Response><Dial timeout="20">'
        f"<Client>{IDENTIDAD}</Client>"
        '</Dial><Say language="es-ES">Ahora mismo no hay nadie disponible. '
        "Te llamaremos lo antes posible. Gracias.</Say></Response>"
    )


async def transferir(call_sid: str) -> None:
    """Cambia la llamada en curso: deja de ir al agente y suena en la página de la persona."""
    from twilio.rest import Client

    cliente = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    try:
        await asyncio.to_thread(cliente.calls(call_sid).update, twiml=twiml_transferencia())
    except Exception as e:  # la llamada sigue con el agente: mejor eso que colgar al cliente
        logger.error(f"No se pudo transferir la llamada {call_sid}: {e}")
        return
    logger.info(f"Llamada {call_sid} transferida a {IDENTIDAD}")


def montar_rutas() -> None:
    """Añade la página de la persona al servidor de Pipecat."""
    from pipecat.runner.run import app

    @app.get("/humano", include_in_schema=False)
    async def pagina():
        return HTMLResponse(PAGINA.read_text(encoding="utf-8"))

    @app.get("/humano/token")
    async def token():
        from twilio.jwt.access_token import AccessToken
        from twilio.jwt.access_token.grants import VoiceGrant

        faltan = [v for v in ("TWILIO_ACCOUNT_SID", "TWILIO_API_KEY", "TWILIO_API_SECRET") if not os.getenv(v)]
        if faltan:
            return JSONResponse({"error": f"Faltan en el .env: {', '.join(faltan)}"}, status_code=500)
        t = AccessToken(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_API_KEY"],
                        os.environ["TWILIO_API_SECRET"], identity=IDENTIDAD, ttl=3600)
        t.add_grant(VoiceGrant(incoming_allow=True))
        return {"token": t.to_jwt(), "identidad": IDENTIDAD}

    @app.get("/humano/caso")
    async def caso(llamada: str | None = None):
        if llamada and llamada in CASOS:
            return CASOS[llamada]
        return list(CASOS.values())[-1] if CASOS else {}
