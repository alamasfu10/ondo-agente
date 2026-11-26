# Producto · qué es el agente de Ondo

## La empresa

Ondo es una tienda online ficticia de bicicletas eléctricas y accesorios. Vende en España, Francia, Italia y Portugal, y tiene talleres asociados en siete ciudades para revisiones, averías y garantía. El equipo de atención al cliente son personas que trabajan de lunes a viernes de 9:00 a 19:00, hora de Madrid.

## Qué hace el agente

Un asistente automático que atiende a los clientes por chat (consola y Telegram) y por voz (navegador), a cualquier hora, y resuelve lo sencillo:

1. **Dónde está mi pedido:** estado, fechas, transportista, seguimiento e incidencias (`flujos/pedido.md`).
2. **Devoluciones:** las que cumplen la política, de principio a fin; las demás, a una persona (`flujos/devolucion.md`).
3. **Cita en un taller asociado:** revisión o avería, con reserva confirmada (`flujos/cita.md`).
4. **Dudas generales:** garantía, envíos, pagos, cuidados de la batería, con la base de conocimiento (`flujos/informacion.md`).

Y pasa a una persona todo lo demás, con un resumen para que el cliente no repita nada (`escalado.md`).

## Qué no hace

- No resuelve casos de seguridad (batería que se calienta, huele a quemado o echa humo; frenos que fallan). Siempre los pasa a una persona, con prioridad.
- No vende, no cambia precios, no modifica pedidos ni direcciones y no hace llamadas salientes.
- No da datos de un pedido a quien no es su titular.
- No toma decisiones fuera de la política: una devolución fuera de plazo o de importe alto la decide una persona.
- Fuera del alcance de este proyecto: conservar o borrar conversaciones, grabar llamadas con consentimiento y evitar reservas simultáneas del mismo hueco. Guardar el estado en memoria basta.

## Cómo se mide

- Las conversaciones de `evaluacion.md` terminan como se espera: reserva hecha, devolución creada o caso pasado a una persona, con la prioridad correcta.
- El juez de la evaluación da «cumple» en sus criterios.
- Ninguna acción con efecto se ejecuta sin confirmación, y ningún dato se inventa.
