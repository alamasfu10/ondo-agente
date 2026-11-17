---
name: completar-flujo
description: Implementa o cambia un paso de un flujo de conversación del agente de Ondo (cita, devolución, pedido u otro nuevo) en agente/flujos/, con su test primero. Úsala cuando pidan completar, añadir o cambiar un flujo, un paso, una confirmación, una reparación o un paso a persona. No sirve para cambiar prompts de llm.py, el servidor MCP ni los canales.
---

# Completar un flujo de conversación

Sigue estos pasos en orden. No te saltes el 3: el test es la especificación.

1. Lee `AGENTS.md` (reglas de la conversación), `agente/flujos/comun.py` y el flujo que vas a tocar. Si es un flujo nuevo, lee `agente/flujos/cita.py` como modelo.
2. Escribe en dos o tres líneas, para quien te lo pidió, qué pasos vas a implementar. Para cada paso: qué dato pide, qué valor de `pendiente` usa, qué opciones (botones) ofrece y qué herramienta llama.
3. Tests primero. Si ya existe un test del flujo en `tests/`, ejecútalo y comprueba que falla por lo que falta. Si no existe, escríbelo siguiendo el patrón de `tests/test_cita.py` (herramientas simuladas, estado construido a mano) y cubre como mínimo:
   - el camino feliz;
   - que la acción con efecto no se ejecuta sin un «sí» claro (con `confirma` False y con None);
   - una respuesta que no se entiende (suma un intento y vuelve a ofrecer las opciones);
   - el paso a una persona al superar los reintentos o cuando una regla lo exige;
   - el fallo de la herramienta.
4. Implementa lo mínimo para que los tests pasen, con las convenciones de `AGENTS.md`: un dato por paso, `borrador()` con la instrucción y los datos (nunca el texto final), `eleccion()` para las opciones y `fin_de_flujo()` al cerrar.
5. Ejecuta los tests con el Python del entorno virtual, como dice `AGENTS.md` (`.venv/bin/python -m pytest`). Si algo falla, arregla el código, no el test.
6. Termina con un resumen corto: pasos implementados, tests nuevos y cómo probarlo en la consola (`python -m canales.consola --estado`, con el entorno virtual activado) con una conversación de ejemplo.
