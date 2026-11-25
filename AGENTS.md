# AGENTS.md · ondo-agente

Agente de atención al cliente de Ondo, una tienda online ficticia de bicicletas eléctricas. Es un grafo de LangGraph que atiende por consola, por Telegram y por voz en el navegador (con Pipecat), y usa las herramientas de un servidor MCP.

## Entorno

El proyecto usa un entorno virtual clásico en `.venv/`. Ejecuta Python siempre desde él, aunque tu terminal no lo tenga activado: `.venv/bin/python` en macOS y Linux, `.venv\Scripts\python` en Windows. En los comandos de abajo, `python` significa ese Python.

## Comandos

- Instalar dependencias: `python -m pip install -r requirements.txt`
- Tests (sin clave de OpenAI, sin red): `python -m pytest`
- Solo los tests de un fichero: `python -m pytest tests/test_<flujo>.py`
- Hablar con el agente en la terminal: `python -m canales.consola --traza` (recorrido por el grafo y estado en cada turno; `--estado` solo el estado)
- Bot de Telegram: `python -m canales.telegram_bot`
- Voz en el navegador: `python -m canales.voz` (http://localhost:7860/client; `--traza` imprime los frames de cada turno, `--tiempos` el tiempo de cada tramo, `--como-chat` usa el agente del chat tal cual, `--voz elevenlabs` la voz de ElevenLabs)
- Práctica del día 3: `python -m practica.cascada_minima --traza` (la solución, en `practica.solucion.cascada_minima`)
- Evaluación con conversaciones simuladas (usa la clave de OpenAI y cuesta céntimos): `python -m evaluacion.suite`, o `--solo <id>` para un escenario

No instales paquetes nuevos ni cambies `requirements.txt` sin que te lo pidan.

## Terminado significa

1. Los tests de lo que te han pedido pasan. Si te piden un solo paso de un flujo, los tests de los pasos que no te han pedido pueden seguir en rojo: dilo en tu resumen y no los toques.
2. Has explicado qué ficheros has cambiado y por qué, en pocas líneas.
3. No has tocado nada fuera de lo que se pidió.

## Dónde va cada cosa

- `agente/flujos/`: un fichero por flujo (pedido, cita, devolución). Aquí se trabaja casi siempre.
- `agente/grafo.py`: el enrutado entre nodos. Cámbialo solo si el cambio no cabe en un flujo.
- `agente/llm.py`: los prompts de interpretar y redactar. `PERSONA_ONDO` es el prompt del chat y `PERSONA_ONDO_VOZ` el de voz; el canal lo elige.
- `canales/voz.py`: el pipeline de voz (STT, turno, grafo, TTS). El grafo no cambia por la voz. `canales/observar.py`: los observadores de `--traza` y `--tiempos`.
- `practica/cascada_minima.py`: la práctica del día 3, una cascada de Pipecat sin el grafo. Usa la API de Pipecat 1.15 (`PipelineWorker`, `WorkerRunner`, `LLMContextAggregatorPair`, servicios con `settings=...Settings(...)`); si dudas de un nombre, búscalo en `.venv/lib/python*/site-packages/pipecat/` en lugar de inventarlo. No mires `practica/solucion/` salvo que te lo pidan.
- `ondo_mcp/` y `data/`: el servidor MCP y los datos de Ondo. Se dan hechos: no los modifiques.
- `evaluacion/`: la suite de evaluación. Los escenarios (`escenarios.json`) se pueden ampliar; no cambies lo que espera un escenario para que pase.

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

- Los tests de flujos usan herramientas simuladas, sin modelo ni MCP, en `tests/test_<flujo>.py`. Dos piezas:
  - Una clase `HerramientasFalsas` con `async def llamar(self, nombre, **args)` que devuelve datos fijos (por ejemplo, `huecos_taller` con un taller y varios huecos, `reservar_cita` con éxito o con `{"ok": False, "error": ...}`), apunta cada llamada en una lista y lanza `AssertionError` si el flujo llama a una herramienta que no debería.
  - Una función que construye el estado a mano: `messages` con un `HumanMessage` del cliente, `cliente`, `datos`, `huecos`, `opciones`, `pendiente`, `intentos_fallidos` y `ultima` (la interpretación del modelo, con `intencion`, `eleccion` y `confirma`).
- Cada test llama a `await flujo_x(estado, herramientas)`, y comprueba el dict que devuelve (`pendiente`, `intencion`, `intentos_fallidos`, `borrador["opciones"]`...) y las herramientas llamadas. Los tests son `async def` sin decorador: `pytest.ini` ya los ejecuta.
- Si te piden los tests antes que el código, escríbelos desde la especificación que te den, sin implementar nada, y ejecútalos para comprobar que fallan por lo que falta, no por un error del propio test.
- Si un test falla porque el código está mal, se arregla el código. No cambies lo que espera un test para que pase.

## Límites

- Nunca leas, muestres ni copies el contenido de `.env`.
- No borres ficheros de `data/estado/` salvo que te lo pidan.
