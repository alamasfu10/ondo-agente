# ondo-agente

Kit de partida del Tema 10 del Máster en Ingeniería de Automatización con IA Agéntica de EBIS:
**Agentes conversacionales: automatización de chats y llamadas telefónicas**.

Ondo es una tienda online ficticia de bicicletas eléctricas que vende en España, Francia, Italia y
Portugal. Durante el tema construyes su agente de atención al cliente: primero por chat (Telegram),
después por voz y por teléfono, y por último lo evalúas. Todos los datos son inventados.

## Qué trae el kit

| Carpeta | Qué hay | ¿Lo tocas? |
|---|---|---|
| `ondo_mcp/` | Servidor MCP de Ondo con 7 herramientas y el RAG de la base de conocimiento | No |
| `data/` | 30 clientes, 40 pedidos, catálogo, 7 talleres y 10 documentos de política | No |
| `agente/` | El grafo de LangGraph del agente: estado, interpretación, flujos y redacción | Sí |
| `agente/flujos/` | Un fichero por flujo: pedido (hecho), cita (a medias), devolución (por hacer) | Sí |
| `canales/` | El agente en la terminal, en Telegram y por voz (navegador y teléfono, día 3) | Poco |
| `app/` | API de texto con FastAPI (`/salud` y `/chat`) | Poco |
| `evaluacion/` | Suite de evaluación del día 2: escenarios, cliente simulado, juez e informe | Los escenarios |
| `scripts/comprobar_entorno.py` | Comprueba que todo está listo | No |
| `tests/` | Pruebas del servidor MCP. Los tests del flujo de cita los escribes tú en la práctica del día 2 | Los escribe el agente del chat |
| `AGENTS.md` | Las reglas del proyecto para el agente del chat: comandos, convenciones y reglas de la conversación | Poco |
| `.agents/skills/completar-flujo/` | Skill para implementar un paso de un flujo, con tests primero | No |
| `.github/agents/revisor_conversacion.agent.md` | Subagente que revisa un flujo contra las reglas, solo con herramientas de lectura | No |

Herramientas del servidor MCP: `buscar_cliente`, `estado_pedido`, `crear_devolucion`,
`huecos_taller`, `reservar_cita`, `escalar_a_humano` y `buscar_conocimiento`.

## Puesta en marcha

Con git (no hace falta cuenta de GitHub):

```bash
git clone https://github.com/alamasfu10/ondo-agente.git
cd ondo-agente
```

O con el ZIP del día que encontrarás en el campus (`ondo-agente-dia1.zip`...): descomprímelo y, dentro de
la carpeta, `git init && git add -A && git commit -m "Kit"` para poder deshacer los cambios del asistente.

Después, en los dos casos, crea el entorno virtual e instala las dependencias (necesitas Python 3.11 o superior;
recomendamos 3.12):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows (PowerShell): .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env               # y pon tu OPENAI_API_KEY
python scripts/comprobar_entorno.py
```

En cada terminal nueva, activa el entorno antes de nada (`source .venv/bin/activate`). En VS Code, elige
el intérprete de `.venv` (**Python: Select Interpreter**) y las terminales nuevas lo activan solas.

## Cómo se usa

Con el entorno activado:

```bash
python -m canales.consola --estado   # chat en la terminal, mostrando el estado
python -m canales.consola --traza    # igual, y además el recorrido por el grafo en cada turno
python -m canales.telegram_bot       # el agente en tu bot de Telegram
python -m canales.voz                # el agente por voz en el navegador (día 3): http://localhost:7860
python -m agente.react_fallo         # demo: el agente genérico que falla
uvicorn app.main:app --port 8000     # la API (GET /salud, POST /chat)
python -m pytest                     # pruebas (sin clave de OpenAI)
python -m evaluacion.suite           # evaluación con conversaciones simuladas (día 2)
```

Datos de prueba útiles: `lucia.martin@example.com` (pedido `OND-10231` en camino, vive en Madrid),
`javier.ortega@example.com` (pedido `OND-10233` entregado hace 12 días), `marta.ruiz@example.com`
(pedido `OND-10234` entregado hace 45 días), `pau.ferrer@example.com` (pedido `OND-10235` de 2.959 €).

Lo que crea el agente (citas, devoluciones y casos pasados a una persona) se guarda en
`data/estado/`. Bórrala para empezar de cero.

## Voz y teléfono (día 3)

```bash
python -m canales.voz                 # abre http://localhost:7860, pulsa Connect y habla (mejor con auriculares)
python -m canales.voz --como-chat     # el agente del chat tal cual (redacta para leer, sin frase de espera)
python -m canales.voz --voz elevenlabs  # la voz de ElevenLabs (ELEVENLABS_API_KEY y ELEVENLABS_VOICE_ID en el .env)
```

Es una cascada de Pipecat: el audio del navegador llega por WebRTC, `gpt-transcribe` lo pasa a texto, el
detector de turno decide cuándo has terminado de hablar, el grafo de siempre decide qué responder con el
prompt de voz de `agente/llm.py` (`PERSONA_ONDO_VOZ`) y `gpt-4o-mini-tts` lo dice. Con `--voz elevenlabs`, lo
dice una voz de ElevenLabs: solo cambia esa pieza de la tubería, en el navegador y en el teléfono.

**A partir del 6/01/2027**, OpenAI retira `gpt-4o-mini-tts`, la voz por defecto del kit, y la voz de OpenAI deja
de sonar. Desde esa fecha usa la de ElevenLabs: crea una cuenta gratuita en elevenlabs.io, copia tu clave
(«API Keys») y el ID de una voz en español de su biblioteca («Voices») en `ELEVENLABS_API_KEY` y
`ELEVENLABS_VOICE_ID` del `.env`, y arranca siempre con `python -m canales.voz --voz elevenlabs`. El plan
gratuito da para la práctica. El canal avisa al arrancar si pides la voz de OpenAI después de esa fecha. Lo que dices y lo que
responde el agente sale en la terminal, con lo que tarda cada turno. Si el micrófono no funciona, el
cuadro de texto de la página también le llega al agente.

Si alguien deja un podcast o la tele hablando, el agente no se pasa la llamada contestando a trozos: cuando
el cliente lleva más de 30 segundos seguidos hablando, o más de 70 palabras sin dejarle contestar, corta,
dice «Perdona, me he perdido: es mucho a la vez. ¿Me lo cuentas en una frase?», no manda ese texto al grafo y
no se deja interrumpir mientras lo dice. Los límites están al principio de `canales/voz.py`
(`MAX_SEGUNDOS_TURNO` y `MAX_PALABRAS_TURNO`).

El teléfono es una demo del docente: `python -m canales.voz -t twilio -x <tu-dominio-de-ngrok>` atiende
las llamadas de un número de Twilio (con `TWILIO_ACCOUNT_SID` y `TWILIO_AUTH_TOKEN` en el `.env`) y, cuando el
agente pasa el caso a una persona, transfiere la llamada a la página `http://localhost:7860/humano`, que
muestra el resumen del caso. Detalles en `canales/persona.py`.

## Con el chat de VS Code

El código del tema se le pide al chat de VS Code en lenguaje natural, con tu clave de OpenAI (sesión
**Local**, modelo de OpenAI añadido en **Chat: Manage Language Models**). Modo **Ask** para entender el
código y modo **Agent** para cambiarlo. Abre esta carpeta en VS Code para que el chat lea `AGENTS.md`, la
skill (`/completar-flujo`) y el subagente (`revisor_conversacion`). Haz un commit antes de cada petición:
`git restore .` deshace lo que no te convenza.

## Coste

El agente usa la API de OpenAI con tu clave: unas dos llamadas al modelo por mensaje con
`gpt-4.1-mini`, menos de un céntimo por conversación. Por voz se añade la transcripción y la síntesis de
cada turno, que se pagan por minuto de audio. Las peticiones al chat en modo Agent gastan más: leen el proyecto y ejecutan
los tests varias veces. El índice del RAG se calcula una vez
(una fracción de céntimo) y se guarda en `data/.cache/`.
