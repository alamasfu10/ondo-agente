# Arquitectura · cómo se organiza el agente

## La decisión principal

El agente es un **grafo de LangGraph** con estado explícito, y no un agente ReAct que decide solo qué herramienta llamar. Motivo: Ondo tiene reglas que no pueden depender del modelo (confirmar antes de reservar, comprobar el titular, escalar la seguridad, el plazo y el importe de una devolución). Esas reglas van en código, en nodos y rutas que se pueden probar sin modelo.

## Un turno

```
mensaje ─► interpretar ─► ruta (código) ─► nodo de la gestión ─► redactar ─► respuesta
```

1. **interpretar** (modelo, salida estructurada con Pydantic): devuelve la interpretación de `intenciones.md`. Después, en código: la lista de palabras de peligro fuerza `seguridad`, se guardan los datos que trae el mensaje y se detecta el cambio de tema.
2. **ruta** (código), en este orden:
   1. si ya hay un caso abierto, `ya_escalado` (incluida la seguridad: no se abre otro caso);
   2. si es seguridad o pide una persona, `escalar`;
   3. si no se entiende: si un flujo espera un dato, el flujo repara; si no, `reparar`;
   4. si es pedido, devolución o cita: `identificar` si no hay cliente, el flujo si lo hay;
   5. si es información, `informar`;
   6. en otro caso, `saludar`.
3. **Nodos** (código): cada uno decide qué decir y deja un borrador. Los flujos están en `agente/flujos/`, uno por fichero, y pueden pedir pasar a una persona poniendo la intención `persona` y el motivo en `datos.motivo_escalado`.
4. **redactar** (modelo): convierte el borrador en el mensaje final según `conversacion.md`.

## Nodos

| Nodo | Qué hace | Spec |
|---|---|---|
| `interpretar` | Entiende el mensaje | `intenciones.md` |
| `identificar` | Pide el email y busca al cliente | abajo |
| `flujo` | Despacha a pedido, devolución o cita | `flujos/` |
| `informar` | Responde con la base de conocimiento | `flujos/informacion.md` |
| `saludar` | Saluda, dice que es una IA y ofrece las gestiones | `conversacion.md` |
| `reparar` | Cuando no se entiende al cliente | `escalado.md` |
| `escalar` | Abre el caso con una persona | `escalado.md` |
| `ya_escalado` | El caso ya está abierto | `escalado.md` |
| `redactar` | Escribe el mensaje | `conversacion.md` |

## Identificar al cliente

- Antes de un pedido, una devolución o una cita, el cliente tiene que estar identificado.
- Se pide el email de la compra; si el cliente ya ha dado un número de pedido, se le dice que es para comprobar que el pedido es suyo.
- Si el email no existe, se le dice y se le pide de nuevo. Al tercer intento fallido, a una persona.
- Una vez identificado, sigue el flujo que pidió, sin volver a preguntar qué quería.

## Cuando algo falla

- Si una herramienta devuelve un error que no tiene tratamiento propio en su flujo, o lanza una excepción, el agente dice que no ha podido hacerlo ahora, no da la operación por hecha y ofrece pasar a una persona.
- Si falla la llamada al modelo al interpretar o al redactar, se responde con un mensaje fijo en el idioma del cliente («Ahora mismo no puedo responder, inténtalo en unos minutos») y el estado no cambia.

## Piezas fuera del grafo

- `agente/herramientas.py`: cliente MCP que arranca el servidor y expone `await llamar(nombre, **args)`. Los tests lo sustituyen por herramientas falsas con la misma firma.
- `agente/agente.py`: una clase con `responder(conversacion, texto, canal)` que devuelve el texto, las opciones y el estado. Todos los canales la usan.
- `--traza` en la consola: una línea por nodo con lo que cambia en el estado y, debajo, las llamadas a herramientas.
