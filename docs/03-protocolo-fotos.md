# Protocolo de fotografía

**Esta es la palanca más grande del sistema y no es código.** El 80% de la precisión de la
clasificación viene de que estas fotos existan y estén enfocadas. Una prenda fotografiada
según el protocolo sale con score 85+; una sin etiquetas legibles no pasa de 45 por bien
que funcione el software.

## Las 5 fotos por prenda, en este orden

| # | Foto | Para qué | ¿Obligatoria? |
|---|---|---|---|
| 1 | **Frontal completa**, extendida sobre fondo liso | Categoría, corte, color, patrón | Sí |
| 2 | **Etiqueta de marca** (cuello o interior), de cerca | Marca — el dato que más mueve el precio | **Sí** |
| 3 | **Etiqueta de talla y composición**, de cerca | Talla, material, país | **Sí** |
| 4 | Trasera completa | Estado, detalles, estampados traseros | Sí |
| 5 | Detalle: defecto, cremallera, botones, tejido | Condición, calidad percibida | Recomendada |

Si una prenda no tiene etiqueta, hazle igualmente la foto 2 del sitio donde debería estar.
El sistema distingue "no hay etiqueta" de "no me diste la foto", y son dos casos distintos.

## Las cuatro reglas que hacen que funcione la agrupación

1. **Siempre el mismo orden.** El sistema no lo exige, pero tú detectas antes los huecos.
2. **Sin pausas dentro de una prenda.** Las fotos de una misma prenda, seguidas. El
   agrupador usa los huecos temporales para separar prendas.
3. **Pausa clara entre prendas** — 10 segundos bastan: el tiempo de retirar una prenda y
   colocar la siguiente. Ese hueco natural es exactamente la señal que necesita.
4. **No edites ni reenvíes por WhatsApp.** Se pierden los metadatos EXIF y con ellos la
   agrupación. Sube el original desde la galería o la app de Drive.

Si prefieres no depender de los tiempos: crea una subcarpeta por prenda. El sistema la
respeta y se salta el clustering.

## Condiciones de luz

- Luz natural indirecta, o dos focos a 45°. Nada de flash directo: quema la etiqueta.
- Fondo liso y de contraste (blanco para prendas oscuras, gris para claras).
- **Etiquetas: acércate hasta que llene el encuadre y toca a enfocar.** Es el error más
  común: una etiqueta a 40 cm es ilegible aunque a ti te parezca nítida en el móvil.
- Prenda extendida y sin arrugas mayores. Colgada también vale; en el suelo arrugada, no.

## Lo que sigue siendo manual (y merece la pena)

**Mide con cinta y anota.** Ancho de pecho (de sisa a sisa) y largo total, en centímetros,
en la columna `medidas` del Sheet. 30 segundos por prenda. Las medidas no se estiman de una
foto de forma fiable, y la mayoría de devoluciones en Vinted son por talla — es el minuto
mejor pagado de todo el proceso.

## Autodiagnóstico

Si al procesar un lote ves muchas prendas con score bajo, mira el motivo antes de tocar el
prompt:

| Síntoma en el Sheet | Causa casi siempre |
|---|---|
| `marca_origen = inferido` en muchas filas | Foto 2 borrosa o lejana |
| `talla = null` frecuente | Foto 3 no la estás haciendo |
| `flag_agrupacion` activo | Pausas irregulares, o EXIF perdido al reenviar |
| `n_comparables = 0` | Marca desconocida o nicho — no es culpa de la foto |
