# Estado · lo que el agente recuerda entre turnos

El estado es explícito: además de los mensajes, guarda quién es el cliente, qué quiere, qué datos tenemos y qué dato estamos esperando. Un checkpointer de LangGraph lo conserva entre turnos, con una conversación (`thread_id`) por chat de Telegram, por sesión de consola o por llamada de voz.

| Campo | Qué guarda |
|---|---|
| `messages` | Historial de mensajes (se van añadiendo) |
| `canal` | `chat` o `voz`. Lo fija el canal en cada turno y decide cómo se redacta |
| `idioma` | Idioma del último mensaje del cliente |
| `intencion` | Intención en curso (`pedido`, `cita`…), o nada |
| `cliente` | Cliente identificado: id, nombre, email, ciudad, idioma y la lista resumida de sus pedidos |
| `datos` | Datos recogidos en la gestión en curso: email, pedido, ciudad, motivo, motivo de escalado… |
| `pendiente` | Qué dato está esperando el agente (`email`, `motivo`, `ciudad`, `hueco`, `confirmar_cita`…), o nada |
| `opciones` | Opciones mostradas en el último mensaje |
| `huecos` | Huecos de taller ofrecidos |
| `hueco_elegido` | Hueco que el cliente eligió, a la espera de confirmar |
| `intentos_fallidos` | Mensajes seguidos sin entender al cliente |
| `escalado` | Caso abierto con una persona, si lo hay |
| `ultima` | La interpretación del último mensaje |
| `borrador` | Qué hay que decir en este turno (lo redacta el último nodo) |

## Reglas

- Al terminar una gestión, se vacían intención, pendiente, datos, huecos e intentos, y se conserva el cliente.
- Un dato que el cliente da antes de que se le pida (el email en el primer mensaje) se guarda y no se vuelve a pedir.
- Lo que crea el agente fuera de la conversación (citas, devoluciones, casos) no va en el estado: lo guardan las herramientas.
