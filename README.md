# vinted-uploader

Clasificación automática de prendas de segunda mano: sueltas un lote de fotos y obtienes
un Google Sheet con título, descripción, marca, talla, precios recomendados y un score de
fiabilidad por prenda, listo para publicar en Vinted o Wallapop.

## Estado

**En diseño.** Todavía no hay código: primero el análisis y el plan, para no construir la
fontanería antes de saber dónde está el valor.

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/01-analisis.md`](docs/01-analisis.md) | Dónde está el valor real, decisiones de arquitectura, costes, y qué **no** va a hacer bien |
| [`docs/02-plan.md`](docs/02-plan.md) | Seis fases con criterios de "hecho", stack y riesgos |
| [`docs/03-protocolo-fotos.md`](docs/03-protocolo-fotos.md) | Cómo fotografiar. La palanca más grande del sistema, y no es código |
| [`docs/04-esquema-sheet.md`](docs/04-esquema-sheet.md) | Columnas del Sheet y pestañas de configuración |

## Las cuatro decisiones que definen el sistema

1. **Agrupación por timestamp EXIF**, no por convención de nombres ni por visión. Cero
   disciplina al fotografiar, y los casos dudosos se marcan en lugar de adivinarse.
2. **El precio se fundamenta en comparables reales**, no en el prior del modelo. Y se
   devuelven tres precios (objetivo, mínimo, suelo), que es lo que de verdad usas.
3. **El score de fiabilidad se calcula, no se le pregunta al LLM.** La autoconfianza
   declarada de un modelo está mal calibrada; una suma de señales observadas no.
4. **La subida a Vinted sigue siendo manual.** No hay API pública y el riesgo de perder
   una cuenta de vendedor supera con creces los dos minutos que se ahorran.
