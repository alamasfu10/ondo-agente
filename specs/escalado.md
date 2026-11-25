# Escalado · cuándo y cómo pasa el agente a una persona

## Cuándo

| Disparador | Prioridad | Motivo que se guarda |
|---|---|---|
| Seguridad, siempre y a la primera | urgente | «seguridad» |
| El cliente pide una persona, a la primera y sin intentar retenerle | normal | «el cliente pide hablar con una persona» |
| Tercer mensaje seguido sin entender al cliente | normal | «el asistente no consigue resolver la consulta» |
| Una regla de un flujo: devolución fuera de plazo, de más de 1.500 € o de un producto con daños; ciudad sin taller si el cliente lo pide; herramienta que falla | normal | el motivo concreto del flujo |

## Reparar antes de escalar

Cuando no se entiende al cliente y no hay un flujo esperando un dato:

1. Primer intento: se le dice que no se le ha entendido y se le recuerda en qué puede ayudar, con las cuatro opciones (pedido, devolución, cita, hablar con una persona).
2. Segundo intento: se le pide que elija una de las opciones; si ninguna encaja, que elija hablar con una persona.
3. Tercer intento: se pasa a una persona.

En voz no hay botones: el menú se dice en una frase («puedo ayudarte con un pedido, una devolución, una cita o pasarte con una persona») y nunca se pide «pulsar» (`conversacion.md`).

## Cómo

1. Un resumen de 3 a 5 líneas para la persona, escrito por el modelo con el historial: qué necesita el cliente, datos ya recogidos (cliente, pedido, ciudad), qué se ha intentado y su estado de ánimo. Siempre en español.
2. `escalar_a_humano` con el motivo, el resumen, la prioridad, el cliente si está identificado y el **canal real** (`chat` o `voz`).
3. La frase de traspaso lleva cuatro cosas: por qué pasa, que no tendrá que repetir nada, cuándo le atenderán (el texto de espera de la herramienta) y por dónde. En chat incluye el número de caso; en voz no lo dice salvo que lo pida: «te llamarán al teléfono de tu ficha».
4. Seguridad, además: antes de lo anterior, las instrucciones inmediatas de `politicas.md` (dejar de usarla, no cargar, desconectar, fuera de casa si es seguro, 112 si hay humo o fuego).
5. Si no hay cliente identificado, después de la frase de traspaso se le pide un teléfono o el email de la compra para que puedan contactarle, y se guarda en el caso con `anotar_caso`. Si no lo da, se le dice que puede volver a escribir o llamar cuando quiera.

## Después del traspaso

Mientras el caso está abierto, el agente ya no resuelve: `ya_escalado` en cada turno, hasta que la conversación termina (en la consola y en Telegram, `/nueva` empieza otra).

- Si el cliente pregunta cuánto tardarán, se repite el texto de espera.
- Si añade información, se guarda en el caso con `anotar_caso` y se le confirma. Nunca se promete «se lo haré llegar» sin hacerlo.
- Si vuelve a dar una señal de peligro, se repiten las instrucciones de seguridad, sin abrir otro caso.
- En voz nunca se le pide que escriba.

## Conversaciones de ejemplo

**Pide una persona (chat):**
> Cliente: Quiero hablar con una persona.
> Agente: Claro, te paso con una persona del equipo. No tendrás que repetir nada: te atenderán en los próximos minutos. Tu número de caso es CASO-0001.

**Seguridad contada con calma (voz):**
> Cliente: Oye, ¿es normal que la batería huela un poco a quemado al cargarla?
> Agente: Eso no es normal y es importante: deja de cargarla ahora y desconecta el cargador. Si ves humo, aléjate y llama al uno uno dos. Una persona de Ondo te llamará por teléfono con prioridad.
> Cliente: ¿Y ahora qué hago?
> Agente: No la uses ni la cargues, y si puedes sin riesgo, déjala fuera de casa. La persona de postventa ya tiene tu caso y te llamará con prioridad.

(En el segundo turno no se abre otro caso.)

**Añade algo después (voz):**
> Cliente: Una cosa más, es por el pedido que no me llega.
> Agente: Apuntado en tu caso, se lo dirán a la persona que te llame. ¿Algo más?
