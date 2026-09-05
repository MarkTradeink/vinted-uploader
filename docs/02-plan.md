# Plan de implementación

> **Decisión tomada:** todo en n8n, sin código propio que mantener. Volumen previsto
> 50–300 prendas/mes. El análisis en `01-analisis.md` recomendaba un núcleo en Python
> primero por el bucle de medición; se descartó a favor de no tocar código. La
> compensación está en la fase 4.

Estado: **fases 0 a 2 hechas.** Lo que queda son pasos de configuración, no de desarrollo.

---

## Fase 0 — Diseño ✅

Análisis, decisiones de arquitectura, protocolo de fotografía y esquema del Sheet.
Ver `01-analisis.md`, `03-protocolo-fotos.md` y `04-esquema-sheet.md`.

## Fase 1 — Workflow de clasificación ✅

Creado en n8n como **[Vinted · Clasificar lote de prendas](https://automation.cifral.io/workflow/3EmHDtZ1D97rPFBW)**
(`3EmHDtZ1D97rPFBW`), 22 nodos, sin publicar. El código fuente SDK está versionado en
`n8n/clasificar-lote.sdk.ts`.

Cubre la cadena completa: listado de Drive con EXIF, agrupación adaptativa en prendas,
deduplicación contra el Sheet, clasificación multiimagen con Claude Opus 5, comparables
vía Serper, cálculo de precios y score, escritura idempotente en Sheets y aviso por
Telegram.

## Fase 2 — Precio y fiabilidad ✅

Integrado en el mismo workflow en lugar de ser una fase aparte, porque en n8n separarlo
habría significado un segundo workflow y una llamada extra.

## Fase 3 — Puesta en marcha ⬜ (te toca a ti, ~40 min)

Crear el Sheet, la carpeta de Drive, rellenar la configuración y lanzar un lote de prueba
de 5 prendas. Paso a paso en **`05-puesta-en-marcha.md`**.

## Fase 4 — Medición ⬜ (cuando tengas 30 prendas conocidas)

La compensación por no tener el núcleo en código. Se resuelve duplicando el workflow y
apuntándolo a una carpeta fija y a la pestaña `Eval`. Detalle en
`05-puesta-en-marcha.md` §6.

Sin esta fase el sistema funciona, pero no sabrás cuánto se equivoca ni si un cambio en el
prompt mejora algo.

## Fase 5 — Bucle de aprendizaje ⬜ (continuo)

Al vender, rellenas `precio_venta` y `fecha_venta`. Con 10–15 ventas ya puedes recalibrar
`factorPedidoPagado`. Con ~100, tu histórico predice mejor que cualquier búsqueda web.

## Fase 6 — Opcional, solo si el volumen lo justifica ⬜

Extensión de navegador que rellene el formulario de Vinted desde la fila del Sheet (tú
logueado, tú pulsas el botón; nunca un bot headless). Retoque automático de fotos.

---

## Arquitectura tal como quedó

```
Disparo manual  ─┐
Programado      ─┴→ Configuracion del lote
                       ↓
                    Listar fotos en Drive con EXIF   (HTTP: el nodo de Drive no
                       ↓                              devuelve imageMediaMetadata)
                    Leer prendas ya procesadas       (dedup)
                       ↓
                    Leer tabla de marcas             (tiers de precio)
                       ↓
                    Agrupar fotos en prendas         (clustering EXIF adaptativo)
                       ↓
                    Recorrer prendas ──── done ───→ Resumir el lote → Telegram
                       │
                       └── por prenda:
                            Separar fotos → Descargar de Drive → Juntar en un item
                            → Clasificar con Claude (todas las fotos, 1 llamada)
                            → Parsear → Buscar comparables (Serper)
                            → Calcular precios y score  ← aritmética, no LLM
                            → Escribir en el Sheet      ← idempotente por id_prenda
```

## Decisiones que quedaron fijadas en el workflow

| Decisión | Dónde vive | Por qué |
|---|---|---|
| Agrupación por EXIF, umbral = 3× la mediana de huecos del lote | `Agrupar fotos en prendas` | Se adapta a si fotografías rápido o despacio, sin pedirte disciplina |
| Margen de 10 minutos antes de procesar | mismo nodo | Evita clasificar un lote a medio subir |
| Dedup por `id_prenda` (hash de los IDs de foto) | mismo nodo | Relanzar no duplica ni vuelve a pagar; no hace falta mover ficheros |
| Todas las fotos en **una** llamada de visión | `Juntar fotos en un solo item` | El modelo cruza la etiqueta con la prenda; 5 llamadas sueltas no pueden |
| `marca_origen` / `talla_origen` obligatorios | prompt de `Clasificar prenda con Claude` | Distinguir dato leído de dato inventado es lo que hace útil el score |
| **El precio se calcula, no lo dice el LLM** | `Calcular precios y score` | Mediana recortada × factor pedido→pagado × estado. Elimina la alucinación aritmética |
| **El score se calcula, no se pregunta** | mismo nodo | La autoconfianza declarada de un modelo está mal calibrada |
| Fallo de Serper o de Claude no tumba la prenda | `onError: continueRegularOutput` | Sale una fila con score bajo y su flag, en vez de perderse |

## Riesgos que quedan vivos

| Riesgo | Mitigación actual | Qué harías si se materializa |
|---|---|---|
| Sin golden set, la calidad del prompt no es medible | Ninguna hasta la fase 4 | Montar el workflow de eval (`05` §6) |
| El modelo devuelve algo que no es JSON | Parseo defensivo, `parse_error`, score 0 y flag | Endurecer el prompt; el JSON crudo queda en `respuesta_cruda` |
| Fotos reenviadas por WhatsApp pierden el EXIF | Recae en `createdTime`, que en una subida masiva es casi idéntico → agrupación mala | Subir siempre el original; o usar subcarpetas por prenda |
| Serper cambia el formato de respuesta | Regex tolerante; sin precios → `n_comparables` 0 y precio por tier | Ajustar el regex en `Calcular precios y score` |
| Límite de peticiones de Google Sheets | Una escritura por prenda, con 3 reintentos | A este volumen no debería aparecer |
