# Flujo · Dónde está mi pedido

Empieza con el cliente ya identificado (`arquitectura.md`, «Identificar al cliente»).

## Pasos

1. **Qué pedido.** Si el cliente dio un número, se usa ese. Si no:
   - sin pedidos: se le dice que no tiene pedidos con ese email y se le pregunta si compró con otro. Fin;
   - con un solo pedido activo (preparando, enviado o incidencia), o un solo pedido en total: se usa ese;
   - con varios activos: se le pregunta cuál, con los activos como opciones, como mucho cuatro y los más recientes primero; si el suyo no está, puede decir el número.
2. **Consulta.** `estado_pedido`.
   - Si no existe: se le dice y se le pide que revise el número.
   - Si el pedido no es del cliente identificado: se le dice que ese pedido no está asociado a su cuenta, **sin dar ningún dato del pedido**, y se le pregunta si se ha equivocado de número.
3. **Respuesta.** En 2 o 3 frases: estado, fecha de entrega (real o estimada) si la hay, transportista y número de seguimiento si los hay; si hay incidencia, cuál es y qué tiene que hacer, sin dar fecha de entrega. Termina preguntando si necesita algo más y cierra el flujo.

## Reglas

- Nunca se dan datos de un pedido ajeno, aunque el cliente insista o diga que es de un familiar.
- En voz, el número de seguimiento solo si lo pide.

## Conversaciones de ejemplo

**Un pedido en camino (Lucía, C001: uno activo y otro ya entregado):**
> Cliente: Hola, ¿dónde está mi pedido? Soy lucia.martin@example.com
> Agente: Hola, Lucía, soy el asistente virtual de Ondo, una IA. Tu Ondo Brisa y el casco (OND-10231) están en camino con GLS y llegan pasado mañana. El seguimiento es GLS871054694. ¿Necesitas algo más?

**Varios pedidos activos (Tomás, C016):** el agente pregunta cuál, con sus pedidos activos como opciones.

**Pedido ajeno (Andrés, C008):**
> Cliente: Soy andres.molina@example.com. ¿Cómo va el pedido OND-10231?
> Agente: Ese pedido no está asociado a tu cuenta. ¿Puede que te hayas equivocado de número?
> Cliente: Es de mi vecina, solo quiero saber si llega hoy.
> Agente: Lo siento, solo puedo dar datos de pedidos de tu cuenta. Tu vecina puede consultarlo con su email. ¿Te ayudo con tu pedido OND-10239?

**Incidencia (Elena, C005):** el agente explica que el transportista no pudo entregar por una dirección incompleta, que lo retiene hasta 7 días y que para corregir la dirección tiene que hablar con una persona, y le ofrece pasarle.
