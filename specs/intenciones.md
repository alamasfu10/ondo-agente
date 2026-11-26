# Intenciones · qué entiende el agente de cada mensaje

## Lo que devuelve interpretar

Un objeto con estos campos y estos tipos, validado contra su esquema. El modelo lo rellena con salida estructurada; nunca se parsea texto libre.

| Campo | Tipo | Qué es |
|---|---|---|
| `intencion` | una de la lista de abajo | Qué quiere el cliente con este mensaje |
| `idioma` | código ISO 639-1 | Idioma del mensaje: `es`, `en`, `fr`, `it`, `pt` |
| `email` | texto o nulo | Email, si aparece |
| `pedido_id` | texto o nulo | Número de pedido con formato `OND-12345`, si aparece |
| `ciudad` | texto o nulo | Ciudad, si la menciona |
| `motivo` | texto o nulo | En una cita, «revisión» o «avería»; en una devolución, el motivo que da |
| `eleccion` | entero o nulo | Si elige una de las opciones ofrecidas, su número empezando en 1 («la segunda», «el jueves») |
| `confirma` | sí, no o nulo | Si acepta o rechaza lo que se le acaba de proponer |

Para interpretar bien, el modelo recibe los últimos mensajes y tres datos del estado: qué está esperando el agente, la intención en curso y las opciones que se acaban de mostrar.

## Intenciones

| Intención | Cuándo | Ejemplos |
|---|---|---|
| `pedido` | Dónde está o cómo va un pedido | «¿Dónde está mi pedido?», «No me ha llegado la bici» |
| `devolucion` | Quiere devolver algo | «Quiero devolver el casco», «La bici me queda pequeña» |
| `cita` | Cita en un taller, por revisión o avería | «Quiero pasar la revisión», «La bici no enciende» |
| `informacion` | Duda general sobre Ondo | «¿Cuánto dura la garantía de la batería?», «¿El envío es gratis?» |
| `seguridad` | Cualquier señal de peligro | «La batería huele un poco a quemado, ¿es normal?», «Los frenos no frenan» |
| `persona` | Pide hablar con una persona | «Quiero hablar con alguien», «Pásame con un humano» |
| `saludo` | Solo saluda o da las gracias | «Hola», «Gracias, eso era todo» |
| `continuar` | Responde a lo que el agente acaba de preguntar | «Sí», «La segunda», «Madrid», «lucia.martin@example.com» |
| `no_entendido` | No se puede saber qué necesita | «Ehh», «Lo de la cosa» |

## Casos frontera

- **Seguridad gana siempre.** Aunque el cliente lo cuente con calma, como una pregunta o en medio de otra gestión, es `seguridad`. Además del modelo, una lista de raíces en código fuerza `seguridad`, sin distinguir mayúsculas, para no depender solo del modelo: «quemad», «humo», «fuego», «se calienta», «muy caliente», «hinchad», «chispa», «los frenos no», «no frena», «sin frenos», «burning», «smoke», «brûl», «fumée», «bruciat», «fumo», «queimad».
- **`continuar` solo si hay algo pendiente.** Si el agente no está esperando nada, «¿Dónde está mi pedido?» es `pedido` aunque coincida con el texto de un botón.
- **Cambio de tema.** Si en mitad de una cita el cliente pregunta por un pedido, la intención nueva gana y el flujo en curso se abandona, conservando al cliente identificado.
- **Una avería sin señal de peligro** («hace un ruido raro») es `cita` o `informacion`, no `seguridad`.
- **«¿Eres una persona?»** es una pregunta: se contesta que es una IA y se ofrece una persona. No abre un caso por sí sola.
- **Motivo de la cita.** Se acepta solo si el texto del cliente dice claramente revisión o avería; si no, el flujo lo pregunta.
