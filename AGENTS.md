# AGENTS.md · ondo-agente

Agente de atención al cliente de Ondo, una tienda online ficticia de bicicletas eléctricas. Es un grafo de LangGraph que atiende por consola y por Telegram, y usa las herramientas de un servidor MCP.

## Comandos

- Instalar dependencias: `uv sync`
- Tests (sin clave de OpenAI, sin red): `uv run pytest`
- Solo el flujo de cita: `uv run pytest tests/test_cita.py`
- Hablar con el agente en la terminal: `uv run python -m canales.consola --estado`
- Bot de Telegram: `uv run python -m canales.telegram_bot`

Usa siempre `uv run`. No instales paquetes con pip ni cambies `pyproject.toml` sin que te lo pidan.

## Terminado significa

1. `uv run pytest` pasa entero.
2. Has explicado qué ficheros has cambiado y por qué, en pocas líneas.
3. No has tocado nada fuera de lo que se pidió.

## Dónde va cada cosa

- `agente/flujos/`: un fichero por flujo (pedido, cita, devolución). Aquí se trabaja casi siempre.
- `agente/grafo.py`: el enrutado entre nodos. Cámbialo solo si el cambio no cabe en un flujo.
- `agente/llm.py`: los prompts de interpretar y redactar.
- `ondo_mcp/` y `data/`: el servidor MCP y los datos de Ondo. Se dan hechos: no los modifiques.

## Cómo se escribe un flujo

- Un flujo es una función `async def flujo_x(estado, h) -> dict` que devuelve solo los campos del estado que cambian.
- Cada paso pide un solo dato y anota en `pendiente` qué está esperando.
- Lo que el agente tiene que decir va en `borrador(instruccion, datos, opciones)`: qué decir y con qué datos, nunca el texto final. El nodo `redactar` escribe el mensaje con el tono de Ondo y en el idioma del cliente.
- Para saber qué opción eligió el cliente, usa `eleccion(estado, opciones)` de `agente/flujos/comun.py`.
- Las herramientas se llaman con `await h.llamar("nombre", argumento=valor)` y devuelven un dict.
- Al terminar un flujo, devuelve `fin_de_flujo()`, que conserva al cliente identificado.

## Reglas de la conversación

Son las reglas de diseño de Ondo. Cualquier cambio en un flujo las cumple:

- Una acción con efecto (`reservar_cita`, `crear_devolucion`) solo se ejecuta después de un «sí» claro: `estado["ultima"]["confirma"] is True` o el botón de confirmar. Una respuesta ambigua no cuenta como sí.
- Si no se entiende lo que elige el cliente, se suma uno a `intentos_fallidos` y se le vuelven a ofrecer las opciones. Al superar `MAX_REINTENTOS`, se pasa a una persona devolviendo `"intencion": "persona"`. Si se sabe el motivo, se guarda en `datos["motivo_escalado"]`.
- Nunca se inventan datos (fechas, códigos, importes, plazos): salen de las herramientas.
- Si una herramienta falla, no se da la operación por hecha y se le dice al cliente.
- La seguridad (batería que se calienta, frenos) la resuelve el grafo antes de llegar a los flujos. No la toques desde un flujo.

## Tests

- Los tests de flujos usan herramientas simuladas, sin modelo ni MCP. Sigue el patrón de `tests/test_cita.py` (`HerramientasFalsas` y una función que construye el estado).
- Si un test falla porque el código está mal, se arregla el código. No cambies lo que espera un test para que pase.

## Límites

- Nunca leas, muestres ni copies el contenido de `.env`.
- No borres ficheros de `data/estado/` salvo que te lo pidan.
