# Herramientas · el servidor MCP de Ondo

Un servidor MCP propio (`ondo_mcp/server.py`, con `FastMCP`) expone ocho herramientas sobre los datos de `data/`. El agente lo arranca como subproceso y le habla por stdio. Las herramientas no conversan ni deciden la política: devuelven datos o hacen una operación y dicen si ha ido bien.

Todas devuelven un diccionario. Un error nunca es una excepción: es `{"ok": false, "error": "…"}` o `{"error": "…"}`, con un texto que se pueda explicar al cliente.

## buscar_cliente(email=None, pedido_id=None, telefono=None)

Identifica al cliente por email (sin distinguir mayúsculas), por número de pedido o por teléfono (comparando los últimos nueve dígitos).

- Encontrado: `{"encontrado": true, "cliente": {id, nombre, email, ciudad, direccion, pais, idioma}, "pedidos": [{id, estado, fecha_pedido, productos}]}`. Nunca devuelve el teléfono.
- No encontrado: `{"encontrado": false}`.

## estado_pedido(pedido_id)

- Devuelve el pedido completo con fechas reales (calculadas con la fecha de referencia), `cliente_id`, transportista, seguimiento e incidencia, y la devolución si la tiene.
- No existe: `{"error": "No existe ningún pedido OND-…"}`.
- No comprueba el titular: lo comprueba el agente con `cliente_id`.

## crear_devolucion(pedido_id, cliente_id, motivo)

- Comprueba que el pedido existe, es de ese cliente, está entregado y no tiene ya una devolución. Si no, `{"ok": false, "error": …}`.
- No comprueba plazo ni importe: eso lo decide el agente antes de llamarla.
- Crea `{id: "DEV-0001"…, pedido_id, cliente_id, motivo, importe, recogida, creada}`, con la recogida dos días después de la fecha de referencia (si cae en fin de semana, el lunes siguiente). Devuelve `{"ok": true, "devolucion": …}`.

## huecos_taller(ciudad, dias=14)

- Sin taller en esa ciudad: `{"encontrado": false, "ciudades_con_taller": [...]}`.
- Con taller: `{"encontrado": true, "taller": {id, nombre, ciudad, direccion}, "huecos": [...], "total_huecos": n}`, con como mucho 12 huecos y empezando mañana. Cada hueco: `{hueco_id: "T-MAD-2026-12-01-10", fecha, dia, hora}`. Los huecos ya reservados no aparecen.

## reservar_cita(cliente_id, hueco_id, motivo)

- Comprueba que el cliente existe y que el hueco es válido y sigue libre. Si no, `{"ok": false, "error": "Ese hueco ya no está libre…"}`.
- Crea `{id: "CIT-0001"…, cliente_id, hueco_id, taller, direccion, fecha, hora, motivo, creada}` y devuelve `{"ok": true, "cita": …}`.

## escalar_a_humano(motivo, resumen, prioridad="normal", cliente_id=None, canal="chat")

- Crea un caso `{id: "CASO-0001"…, cliente_id, motivo, resumen, prioridad ("normal" o "urgente"), canal, creado}`.
- Devuelve `{"ok": true, "caso": …, "espera": "…", "en_horario": …}`. El texto de espera es el de `politicas.md`, «Cuándo atiende una persona», según la prioridad y la hora.
- La hora es la de Madrid. Para los tests, `ONDO_AHORA` (AAAA-MM-DDTHH:MM) fija el momento; si no está, la hora real.

## anotar_caso(caso_id, nota)

- Añade una nota a un caso abierto (lo que el cliente cuenta después de pasar a una persona). Devuelve `{"ok": true}` o un error si el caso no existe.

## buscar_conocimiento(pregunta)

RAG sencillo sobre `data/conocimiento/`:

- Un fragmento por sección (`##`), con documento y sección como metadatos.
- Embeddings `text-embedding-3-small` de OpenAI y un almacén vectorial en memoria, guardados en `data/.cache/` para no pagarlos en cada arranque.
- La caché se regenera cuando cambia algún documento (huella de su contenido) o el modelo de embeddings.
- Devuelve hasta 3 fragmentos con similitud coseno de al menos 0,35 (`RAG_UMBRAL`): `{"resultados": [{documento, seccion, texto}]}`. Si ninguno lo supera, `{"resultados": [], "mensaje": "sin resultados"}`.
- Los datos de pedidos, huecos y clientes nunca se buscan aquí: tienen sus herramientas.

## Tests

`tests/test_herramientas.py` llama a las funciones directamente, con `ONDO_HOY` fijo y una carpeta de estado temporal, y prueba cada error. `buscar_conocimiento` se prueba sin red, con embeddings falsos.
