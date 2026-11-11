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
| `app/` | API con FastAPI (la usaremos con ngrok y en los días 2 y 3) | Poco |
| `scripts/comprobar_entorno.py` | Comprueba que todo está listo | No |

Herramientas del servidor MCP: `buscar_cliente`, `estado_pedido`, `crear_devolucion`,
`huecos_taller`, `reservar_cita`, `escalar_a_humano` y `buscar_conocimiento`.

## Puesta en marcha

```bash
git clone https://github.com/alamasfu10/ondo-agente.git
cd ondo-agente
uv sync
cp .env.example .env        # y pon tu OPENAI_API_KEY
uv run python scripts/comprobar_entorno.py
```

## Cómo se usa

```bash
uv run python -m canales.consola --estado   # chat en la terminal, mostrando el estado
uv run python -m canales.telegram_bot       # el agente en tu bot de Telegram
uv run python -m agente.react_fallo         # demo: el agente genérico que falla
uv run uvicorn app.main:app --port 8000     # la API (GET /salud, POST /chat)
uv run pytest                               # pruebas del servidor MCP
```

Datos de prueba útiles: `lucia.martin@example.com` (pedido `OND-10231` en camino, vive en Madrid),
`javier.ortega@example.com` (pedido `OND-10233` entregado hace 12 días), `marta.ruiz@example.com`
(pedido `OND-10234` entregado hace 45 días), `pau.ferrer@example.com` (pedido `OND-10235` de 2.959 €).

Lo que crea el agente (citas, devoluciones y casos pasados a una persona) se guarda en
`data/estado/`. Bórrala para empezar de cero.

## Coste

El agente usa la API de OpenAI con tu clave: unas dos llamadas al modelo por mensaje con
`gpt-4.1-mini`, menos de un céntimo por conversación. El índice del RAG se calcula una vez
(una fracción de céntimo) y se guarda en `data/.cache/`.
