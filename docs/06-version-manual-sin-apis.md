# Versión manual: sin Serper, sin API de pago, con tu ChatGPT

> Este documento sustituye a la vía de `docs/05-puesta-en-marcha.md` (n8n + Claude API +
> Serper) como camino recomendado. El workflow de n8n queda **aparcado, no borrado**: si
> más adelante quieres volver a la automatización completa, sigue ahí.

## Por qué el cambio

Tres objeciones tuyas, todas legítimas:

1. **Serper tiene límite.** Es una cuota mensual de peticiones; a partir de cierto
   volumen hay que pagar más o se corta.
2. **No quieres gastar tokens.** Cada llamada a la API de Claude (o de OpenAI) se
   factura por uso. Aunque el análisis inicial mostraba que salía barato (~0,08 €
   por prenda), sigue siendo un gasto variable nuevo.
3. **Ya pagas ChatGPT y no tiene ese problema.** Un GPT personalizado con navegación
   web activada busca comparables igual que hacía Serper, y usarlo no añade coste: va
   incluido en la suscripción que ya tienes, uses lo que uses dentro de los límites
   normales de la app.

La consecuencia directa es que el paso de "mirar las fotos, buscar en internet y decidir
título/marca/precio" deja de ser una llamada automática dentro de un workflow y pasa a
ser algo que haces tú, a mano, en la interfaz de ChatGPT — una vez por prenda. Se pierde
automatización total; se gana coste marginal cero.

## Qué se mantiene del análisis original y qué cambia

| Decisión | Antes (n8n + Claude + Serper) | Ahora (local + ChatGPT) |
|---|---|---|
| Agrupar fotos en prendas por EXIF | Sí, en un nodo Code de n8n contra la API de Drive | Sí, igual de importante — ahora en `agrupar_fotos.py`, local |
| Distinguir dato leído vs. inferido (`marca_origen`, `talla_origen`) | Sí, en el prompt de Claude | Sí, igual — en el prompt del GPT personalizado |
| El precio se fundamenta en comparables reales, no en el prior del modelo | Sí, vía Serper | Sí — ahora la búsqueda la hace el propio GPT navegando, y te dice cuántos comparables encontró |
| El score se calcula, no se pregunta | Sí, en un nodo Code | Sí, igual — en `parsear_respuestas.py`, con la misma fórmula |
| Automatización de extremo a extremo (subes fotos, sale el Sheet solo) | Sí | **No.** Cada prenda pasa por un paso manual: pegar fotos en el GPT, copiar su respuesta |
| Coste variable por prenda | ~0,08 € (Claude) + cuota de Serper | 0 € — todo dentro de tu suscripción de ChatGPT y de Python local |
| Reintentos automáticos si algo falla | Sí (n8n) | No — si un bloque sale mal formado, el script lo avisa y lo omite; lo repites tú a mano |

La pieza que **no** cambia es la más importante: agrupar mal las fotos, no distinguir
marca leída de marca inventada, o preguntarle al modelo su propia confianza en vez de
calcularla, seguían siendo los tres motivos reales por los que un sistema de este tipo
falla. Cambiar de proveedor de LLM no resuelve ni empeora ninguno de los tres, así que
esas tres decisiones se trasladan tal cual.

## Arquitectura

```
Carpeta local de fotos del lote
        │
        ▼
agrupar_fotos.py   (Python local, gratis, sin red)
  · lee EXIF, agrupa por hueco temporal adaptativo
  · copia cada grupo a salida/prenda-NNN/
  · escribe salida/manifiesto.csv
        │
        ▼  (por cada prenda-NNN, a mano)
GPT personalizado "Tasador Vinted" en ChatGPT
  · arrastras las fotos de esa carpeta al chat
  · escribes "ID: prenda-NNN"
  · el GPT navega por internet, busca comparables, responde en un
    bloque de texto de formato fijo
  · copias y pegas ese bloque al final de salida/respuestas.txt
        │
        ▼  (cuando ya pegaste todas las prendas del lote)
parsear_respuestas.py   (Python local, gratis, sin red)
  · separa respuestas.txt en bloques por prenda
  · cruza con manifiesto.csv
  · calcula precio y score con formulas fijas (no se lo pregunta al GPT)
  · escribe salida/prendas.csv
        │
        ▼
Abres prendas.csv en Excel / Numbers / lo importas a Google Sheets
```

## Uso paso a paso

### 1. Instalar dependencias (una vez)

```bash
cd local
pip install -r requirements.txt
```

Si fotografías con iPhone, instala también `pillow-heif` (ya está en el
`requirements.txt`): sin él, el script sigue funcionando pero avisa de que no puede
leer la fecha de disparo de tus `.heic` y usa una fecha de respaldo menos fiable.

### 2. Crear el GPT personalizado (una vez)

Sigue `local/plantilla_gpt.md`: crear un GPT en ChatGPT llamado "Tasador Vinted", con
navegación web activada, y pegarle las instrucciones que trae el documento. Cinco
minutos, y no hace falta repetirlo nunca más.

### 3. Por cada lote de fotos

```bash
python3 agrupar_fotos.py ~/fotos/lote-2026-09-05
```

Esto crea `~/fotos/lote-2026-09-05-prendas/` con una subcarpeta `prenda-001/`,
`prenda-002/`... y un `manifiesto.csv`. Antes de seguir, revisa el aviso en pantalla:
si dice que alguna prenda tiene un número de fotos sospechoso (menos de 3 o más de 8),
ábrela y comprueba a ojo que de verdad es una sola prenda.

### 4. Por cada prenda del lote (esto es lo manual)

1. Abre el GPT "Tasador Vinted", **en un chat nuevo**.
2. Arrastra las fotos de `prenda-001/` al chat.
3. Escribe `ID: prenda-001`.
4. Copia la respuesta completa y pégala al final de
   `~/fotos/lote-2026-09-05-prendas/respuestas.txt` (créalo la primera vez).
5. Repite para `prenda-002`, `prenda-003`... siempre en un chat nuevo, para que el
   histórico de una prenda no contamine la siguiente.

Con práctica, esto son unos 30-45 segundos por prenda.

### 5. Cerrar el lote

```bash
python3 parsear_respuestas.py ~/fotos/lote-2026-09-05-prendas
```

Esto escribe `prendas.csv` en esa misma carpeta y te imprime un resumen: cuántas
prendas puedes publicar sin revisar (score ≥85), cuántas conviene revisar (50-84),
cuántas hay que refotografiar o repasar a mano (<50), y el valor estimado del lote.

## Limitaciones honestas de esta vía frente a la automática

- **Es manual, prenda a prenda.** A 50-300 prendas/mes son 50-300 idas y vueltas a
  ChatGPT. La vía de n8n lo hacía sin que tocaras nada; esta te ahorra dinero a cambio
  de tu tiempo.
- **Sin reintentos automáticos.** Si el GPT responde mal formado o tú pegas mal el
  bloque, `parsear_respuestas.py` avisa y omite esa prenda — la repites tú.
- **La calidad del GPT depende de que sigas el formato al pie de la letra.** Si el
  modelo decide explicar algo fuera del bloque, o lo envuelve en markdown, el parseo
  puede fallar en esa prenda. El prompt se lo prohíbe explícitamente, pero no hay
  garantía dura como con `output_config.format` de la API.
- **No hay medición sistemática de calidad (golden set).** La vía API permitía montar
  un segundo workflow de evaluación fácilmente; aquí montar ese bucle es más manual
  todavía. Si te importa medir precisión de forma rigurosa con el tiempo, esa pieza
  seguiría faltando.
- **Sin aviso automático por Telegram al terminar un lote.** El resumen sale por
  terminal al ejecutar `parsear_respuestas.py`, no llega a tu móvil solo.

Ninguna de estas es un defecto de diseño: son el precio de haber elegido "gratis y
manual" sobre "automático y con coste variable". Es una decisión razonable para un
volumen de 50-300 prendas/mes gestionado por una sola persona.

## Si más adelante quieres volver a la vía automática

El workflow de n8n (`n8n/clasificar-lote.sdk.ts`, ya creado como
`Vinted · Clasificar lote de prendas` en tu instancia, sin publicar) sigue ahí. El
único cambio real sería sustituir el nodo de Claude por uno que llame al modelo que
prefieras, y el de Serper por otra fuente de comparables si la cuota se queda corta.
Nada de lo demás (agrupación por EXIF, score determinista, precio en tres niveles)
tendría que rehacerse: es la misma lógica, ya trasladada aquí a Python.
