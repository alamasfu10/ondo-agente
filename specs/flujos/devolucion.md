# Flujo · Devolver un producto

Empieza con el cliente ya identificado. Las reglas salen de `politicas.md`, «Devoluciones».

## Pasos

1. **Qué pedido.** Solo cuentan los entregados.
   - Si dio un número, se usa ese.
   - Con un solo pedido entregado, se usa ese.
   - Sin ninguno entregado: se le dice que no tiene pedidos que se puedan devolver y que un pedido que no ha llegado se puede rechazar en la entrega. Fin.
   - Con varios: se le pregunta cuál, con los entregados como opciones («OND-10233 · Ondo Ría»), como mucho cuatro y los más recientes primero; si el suyo no está, puede decir el número.
   - Si pide devolver solo una parte del pedido («el casco»), se le explica que se devuelve el pedido entero y se le pregunta si sigue adelante.
2. **Comprobaciones,** en este orden, con `estado_pedido`:
   1. No existe o no es suyo: se le dice que no está asociado a su cuenta, sin dar datos, y se le pide que lo revise.
   2. Ya tiene devolución (en `data/estado/` o, si está en estado devuelto, la de `pedidos.json`): se le dan sus datos. Fin.
   3. No está entregado: se explica que aún no se puede devolver y que puede rechazarlo en la entrega. Fin.
   4. Más de 30 días desde la entrega: **a una persona**, con el motivo «devolución fuera de plazo: han pasado N días».
   5. Total de más de 1.500 €: **a una persona**, con el motivo «devolución de N € (más de 1.500 €)».
3. **Motivo.** Se le dice cuántos días le quedan de plazo y se le pregunta el motivo, aclarando que no tiene que justificarse. Si el motivo habla de daños (golpe, roto, caída, rayado), **a una persona** con el motivo «devolución de un producto con daños».
4. **Confirmación.** Se resume: pedido, productos, importe que se reembolsa, recogida sin coste en la dirección de su ficha, caja original o equivalente y reembolso en un máximo de 14 días desde que el almacén lo revisa. Opciones: [Sí, solicita la devolución] [No, déjalo]. Si no hay un sí claro, no se crea y se cierra el flujo.
5. **Devolución.** `crear_devolucion`.
   - Si falla: a una persona, con el error como motivo. No se da por hecha.
   - Si va bien: se confirma con el código, la fecha de recogida y el plazo de reembolso, y se cierra el flujo.

## Reglas

- Plazo e importe se comprueban en código, con las constantes de `politicas.md`. El modelo no decide si una devolución procede.
- Las condiciones que se explican al cliente salen de la base de conocimiento o de la herramienta.

## Conversaciones de ejemplo

**Dentro de plazo (Javier, C002, OND-10233, hace 12 días):**
> Cliente: Quiero devolver la bici, me queda pequeña. javier.ortega@example.com
> Agente: Tu pedido OND-10233 está dentro de plazo: te quedan 18 días. ¿Por qué quieres devolverlo? No tienes que justificarte, es solo para mejorar.
> Cliente: Me queda pequeña
> Agente: Devolución del OND-10233, una Ondo Ría: se te reembolsan 990 €. Pasamos a recogerla sin coste; tiene que ir en su caja o en una equivalente, y el reembolso llega en un máximo de 14 días desde que el almacén la revisa. ¿La solicito? [Sí, solicita la devolución] [No, déjalo]
> Cliente: Sí, solicita la devolución
> Agente: Hecho: devolución DEV-0001. La recogemos el miércoles 3 de diciembre. ¿Algo más?

**Fuera de plazo (Marta, C003, OND-10234, hace 45 días):** el agente no pregunta el motivo ni crea nada: pasa a una persona con el motivo del plazo y la frase de traspaso.

**Importe alto (Pau, C004, OND-10235, 2959 €, hace 9 días):** a una persona por el importe.

**Ya devuelto (Iván, C010):** se le dan los datos de la devolución existente.
