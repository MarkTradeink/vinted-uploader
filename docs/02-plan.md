# Plan de implementación

Seis fases. Las fases 1–3 son el sistema real; la 4 lo automatiza; las 5–6 son mejora
continua y opcionales. Estimaciones en tardes de trabajo, no en días completos.

---

## Fase 0 — Preparación (~1 hora)

- [ ] Crear el Google Sheet con 4 pestañas: `Prendas`, `Marcas`, `Ventas`, `Config`
      (esquema completo en `04-esquema-sheet.md`).
- [ ] Rellenar `Marcas` con las ~40 marcas que más manejas y su tier (A–D). Media hora
      bien invertida: es la variable más predictiva del precio.
- [ ] Crear en Drive `/vinted/entrada/`, `/vinted/procesado/`, `/vinted/error/`.
- [ ] Service Account de Google con acceso al Sheet y a la carpeta de Drive
      (no OAuth de usuario: el script correrá desatendido).
- [ ] Leer `03-protocolo-fotos.md` y hacer un lote de prueba de 5 prendas siguiéndolo.

**Sale de aquí:** el Sheet vivo y 25 fotos reales para desarrollar contra ellas.

---

## Fase 1 — Núcleo de clasificación (~2 tardes)

El corazón. Un comando, una carpeta, filas en el Sheet.

```
vinted-uploader procesar ./fotos/lote-2026-09-05 --dry-run
vinted-uploader procesar ./fotos/lote-2026-09-05 --sheet <id>
```

- [ ] **Ingesta**: leer carpeta local o de Drive, extraer EXIF, ordenar por timestamp.
- [ ] **Agrupación**: clustering por hueco temporal con umbral adaptativo (mediana de
      huecos × 3). Si existen subcarpetas, mandan ellas y se salta el clustering.
- [ ] **Preproceso**: redimensionar a 1000px lado largo, autorrotar por EXIF. Recorta
      coste ~40% sin perder legibilidad de etiquetas.
- [ ] **Llamada de visión** (Claude Opus 5, structured outputs con esquema estricto):
      todas las fotos de la prenda en un mensaje. Devuelve los campos de clasificación,
      **la confirmación de agrupación**, y para marca/talla el `origen` del dato
      (`etiqueta` | `logo` | `inferido`) — este campo alimenta el score.
- [ ] **Score de fiabilidad**: calculado en código con la tabla de `01-analisis.md`.
      Nunca pedido al modelo.
- [ ] **Escritura en Sheets**: una fila por prenda, idempotente por `id_prenda`
      (hash del contenido de las fotos). Relanzar el mismo lote no duplica.
- [ ] **Estado en disco**: un `.jsonl` por lote. Si falla la prenda 47 de 60, reanudas
      desde la 47 sin repagar las 46 primeras.
- [ ] Prompt caching sobre el bloque de sistema.

**Criterio de hecho:** 20 prendas reales entran, 20 filas correctas salen, y relanzar el
comando no duplica ni cobra de nuevo.

**Aquí ya tienes un sistema útil**, aunque los precios todavía sean flojos.

---

## Fase 2 — Fundamentar el precio (~1 tarde)

Sin esto los precios son inventos plausibles.

- [ ] Consulta a **Serper** por prenda: `"<marca> <tipo> <talla>" vinted` +
      una variante en wallapop. Máximo 2 consultas por prenda.
- [ ] Parsear precios de los resultados, descartar outliers (percentiles 10/90).
- [ ] **Corrección pedido→pagado**: aplicar el factor de la pestaña `Config`
      (empieza en 0,65 y ajústalo con tus ventas reales en la Fase 5).
- [ ] Cruzar con el tier de marca de la pestaña `Marcas` y el estado de la prenda.
- [ ] Devolver `precio_objetivo`, `precio_min`, `precio_suelo` + `justificacion_precio`
      en texto (una frase: en qué se basa).
- [ ] Alimentar el score con `n_comparables` y `dispersion_comparables`.

**Criterio de hecho:** para 10 prendas que ya has vendido, `precio_objetivo` cae dentro de
±25% del precio real de venta.

---

## Fase 3 — Medición y ajuste (~1 tarde, y es la fase que más precisión aporta)

Sin esto estás ajustando el prompt a ojo.

- [ ] **Golden set**: 30 prendas fotografiadas cuyos valores correctos anotas a mano
      (marca, talla, material, y precio real de venta si la vendiste).
- [ ] Script `evaluar` que procesa las 30 y saca: % acierto de marca, % de talla,
      error medio de precio, y calibración del score (¿las de score ≥85 aciertan de
      verdad más que las de 50–84?).
- [ ] Iterar el prompt: cambiar → relanzar → comparar. 3 o 4 rondas.
- [ ] Congelar el prompt cuando dos rondas seguidas no mejoren.

**Criterio de hecho:** una tabla de métricas versionada. Sabes cuánto se equivoca tu
sistema, que es el requisito para confiar en él.

---

## Fase 4 — Automatización con n8n (~medio día)

Ahora que el núcleo es estable, la fontanería.

- [ ] Desplegar el núcleo tras un webhook (Cloud Run o un VPS pequeño; es un contenedor).
- [ ] Workflow n8n: trigger de Google Drive sobre `/vinted/entrada/` → agrupa el lote →
      POST al webhook → mueve las fotos a `/procesado/` → **Telegram** con el resumen
      ("18 prendas, 3 con score <50, valor estimado total 412 €").
- [ ] Rama de error: fallo → `/vinted/error/` + Telegram con el motivo.
- [ ] Credenciales que ya tienes: `Google Drive Cifral`, `Google Sheets account_Cifral`,
      `Anthropic account`, `Serper API`, y cualquiera de los bots de Telegram.

**Criterio de hecho:** sueltas fotos en Drive desde el móvil, y a los minutos te llega un
Telegram con el lote clasificado.

---

## Fase 5 — Bucle de aprendizaje (continuo, ~1 hora de montaje)

Lo que convierte esto en un sistema que mejora en vez de uno que se estanca.

- [ ] Al vender, rellenas 3 columnas: `precio_venta`, `fecha_venta`, `plataforma`.
- [ ] Informe mensual: sesgo por marca y por categoría (¿estimo sistemáticamente alto en
      denim?), y recalibración del factor pedido→pagado.
- [ ] Inyectar tus 20 ventas más parecidas como contexto en la estimación de precio. A
      partir de ~100 ventas, esto vale más que cualquier búsqueda web.

---

## Fase 6 — Opcional, solo si el volumen lo justifica

- [ ] Extensión de navegador que rellena el formulario de Vinted desde la fila del Sheet.
      Riesgo bajo (tú logueado, tú pulsas). No un bot headless: no vale la pena arriesgar
      la cuenta.
- [ ] Retoque de fotos: fondo limpio, recorte, enderezado.
- [ ] Multi-idioma para vender fuera de España.

---

## Stack

| Pieza | Elección | Por qué |
|---|---|---|
| Lenguaje | Python 3.11+ | Mejor ecosistema de imagen (Pillow, exifread) y SDK de Anthropic |
| LLM | Claude Opus 5 (`claude-opus-5`) | Lectura de etiquetas y razonamiento de precio; 0,08 €/prenda |
| Salida estructurada | `output_config.format` con esquema estricto | JSON válido garantizado, sin parseo frágil |
| Búsqueda | Serper (ya la tienes) | Comparables reales por la vía correcta |
| Almacén | Google Sheets | Lo editas a mano, y ese es un requisito de verdad |
| Orquestación | n8n, solo desde la Fase 4 | Disparadores y avisos, no lógica de negocio |
| Estado | `.jsonl` por lote | Reanudable e idempotente sin base de datos |

## Estructura del repositorio

```
vinted-uploader/
├── docs/                      # este análisis, el plan, protocolo y esquema
├── src/vinted_uploader/
│   ├── cli.py                 # comandos: procesar, evaluar, sync-ventas
│   ├── ingest.py              # EXIF, orden, redimensionado
│   ├── grouping.py            # clustering temporal → prendas
│   ├── classify.py            # llamada de visión + esquema estricto
│   ├── pricing.py             # Serper, comparables, tier, tres precios
│   ├── scoring.py             # score determinista de fiabilidad
│   ├── sheets.py              # escritura idempotente
│   └── prompts/               # prompts versionados (el activo se congela en Fase 3)
├── eval/
│   ├── golden/                # 30 prendas + valores correctos
│   └── run_eval.py
└── n8n/workflow.json          # exportado, versionado (Fase 4)
```

## Riesgos y cómo se gestionan

| Riesgo | Mitigación |
|---|---|
| Agrupación incorrecta contamina la ficha | Validación LLM + `flag_agrupacion` + score −20 |
| Precios inventados con aspecto creíble | Comparables obligatorios; sin ellos el score no llega a 85 |
| Etiquetas ilegibles | `origen` del dato explícito; el protocolo de fotos es la solución real |
| Cambio de formato en resultados de búsqueda | Parseo tolerante; si falla, precio sin comparables y score bajo, nunca un número inventado |
| Coste desbocado en lotes grandes | Tope de gasto por lote en `Config`; el comando aborta y avisa |
| Deriva de calidad al tocar el prompt | El golden set de la Fase 3 la detecta antes de que llegue a producción |
