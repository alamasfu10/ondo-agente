# Ondo desde cero

Un entorno vacío para construir con un asistente de IA (el chat de VS Code en modo Agent, Codex o Claude Code) el agente conversacional de atención al cliente de Ondo, el mismo caso del tema. No hay código, ni datos, ni skills, ni subagentes: solo lo que tendría una empresa antes de empezar.

| Fichero | Para qué |
|---|---|
| `AGENTS.md` | Instrucciones para el asistente: stack, cómo trabaja en cada paso, qué significa terminado y las reglas que no se negocian |
| `specs/` | Qué tiene que hacer el agente, incluidos los datos simulados que hay que generar |
| `PLAN.md` | Los doce pasos, con el prompt de cada uno y cómo comprobarlo |
| `requirements.txt` | Versiones exactas, para que el asistente no use APIs que no existen |
| `.env.example` | Claves y ajustes. Cópialo como `.env` |

## Cómo se usa

1. Descarga solo esta rama en una carpeta nueva: `git clone -b desde-cero https://github.com/alamasfu10/ondo-agente.git ondo-desde-cero`. Es una rama aparte, sin nada del kit de clase.
2. Copia `.env.example` como `.env` y pon tu clave de OpenAI.
3. Abre la carpeta en tu editor y sigue `PLAN.md` desde el paso 0, una conversación nueva por paso.

## Specs

| Spec | Qué fija |
|---|---|
| `producto.md` | Qué hace el agente, qué no y cómo se mide |
| `conversacion.md` | Cómo habla, en chat y en voz |
| `intenciones.md` | Qué entiende de cada mensaje y los casos frontera |
| `estado.md` | Qué recuerda entre turnos |
| `arquitectura.md` | Por qué es un grafo y cómo es un turno |
| `politicas.md` | Plazos, importes, horario: la fuente de todas las reglas |
| `datos.md` | Los datos simulados y los casos con nombre |
| `herramientas.md` | El contrato de las ocho herramientas MCP |
| `flujos/` | Pedido, cita, devolución y dudas generales, con conversaciones de ejemplo |
| `escalado.md` | Cuándo y cómo pasa a una persona |
| `canales.md` | Consola, Telegram y voz |
| `evaluacion.md` | Escenarios y criterios del juez |
