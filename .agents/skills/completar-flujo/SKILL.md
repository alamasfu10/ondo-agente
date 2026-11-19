---
name: completar-flujo
description: Implementa o cambia un paso de un flujo de conversación del agente de Ondo (cita, devolución, pedido u otro nuevo) en agente/flujos/, con su test primero. Úsala cuando pidan completar, añadir o cambiar un flujo, un paso, una confirmación, una reparación o un paso a persona. No sirve para cambiar prompts de llm.py, el servidor MCP ni los canales.
---

# Completar un flujo de conversación

Sigue estos pasos en orden. No te saltes el 3: el test es la especificación.

1. Lee `AGENTS.md` (reglas de la conversación), `agente/flujos/comun.py` y el flujo que vas a tocar. Si es un flujo nuevo, lee `agente/flujos/cita.py` como modelo.
2. Escribe en dos o tres líneas, para quien te lo pidió, qué pasos vas a implementar. Para cada paso: qué dato pide, qué valor de `pendiente` usa, qué opciones (botones) ofrece y qué herramienta llama.
3. Tests primero. Hazlo siempre antes de cambiar el flujo:
   - Si te piden escribir los tests, escríbelos desde la especificación que te den, siguiendo el patrón de la sección Tests de `AGENTS.md` (herramientas simuladas, estado construido a mano), con un test por comportamiento y como mínimo los casos que cubra la especificación: camino feliz, acción con efecto sin un «sí» claro (con `confirma` False y con None), respuesta que no se entiende, paso a una persona al superar los reintentos y fallo de la herramienta. Ejecútalos y comprueba que fallan por lo que falta, no por un error del test. Si solo te pidieron los tests, para aquí y no implementes nada.
   - Si ya existen tests del flujo, ejecútalos y comprueba que fallan por lo que falta.
4. Implementa solo el paso que te piden, y lo mínimo para que sus tests pasen, con las convenciones de `AGENTS.md`: un dato por paso, `borrador()` con la instrucción y los datos (nunca el texto final), `eleccion()` para las opciones y `fin_de_flujo()` al cerrar.
5. Ejecuta los tests con el Python del entorno virtual, como dice `AGENTS.md` (`.venv/bin/python -m pytest`). Si algo falla, arregla el código, no el test.
6. Termina con un resumen corto: pasos implementados, tests nuevos y cómo probarlo en la consola (`python -m canales.consola --traza`, con el entorno virtual activado) con una conversación de ejemplo.
