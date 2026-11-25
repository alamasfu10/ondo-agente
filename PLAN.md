# PLAN · Construir el agente de Ondo desde cero

Doce pasos, en este orden. Cada uno se le pide al asistente con el prompt de abajo, en una conversación nueva. Antes de cada paso, un commit (`git add -A && git commit -m "Antes del paso N"`), para poder volver atrás. Al terminar, la revisión del final.

El orden importa: primero lo que no depende del modelo (datos, herramientas), luego el cerebro (estado y grafo), luego cada flujo, después la evaluación y los canales al final. Quien empieza por la voz depura dos cosas a la vez.

## Paso 0 · Revisar las specs (modo Ask)

> Lee AGENTS.md y todos los ficheros de specs/. No escribas código. Dime qué falta para poder construir el agente, qué se contradice entre ficheros y qué está tan abierto que tendrías que inventarlo. Cita el fichero y la frase en cada punto.

Terminado: una lista de huecos. Corrígelos en las specs antes de seguir.

## Paso 1 · Datos simulados

> Lee AGENTS.md y specs/datos.md, specs/politicas.md y specs/herramientas.md («Fecha de referencia»). Crea el entorno virtual e instala requirements.txt. Escribe scripts/generar_datos.py, con semilla fija, que genere data/ con el catálogo, los talleres, los clientes, los pedidos y la base de conocimiento, incluidos todos los casos con nombre. Escribe primero tests/test_datos.py con lo que pide la spec y comprueba que falla.

Terminado: `python scripts/generar_datos.py` dos veces da los mismos ficheros y `python -m pytest` pasa.

## Paso 2 · Servidor MCP

> Lee specs/herramientas.md. Escribe ondo_mcp/ con la lectura de datos (fecha de referencia ONDO_HOY y carpeta de estado ONDO_ESTADO) y el servidor FastMCP con las ocho herramientas. Tests primero en tests/test_herramientas.py, sin red: cada respuesta y cada error de la spec.

Terminado: tests en verde y `python -m ondo_mcp.server` arranca y espera por stdio.

## Paso 3 · Estado, interpretar, redactar y consola

> Lee specs/arquitectura.md, specs/estado.md, specs/intenciones.md y specs/conversacion.md. Escribe agente/estado.py (estado e interpretación con Pydantic), agente/llm.py (interpretar y redactar, con un prompt para chat y otro para voz), agente/herramientas.py (cliente MCP), un grafo mínimo interpretar, saludar y redactar, agente/agente.py y canales/consola.py con --traza. Tests sin red con un modelo falso: la palabra «quemado» fuerza seguridad, el idioma se guarda, redactar recibe el borrador.

Terminado: tests en verde y, con tu clave, `python -m canales.consola --traza` saluda, dice que es una IA y responde en el idioma del cliente.

## Paso 4 · Grafo: identificar, reparar y escalar

> Lee specs/arquitectura.md y specs/escalado.md. Completa el grafo con la ruta en el orden de la spec y los nodos identificar, reparar, escalar y ya_escalado, con la herramienta anotar_caso. Tests primero: cada disparador de escalado, los tres intentos de reparar, que con un caso abierto la seguridad no abre otro, que el canal llega a escalar_a_humano y que ya_escalado en voz no pide escribir.

Terminado: tests en verde y, en la consola, «quiero hablar con una persona» abre un caso y una batería que huele a quemado da las instrucciones y un caso urgente.

## Paso 5 · Flujo de pedido

> Lee specs/flujos/pedido.md. Tests primero en tests/test_pedido.py con herramientas falsas, uno por regla y por conversación de ejemplo. Comprueba que fallan. Después implementa agente/flujos/pedido.py.

Terminado: tests en verde; en la consola, Lucía (C001) consulta su pedido y Andrés (C008) no consigue datos de OND-10231.

## Paso 6 · Flujo de cita

> Lee specs/flujos/cita.md. Tests primero en tests/test_cita.py, con herramientas falsas: elegir hueco, ninguno me va bien, no entender la elección, confirmar, respuesta ambigua que no reserva, hueco ocupado al reservar y ciudad sin taller. Después implementa agente/flujos/cita.py.

Terminado: tests en verde; en la consola, Hugo (C026) reserva una revisión en Madrid.

## Paso 7 · Flujo de devolución

> Lee specs/flujos/devolucion.md y specs/politicas.md. Tests primero en tests/test_devolucion.py, con un caso por comprobación y por ejemplo (Javier, Marta, Pau, Iván, Sergio). Después implementa agente/flujos/devolucion.py con el plazo y el importe como constantes.

Terminado: tests en verde; en la consola, Javier devuelve OND-10233 y Marta pasa a una persona.

## Paso 8 · Dudas generales

> Lee specs/flujos/informacion.md. Implementa el nodo informar con buscar_conocimiento. Tests sin red: con fragmentos responde con ellos; sin fragmentos ofrece una persona.

Terminado: tests en verde; en la consola, la garantía de la batería sale con sus cifras y «¿enviáis a Alemania?» ofrece una persona.

## Paso 9 · Evaluación

> Lee specs/evaluacion.md. Escribe evaluacion/ (escenarios, simulador, comprobaciones, juez y suite). Ejecuta la suite y dame la tabla. No cambies lo que espera un escenario para que pase: si uno falla, dime por qué.

Terminado: la suite se ejecuta de principio a fin. Anota cuántos escenarios pasan y el porcentaje del juez: es la cifra de partida.

## Paso 10 · Telegram

> Lee specs/canales.md, «Telegram». Escribe canales/telegram_bot.py con la clase del agente. Sin tocar el grafo.

Terminado: conversación real con tu bot, con botones.

## Paso 11 · Voz en el navegador

> Lee specs/canales.md, «Voz», y specs/conversacion.md, «En voz». Escribe canales/voz.py con Pipecat. Usa la API de la versión instalada: busca los nombres en .venv/lib/python*/site-packages/pipecat/ antes de usarlos. Sin tocar el grafo.

Terminado: conversación por voz en http://localhost:7860, con la frase de espera y la interrupción funcionando.

## Revisión al final de cada paso (modo Ask)

> Compara lo que se ha hecho en este paso con las specs que cita PLAN.md. Dime qué regla no se cumple o no tiene test, citando la spec. No cambies nada.
