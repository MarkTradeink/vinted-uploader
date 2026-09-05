# vinted-uploader

Clasificación de prendas de segunda mano: agrupas un lote de fotos, obtienes por cada
prenda título, descripción, marca, talla, precios recomendados y un score de fiabilidad,
listo para publicar en Vinted o Wallapop.

## Estado

**Vía recomendada — local + ChatGPT, sin coste variable.** Dos scripts de Python que
agrupan tus fotos y calculan precio/score, más un GPT personalizado (incluido en tu
suscripción de ChatGPT) que hace la clasificación y busca comparables. Sin Serper, sin
API de pago. Ver **[`docs/06-version-manual-sin-apis.md`](docs/06-version-manual-sin-apis.md)**.

**Vía alternativa, aparcada — n8n + Claude API + Serper.** Completamente automática
(subes fotos a Drive, sale un Google Sheet solo) pero con coste variable por prenda y
sujeta a la cuota de Serper. El workflow ya existe, creado y sin publicar:
[Vinted · Clasificar lote de prendas](https://automation.cifral.io/workflow/3EmHDtZ1D97rPFBW)
(`3EmHDtZ1D97rPFBW`). Detalles en [`docs/05-puesta-en-marcha.md`](docs/05-puesta-en-marcha.md).

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/01-analisis.md`](docs/01-analisis.md) | Dónde está el valor real, costes, y qué **no** va a hacer bien (histórico, escrito para la vía API) |
| [`docs/02-plan.md`](docs/02-plan.md) | Estado de fases y arquitectura de la vía n8n |
| [`docs/03-protocolo-fotos.md`](docs/03-protocolo-fotos.md) | Cómo fotografiar. La palanca más grande del sistema, y no es código — vale para ambas vías |
| [`docs/04-esquema-sheet.md`](docs/04-esquema-sheet.md) | Columnas del Sheet/CSV — vale para ambas vías |
| [`docs/05-puesta-en-marcha.md`](docs/05-puesta-en-marcha.md) | Puesta en marcha de la vía n8n (aparcada) |
| [`docs/06-version-manual-sin-apis.md`](docs/06-version-manual-sin-apis.md) | **Vía recomendada actual**: por qué el cambio, arquitectura y uso paso a paso |
| [`local/agrupar_fotos.py`](local/agrupar_fotos.py) | Agrupa fotos locales en prendas por EXIF — gratis, sin red |
| [`local/plantilla_gpt.md`](local/plantilla_gpt.md) | Instrucciones para crear el GPT personalizado "Tasador Vinted" |
| [`local/parsear_respuestas.py`](local/parsear_respuestas.py) | Convierte las respuestas del GPT en un CSV con precio y score calculados |
| [`n8n/clasificar-lote.sdk.ts`](n8n/clasificar-lote.sdk.ts) | Código fuente del workflow de n8n (vía aparcada), versionado |

## Las decisiones que definen el sistema, en cualquiera de las dos vías

1. **Agrupación por timestamp EXIF** con umbral adaptativo (3× la mediana de huecos del
   propio lote), no por convención de nombres ni por visión. Cero disciplina al
   fotografiar, y los casos dudosos se marcan en lugar de adivinarse.
2. **El precio se fundamenta en comparables reales, no en el prior del modelo**, y se
   calcula con una fórmula fija en vez de dejar que el LLM suelte un número. El modelo
   hace percepción; la aritmética la hace el código.
3. **El score de fiabilidad se calcula, no se le pregunta al LLM.** La autoconfianza
   declarada de un modelo está mal calibrada; una suma de señales observadas no. Y puedes
   subirlo cambiando cómo fotografías, que es todo el sentido de tener un score.
4. **La subida a Vinted sigue siendo manual.** No hay API pública y el riesgo de perder una
   cuenta de vendedor con valoraciones supera con creces los dos minutos que se ahorran.

## Coste

**Vía recomendada:** cero coste variable — todo dentro de tu suscripción de ChatGPT y de
Python local. Tu tiempo es el coste: unos 30-45 segundos por prenda.

**Vía aparcada (n8n):** unos 0,08 € por prenda con Claude Opus 5, más la cuota de Serper.
