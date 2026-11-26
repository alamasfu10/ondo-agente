# AGENTS.md · Agente de atención al cliente de Ondo

Vas a construir, paso a paso, el agente conversacional de atención al cliente de Ondo, una tienda online ficticia de bicicletas eléctricas. El proyecto empieza vacío: solo están este fichero, `PLAN.md`, `specs/` y `requirements.txt`. Todo el código, los datos simulados y los tests los escribes tú.

## Las specs mandan

- Qué tiene que hacer el agente está en `specs/`. Antes de cada paso, lee las specs que ese paso indica en `PLAN.md`.
- Si una spec no dice algo que necesitas, o dos specs se contradicen, no lo decidas tú: para y pregúntalo, citando el fichero y la frase.
- No añadas funciones que ninguna spec pide.

## Stack

Fijo. No lo cambies ni añadas dependencias sin que te lo pidan.

- Python 3.11 o superior, con un entorno virtual clásico en `.venv/`. Ejecuta Python siempre desde él, aunque la terminal no lo tenga activado: `.venv/bin/python` en macOS y Linux, `.venv\Scripts\python` en Windows. En este fichero, `python` significa ese Python.
- Instalar: `python -m venv .venv` y después `python -m pip install -r requirements.txt`. Las versiones de `requirements.txt` son exactas y están probadas.
- El modelo es de OpenAI y sale de `OPENAI_MODEL`; si no está, `gpt-4.1-mini`.
- Las librerías del agente (cómo se organiza el turno y se guarda el estado, cómo se llama al modelo, cómo se valida lo que devuelve) no están fijadas aquí. Las propones tú en el paso 0, solo entre las de `requirements.txt` y a partir de lo que piden las specs, con la regla de cada spec que justifica cada una. Cuando las apruebe, quedan escritas en `specs/decisiones.md` y son fijas.
- La configuración (clave, modelo, `ONDO_HOY`, `ONDO_AHORA`) vive en `.env`. Todo punto de entrada (consola, Telegram, voz, servidor MCP, evaluación, generador de datos) la carga al arrancar con `load_dotenv` de `python-dotenv`, sin depender de que la terminal tenga las variables.
- MCP (`mcp`, con `FastMCP`) para las herramientas, en un servidor propio que el agente arranca por stdio.
- `python-telegram-bot` para Telegram y Pipecat para la voz en el navegador.
- Si dudas del nombre o la firma de una función de una librería, búscalo en `.venv/lib/python*/site-packages/` en lugar de suponerlo. Las versiones instaladas pueden no coincidir con lo que recuerdas.

## Estructura del proyecto

La creas tú a medida que avanzas:

- `scripts/generar_datos.py`: genera los datos simulados (paso 1).
- `data/`: los datos simulados y la base de conocimiento. `data/estado/` guarda lo que crea el agente (citas, devoluciones, casos) y no va a git.
- `ondo_mcp/`: el servidor MCP con las herramientas (paso 2).
- `agente/`: el estado, las llamadas al modelo, el flujo del turno y un fichero por flujo de conversación en `agente/flujos/`.
- `canales/`: consola, Telegram y voz.
- `evaluacion/`: escenarios, cliente simulado, juez y la suite.
- `tests/`: un fichero por pieza, `tests/test_<pieza>.py`.

## Cómo trabajas en cada paso

1. Lee el paso en `PLAN.md` y las specs que cita.
2. Escribe primero los tests que traducen la spec: un test por regla o por conversación de ejemplo. Cada test lleva un comentario con la spec y la regla que comprueba.
3. Ejecútalos y comprueba que fallan por la razón esperada.
4. Implementa lo mínimo para que pasen. No adelantes trabajo de pasos siguientes.
5. Ejecuta todos los tests: `python -m pytest`.
6. Termina con un resumen corto: ficheros creados o cambiados, qué regla cubre cada test y qué dudas te han quedado de las specs.

## Terminado significa

1. Los tests del paso pasan y los de pasos anteriores siguen pasando.
2. Los tests no usan red ni clave de OpenAI: el modelo y las herramientas se sustituyen por versiones falsas que devuelven datos fijos.
3. Has explicado en pocas líneas qué has cambiado y por qué.
4. No has tocado nada fuera de lo que pedía el paso.

## Reglas que no se negocian

Valen para todo el código, en todos los pasos:

- Las decisiones con consecuencias se toman en código, no en el prompt: qué dato falta, qué herramienta se llama, cuándo se pide confirmación, cuándo se pasa a una persona. El modelo interpreta el mensaje y redacta la respuesta; nada más.
- Una acción con efecto (reservar una cita, crear una devolución) solo se ejecuta tras un «sí» claro del cliente. Una respuesta ambigua no cuenta.
- Nunca se inventan datos: fechas, códigos, importes y plazos salen de las herramientas o de la base de conocimiento.
- Nunca se dan datos de un pedido a quien no es su titular.
- Si una herramienta falla, no se da la operación por hecha y se le dice al cliente.
- Las reglas de negocio (plazos, importes, horario, número de intentos) son constantes con nombre en el código y salen de `specs/politicas.md`.
- Las claves van en `.env`, que no se sube a git. Nunca las imprimas.

## Comandos

Los vas creando en los pasos. Cuando existan:

- Tests: `python -m pytest`
- Datos: `python scripts/generar_datos.py`
- Consola: `python -m canales.consola --traza`
- Telegram: `python -m canales.telegram_bot`
- Voz: `python -m canales.voz`
- Evaluación: `python -m evaluacion.suite`, o `--solo <id>` para un escenario
