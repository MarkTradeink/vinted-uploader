# vinted-uploader

Clasificación automática de prendas de segunda mano: sueltas un lote de fotos en Google
Drive y obtienes un Google Sheet con título, descripción, marca, talla, precios
recomendados y un score de fiabilidad por prenda, listo para publicar en Vinted o Wallapop.

## Estado

Workflow construido en n8n y **sin publicar**:
[Vinted · Clasificar lote de prendas](https://automation.cifral.io/workflow/3EmHDtZ1D97rPFBW)
(`3EmHDtZ1D97rPFBW`, 22 nodos). Falta la configuración inicial —
ver **[`docs/05-puesta-en-marcha.md`](docs/05-puesta-en-marcha.md)**, unos 40 minutos.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/01-analisis.md`](docs/01-analisis.md) | Dónde está el valor real, decisiones de arquitectura, costes, y qué **no** va a hacer bien |
| [`docs/02-plan.md`](docs/02-plan.md) | Estado de las fases, arquitectura final y riesgos vivos |
| [`docs/03-protocolo-fotos.md`](docs/03-protocolo-fotos.md) | Cómo fotografiar. La palanca más grande del sistema, y no es código |
| [`docs/04-esquema-sheet.md`](docs/04-esquema-sheet.md) | Columnas del Sheet y pestañas de configuración |
| [`docs/05-puesta-en-marcha.md`](docs/05-puesta-en-marcha.md) | Pasos que faltan, lote de prueba y calibración |
| [`n8n/clasificar-lote.sdk.ts`](n8n/clasificar-lote.sdk.ts) | Código fuente del workflow (SDK de n8n), versionado |

## Las cuatro decisiones que definen el sistema

1. **Agrupación por timestamp EXIF** con umbral adaptativo (3× la mediana de huecos del
   propio lote), no por convención de nombres ni por visión. Cero disciplina al
   fotografiar, y los casos dudosos se marcan en lugar de adivinarse.
2. **El precio se calcula, no lo dice el LLM.** Mediana de comparables reales recortada al
   10–90%, por el factor pedido→pagado, por el multiplicador de estado. El modelo hace
   percepción; la aritmética la hace el código.
3. **El score de fiabilidad se calcula, no se le pregunta al LLM.** La autoconfianza
   declarada de un modelo está mal calibrada; una suma de señales observadas no. Y puedes
   subirlo cambiando cómo fotografías, que es todo el sentido de tener un score.
4. **La subida a Vinted sigue siendo manual.** No hay API pública y el riesgo de perder una
   cuenta de vendedor con valoraciones supera con creces los dos minutos que se ahorran.

## Coste

Unos **0,08 € por prenda** con Claude Opus 5. Entre 4 y 24 € al mes a 50–300 prendas.
