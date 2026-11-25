# Flujo · Cita en el taller

Empieza con el cliente ya identificado. Cada paso pide un solo dato y anota en `pendiente` qué espera.

## Pasos

1. **Motivo:** revisión o avería. Si el mensaje ya lo dice claramente, no se pregunta. Opciones: [Revisión] [Avería].
2. **Ciudad:** se propone la del cliente. Opciones: [su ciudad] [Otra ciudad]. Si elige otra, la dice o la escribe.
3. **Huecos:** `huecos_taller` con la ciudad.
   - Sin taller: se le dice, se enumeran las ciudades con taller y se le ofrece elegir otra o que una persona organice la recogida.
   - Con taller: se le dice qué taller le corresponde (nombre y dirección) y se le ofrecen **tres huecos**, como «Martes 02/12 a las 10:00».
   - Si no quedan huecos en los próximos 14 días, o ya se le han ofrecido los 12 que devuelve la herramienta, se ofrece que una persona le busque fecha.
4. **Elección:** el cliente elige un hueco (botón, «la segunda», «el martes»).
   - Si dice que ninguno le va bien, se le ofrecen los tres siguientes.
   - Si no se entiende qué elige, se le repiten los huecos con la opción [Ninguna me va bien]. Al tercer intento sin entenderle, a una persona.
5. **Confirmación:** se resume la cita (taller, dirección, día, hora, motivo) y se pregunta si se reserva. Opciones: [Sí, resérvala] [No, ver otras fechas].
   - Sí claro: paso 6.
   - No: se le ofrecen los huecos siguientes.
   - Ambiguo («vale, bueno, no sé»): se le vuelve a preguntar de forma directa. **No se reserva.**
6. **Reserva:** `reservar_cita`.
   - Si el hueco se acaba de ocupar: se le dice y se le ofrecen otros. No se da la cita por hecha.
   - Si va bien: se confirma con todos los datos y el código, se recuerda que puede cambiarla o cancelarla sin coste hasta 24 horas antes y se cierra el flujo.

## Reglas

- Nunca se reserva sin un sí claro en el paso 5.
- Las fechas y horas salen de la herramienta; nunca se inventan.
- En voz, los huecos los dice el agente (como mucho tres) y repite fecha y hora antes de reservar.

## Conversaciones de ejemplo

**Revisión en Madrid (Hugo, C026):**
> Cliente: Quiero pedir cita para la revisión. hugo.serrano@example.com
> Agente: ¿La cita es en Madrid? [Madrid] [Otra ciudad]
> Cliente: Madrid
> Agente: Te corresponde Ondo Taller Madrid Centro, en la Calle del Prado 12. ¿Qué hueco prefieres? [Lunes 01/12 a las 10:00] [Lunes 01/12 a las 12:00] [Lunes 01/12 a las 17:00]
> Cliente: El primero
> Agente: Revisión el lunes 1 de diciembre a las 10:00 en Ondo Taller Madrid Centro, Calle del Prado 12. ¿Te la reservo? [Sí, resérvala] [No, ver otras fechas]
> Cliente: Sí, resérvala
> Agente: Hecho: cita CIT-0001, lunes 1 de diciembre a las 10:00. Puedes cambiarla o cancelarla sin coste hasta 24 horas antes. ¿Algo más?

**Cambia de idea al confirmar (Paula, C011):** elige el segundo hueco; al pedirle confirmación dice «mejor otro día»; el agente le ofrece los tres siguientes; elige uno y confirma. Se reserva una sola cita.

**Ciudad sin taller (Nerea, C009, Bilbao):** el agente dice que no hay taller en Bilbao, enumera las siete ciudades con taller y ofrece que una persona organice la recogida.

**Respuesta ambigua:**
> Agente: ¿Te reservo el martes a las 16:00? [Sí, resérvala] [No, ver otras fechas]
> Cliente: Bueno, no sé, puede ser
> Agente: Para no reservarte algo que no quieres: ¿te reservo el martes a las 16:00, sí o no?
