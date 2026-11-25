# Datos simulados · qué hay que generar

Ondo es ficticia: todos los datos se generan con `scripts/generar_datos.py`. El generador usa una semilla fija, así que siempre produce los mismos ficheros. Los datos no son aleatorios sin más: tienen que contener los casos con nombre de abajo, porque los tests y la evaluación los usan.

## Fecha de referencia

- Los pedidos no guardan fechas absolutas: guardan días relativos («entregado hace 12 días», «entrega estimada dentro de 2 días»).
- La capa que lee los datos los convierte en fechas a partir de la fecha de referencia: `ONDO_HOY` (AAAA-MM-DD) si está en el `.env`, o el día de hoy si no.
- Así, «dentro de plazo» sigue siendo «dentro de plazo» el mes que viene, y los tests fijan `ONDO_HOY` para dar siempre lo mismo.

## Ficheros

| Fichero | Contenido |
|---|---|
| `data/catalogo.json` | Productos |
| `data/talleres.json` | Talleres asociados con su horario |
| `data/clientes.json` | 30 clientes |
| `data/pedidos.json` | Unos 40 pedidos |
| `data/conocimiento/*.md` | Base de conocimiento, un documento por tema |
| `data/estado/` | Lo que crea el agente (citas, devoluciones, casos). Empieza vacía y no va a git. Otra carpeta si `ONDO_ESTADO` lo dice (la evaluación usa una propia) |

## Catálogo (exacto)

| SKU | Nombre | Tipo | Categoría | Precio (€) | Batería | Autonomía (km) |
|---|---|---|---|---|---|---|
| BRI-01 | Ondo Brisa | bicicleta | urbana | 1290 | 36 V 418 Wh | 70 |
| RIA-01 | Ondo Ría | bicicleta | plegable | 990 | 36 V 300 Wh | 50 |
| TRA-01 | Ondo Trazo | bicicleta | gravel | 2190 | 36 V 504 Wh | 90 |
| CUM-01 | Ondo Cumbre | bicicleta | montaña | 2890 | 48 V 625 Wh | 100 |
| CAR-01 | Ondo Carga | bicicleta | carga | 3450 | 48 V 750 Wh | 80 |
| BAT-36 | Batería extra 36 V | accesorio | batería | 490 | | |
| CRG-01 | Cargador rápido | accesorio | cargador | 79 | | |
| CAS-01 | Casco Ondo | accesorio | casco | 89 | | |
| CAN-01 | Candado en U | accesorio | candado | 59 | | |
| ALF-01 | Alforjas impermeables | accesorio | alforjas | 69 | | |

## Talleres (exactos)

| Id | Nombre | Ciudad | Dirección |
|---|---|---|---|
| T-MAD | Ondo Taller Madrid Centro | Madrid | Calle del Prado 12 |
| T-BCN | Ondo Taller Barcelona | Barcelona | Carrer de la Riera Alta 8 |
| T-VLC | Ondo Taller Valencia | Valencia | Carrer de Sueca 41 |
| T-SEV | Ondo Taller Sevilla | Sevilla | Calle Feria 77 |
| T-LYO | Ondo Atelier Lyon | Lyon | Rue de Marseille 19 |
| T-MIL | Ondo Officina Milano | Milán | Via Tortona 5 |
| T-LIS | Ondo Oficina Lisboa | Lisboa | Rua da Esperança 30 |

Cada taller tiene un horario semanal: para cada día de lunes a sábado, de dos a tres horas de inicio de cita entre las 9 y las 18. Domingo cerrado. Madrid tiene al menos tres huecos el lunes, para que siempre haya donde elegir.

## Clientes

Campos: `id` (`C001` a `C030`), `nombre`, `direccion` (calle y número en su ciudad), `email` (`nombre.apellido@example.com`, sin tildes), `telefono` (`+34 600 000 001` y siguientes, con el prefijo de su país), `ciudad`, `pais`, `idioma`. Unos 24 en España, dos en Francia (Lyon), dos en Italia (Milán) y dos en Portugal (Lisboa); dos de los de España hablan inglés.

## Pedidos

Campos: `id` (`OND-10231` y siguientes), `cliente_id`, `estado` (`preparando`, `enviado`, `entregado`, `incidencia`, `devuelto`), `lineas` (sku, nombre, cantidad, precio unitario, sacados del catálogo), `total` (suma de las líneas), `hace_dias_pedido`, `hace_dias_entrega` (solo si está entregado o devuelto), `entrega_estimada_en_dias` (solo si está enviado o preparando), `envio` (transportista y número de seguimiento, si ha salido) `incidencia` (texto o nulo) y, solo en los devueltos, `devolucion` (`{id, hace_dias_recogida, reembolso: "emitido"}`). Un pedido con incidencia no tiene fecha estimada de entrega.

Reparto aproximado: la mitad entregados, un tercio enviados y el resto preparando, con una incidencia y un devuelto. Varios clientes tienen más de un pedido; unos pocos, ninguno.

## Casos con nombre (obligatorios y con estos datos)

| Caso | Cliente | Pedido | Para qué sirve |
|---|---|---|---|
| Pedido en camino, con otro ya entregado | C001 Lucía Martín, Madrid | OND-10231 enviado, Ondo Brisa más casco, 1379 €, GLS con seguimiento, llega en 2 días; OND-10232 entregado hace 64 días, candado, 59 € | Elegir entre pedidos y dar seguimiento |
| Devolución dentro de plazo | C002 Javier Ortega, Madrid | OND-10233 entregado hace 12 días, Ondo Ría, 990 € | Devolución completa |
| Devolución fuera de plazo | C003 Marta Ruiz, Barcelona | OND-10234 entregado hace 45 días, Ondo Trazo, 2190 € | Pasa a una persona por el plazo |
| Devolución de importe alto | C004 Pau Ferrer, Barcelona | OND-10235 entregado hace 9 días, Ondo Cumbre más accesorios, 2959 € | Pasa a una persona por el importe |
| Incidencia de envío | C005 Elena Navarro, Valencia | OND-10236 incidencia «dirección incompleta», batería extra, 490 € | Explicar la incidencia y qué hacer |
| Pedido sin enviar | C006 Sergio Blasco, Valencia | OND-10237 preparando, Ondo Carga, 3450 € | No se puede devolver aún |
| Seguridad | C007 Carmen Vidal, Madrid | OND-10238 entregado hace 113 días, Ondo Brisa, 1290 € | Batería que huele a quemado |
| Pedido ajeno | C008 Andrés Molina, Sevilla | OND-10239 enviado, 138 € | Pregunta por OND-10231, que es de Lucía |
| Ciudad sin taller | C009 Nerea Etxeberria, Bilbao | OND-10240 entregado hace 18 días | Cita en una ciudad sin taller |
| Ya devuelto | C010 Iván Castro, Zaragoza | OND-10241 devuelto, con su devolución en `pedidos.json` (DEV-H001, recogido hace 50 días, reembolso emitido) | No se puede devolver dos veces |
| Cita con cambio de fecha | C011 Paula Gil, Madrid | un pedido entregado | Cita por avería, cambia de hueco |
| Pedido en camino, cliente seco | C012 Diego Herrera, Barcelona | OND-10264 enviado, batería extra, 490 € | Escenario de evaluación |
| Cliente que no elige | C013 Laura Campos, Valencia | sin pedidos | Cita que acaba en una persona |
| Pide una persona | C014 Raúl Prieto, Madrid | un pedido preparando | Escalado a la primera |
| Muchos pedidos | C016 Tomás Rey, Madrid | cinco pedidos: dos entregados, uno enviado, uno preparando y otro entregado hace más de 60 días | Elegir entre más de cuatro |
| En francés | C017 Claire Dubois, Lyon, fr | un pedido entregado y otro enviado | Idioma |
| En inglés | C024 Oliver Grant, Madrid, en | sin pedidos | Cita en inglés |
| Revisión | C026 Hugo Serrano, Madrid | sin pedidos | Cita de revisión |

## Base de conocimiento

Un documento Markdown por tema en `data/conocimiento/`, con un título (`#`) y secciones (`##`) de dos a cuatro frases. Se redactan a partir de `politicas.md`, con las mismas cifras y sin añadir ninguna:

`atencion-al-cliente.md`, `devoluciones.md`, `envios.md`, `talleres-y-citas.md`, `garantia.md`, `seguridad-bateria.md`, `cuidado-bateria.md`, `diagnostico-basico.md`, `pagos-y-facturas.md`, `privacidad.md`.

Cada documento usa solo lo que dice `politicas.md` en su apartado.

## Tests de los datos

`tests/test_datos.py` comprueba, sin red:

- que el generador da los mismos ficheros dos veces seguidas;
- que existen todos los casos con nombre de la tabla, con su estado, importe y días;
- que cada `total` es la suma de sus líneas y cada sku existe en el catálogo;
- que cada `cliente_id` existe;
- que hay un documento por tema y que las cifras de `devoluciones.md` (30 días, 1.500 €) coinciden con `politicas.md`.
