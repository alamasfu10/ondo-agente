# Canales · por dónde habla el cliente con el agente

Los tres canales usan la misma clase `agente.responder(conversacion, texto, canal)`. El flujo del agente no cambia por el canal: solo cambia cómo se redacta (`conversacion.md`) y cómo se muestran las opciones.

## Consola (paso 3 en adelante)

- `python -m canales.consola`: conversación en la terminal. Las opciones se muestran numeradas y el cliente puede escribir el número o el texto.
- `--traza`: después de cada turno, una línea por nodo con lo que cambia en el estado y, debajo, las herramientas llamadas con sus argumentos.
- `--estado`: el estado completo al final de cada turno.
- `/nueva`: empieza una conversación nueva.

## Telegram (paso 10)

- `python -m canales.telegram_bot`, con `python-telegram-bot` en modo polling: sin URL pública ni ngrok.
- Una conversación por chat (`thread_id` = id del chat).
- Las opciones van como botones de respuesta (teclado), y al pulsarlos llega su texto.
- Muestra «escribiendo…» mientras el agente piensa; si eso falla, la respuesta se envía igual.
- Ignora los mensajes editados.
- `/start` saluda y `/nueva` empieza de cero.

## Voz en el navegador (paso 11)

- `python -m canales.voz` abre una página en `http://localhost:7860` con el cliente de WebRTC de Pipecat (`SmallWebRTCTransport`).
- Tubería en cascada: transporte → reconocimiento de voz (STT de OpenAI) → agregador del turno del usuario con detector de voz (Silero) → el agente de Ondo como procesador que recibe el contexto y devuelve el texto → síntesis de voz (TTS de OpenAI) → transporte → agregador del turno del asistente.
- El agente se llama con `canal="voz"`.
- Si el agente tarda más de un segundo (consulta herramientas), dice una frase de espera corta, elegida al azar entre varias y sin repetir la anterior.
- Si el cliente interrumpe, se descarta lo que se iba a decir, no lo que ya se ha hecho: si la reserva o la devolución se completó, el estado lo sabe y el siguiente turno la confirma.
- Una conversación por conexión.
