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
| `canales/` | El agente en la terminal y en Telegram | Poco |
| `app/` | API con FastAPI (se usa en los días 2 y 3, con ngrok) | Poco |
| `scripts/comprobar_entorno.py` | Comprueba que todo está listo | No |
| `tests/` | Pruebas del servidor MCP y del flujo de cita (`test_cita.py`, la especificación de la práctica del día 1) | Las amplía Codex |
| `AGENTS.md` | Las reglas del proyecto para Codex: comandos, convenciones y reglas de la conversación | Poco |
| `.agents/skills/completar-flujo/` | Skill de Codex para implementar un paso de un flujo, con tests primero | No |
| `.codex/agents/revisor_conversacion.toml` | Subagente de Codex que revisa un flujo contra las reglas, sin editar | No |

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
python -m canales.telegram_bot       # el agente en tu bot de Telegram
python -m agente.react_fallo         # demo: el agente genérico que falla
uvicorn app.main:app --port 8000     # la API (GET /salud, POST /chat)
python -m pytest                     # pruebas (sin clave de OpenAI)
```

Datos de prueba útiles: `lucia.martin@example.com` (pedido `OND-10231` en camino, vive en Madrid),
`javier.ortega@example.com` (pedido `OND-10233` entregado hace 12 días), `marta.ruiz@example.com`
(pedido `OND-10234` entregado hace 45 días), `pau.ferrer@example.com` (pedido `OND-10235` de 2.959 €).

Lo que crea el agente (citas, devoluciones y casos pasados a una persona) se guarda en
`data/estado/`. Bórrala para empezar de cero.

## Con Codex

El código del tema se le pide a Codex (extensión `openai.chatgpt` de VS Code, con tu clave de API)
en lenguaje natural. Abre esta carpeta en VS Code para que Codex lea `AGENTS.md`,
la skill (`$completar-flujo`) y el subagente (`revisor_conversacion`). Haz un commit antes de cada
petición: `git restore .` deshace lo que no te convenza.

## Coste

El agente usa la API de OpenAI con tu clave: unas dos llamadas al modelo por mensaje con
`gpt-4.1-mini`, menos de un céntimo por conversación. Las peticiones a Codex gastan más: leen el proyecto y ejecutan
los tests varias veces. El índice del RAG se calcula una vez
(una fracción de céntimo) y se guarda en `data/.cache/`.
