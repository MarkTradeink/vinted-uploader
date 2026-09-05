# Puesta en marcha

El workflow ya existe en tu n8n, **sin publicar**:
[Vinted · Clasificar lote de prendas](https://automation.cifral.io/workflow/3EmHDtZ1D97rPFBW) (`3EmHDtZ1D97rPFBW`).

Estos son los pasos que faltan. Ninguno requiere escribir código.

---

## 1. Crear el Google Sheet (10 min)

Crea una hoja nueva llamada **`Vinted - Clasificacion de prendas`** con cuatro pestañas.

**Pestaña `Prendas`** — pega esta fila como cabecera (fila 1):

```
id_prenda	fecha_lote	n_fotos	foto_principal	carpeta_drive	categoria	tipo_prenda	marca	marca_origen	talla	talla_es	talla_origen	color_principal	color_secundario	material	patron	estilo	temporada	condicion	defectos	medidas	titulo	descripcion	keywords	precio_objetivo	precio_min	precio_suelo	n_comparables	rango_comparables	fuente_precio	tier_marca	score	score_desglose	flags	estado	plataforma	precio_publicado	fecha_publicacion	precio_venta	fecha_venta
```

`medidas`, `plataforma`, `precio_publicado`, `fecha_publicacion`, `precio_venta` y
`fecha_venta` las rellenas tú; el workflow no las toca.

**Pestaña `Marcas`** — cabecera `marca`, `tier`, `multiplicador`, `notas`. Rellénala con
las 40 marcas que más manejas. Media hora de trabajo, la variable más predictiva del
sistema. Arranque:

```
marca	tier	multiplicador	notas
Shein	D	0.4	fast fashion muy barata
Primark	D	0.5
Zara	C	1.0	referencia base
H&M	C	0.8
Mango	C	1.0
Bershka	D	0.6
Levi's	B	1.6	el denim vintage sube mas
Nike	B	1.5
Adidas	B	1.4
The North Face	A	2.2
Carhartt	A	2.2
Ralph Lauren	A	2.4
Patagonia	A	2.4
```

**Pestaña `Ventas`** — cabecera `id_prenda`, `marca`, `tipo`, `precio_estimado`,
`precio_venta`, `dias_hasta_venta`, `plataforma`. Vacía por ahora.

**Pestaña `Eval`** — misma cabecera que `Prendas`. Vacía por ahora (paso 6).

Formato condicional en `score`: verde ≥85, ámbar 50–84, rojo <50.

---

## 2. Carpeta de Drive (2 min)

Crea `/vinted/entrada/`. Copia el ID de la URL: en
`drive.google.com/drive/folders/`**`1AbCdEfGh...`** el ID es la parte en negrita.

No hacen falta más carpetas: el sistema no mueve ni borra nada. La deduplicación por
`id_prenda` es lo que evita reprocesar, así que las fotos se quedan donde están.

---

## 3. Rellenar los nodos que quedan pendientes (5 min)

Abre el workflow. Los campos marcados como pendientes están todos en un sitio:

**`Configuracion del lote`**
| Campo | Qué poner |
|---|---|
| `idCarpetaEntrada` | El ID del paso 2 |
| `urlCarpetaEntrada` | La URL completa de esa carpeta |
| `chatIdTelegram` | Tu chat ID (pregúntaselo a `@get_id_bot` en Telegram) |

El resto (`minutosDeGracia` 10, `fotosMinimas` 3, `fotosMaximas` 8,
`factorPedidoPagado` 0.65, `precioBaseTierC` 12) ya viene con valores razonables.

**Los tres nodos de Google Sheets** — selecciona el documento del paso 1 en el desplegable
"Document". La pestaña ya viene puesta por nombre (`Prendas` / `Marcas`).

**Los dos nodos HTTP Request** — n8n no autoasigna credenciales en estos nodos, así que
hay que elegirlas a mano:
- `Listar fotos en Drive con EXIF` → credencial **Google Drive Cifral**
- `Buscar precios comparables` → credencial **Serper API**

**`Revisar carpeta cada dia`** — ponle la cadencia que quieras, o desactiva el nodo si
prefieres lanzarlo tú a mano con el otro disparador.

---

## 4. Primer lote de prueba (20 min)

Fotografía **5 prendas** siguiendo `03-protocolo-fotos.md` al pie de la letra, súbelas a
`/vinted/entrada/` y espera 10 minutos (el margen de gracia evita procesar un lote a medio
subir). Luego dale a **Procesar lote ahora**.

Qué mirar, en este orden:
1. **`Agrupar fotos en prendas` debe sacar exactamente 5 items.** Si saca 3 o 7, la
   agrupación falló: mira `umbral_segundos` en la salida y revisa tus pausas al fotografiar.
2. **`marca_origen` debe poner `etiqueta`** en la mayoría. Si pone `inferido`, tus fotos de
   etiqueta están lejos o borrosas — se arregla con la cámara, no con el prompt.
3. **`n_comparables` mayor que 0.** Si sale 0 en todas, revisa que la credencial de Serper
   esté bien puesta en el nodo HTTP.

---

## 5. Calibrar (continuo)

El único número que merece la pena tocar al principio es **`factorPedidoPagado`**. Empieza
en 0,65. Cuando tengas 10–15 ventas reales, compara en la pestaña `Ventas` lo que estimaste
con lo que cobraste y muévelo. Si vendes sistemáticamente por encima de lo estimado, súbelo;
si las prendas se te quedan colgadas semanas, bájalo.

---

## 6. Workflow de evaluación (cuando tengas 30 prendas conocidas)

Es la compensación por no tener el núcleo en código: sin él no hay forma de saber si un
cambio en el prompt mejora o empeora.

No hace falta construir nada nuevo: **duplica el workflow** y cambia tres cosas.

1. `Configuracion del lote` → apunta a una carpeta fija `/vinted/eval/` con 30 prendas
   cuyos valores correctos hayas anotado a mano.
2. Los nodos de Sheets → pestaña **`Eval`** en vez de `Prendas`.
3. Quita el nodo de Telegram.

Añade en la pestaña `Eval` tres columnas a la derecha con los valores correctos
(`marca_real`, `talla_real`, `precio_venta_real`) y una cuarta con
`=SI(marca=marca_real;1;0)`. La media de esa columna es tu tasa de acierto de marca.

Flujo de trabajo: anota la tasa → cambia el prompt del nodo `Clasificar prenda con Claude` →
vacía la pestaña `Eval` → relanza → compara. Congela el prompt cuando dos rondas seguidas
no mejoren.

Sin este paso el sistema funcionará, pero nunca sabrás cuánto se equivoca.

---

## Coste real esperado

A 50–300 prendas/mes con Claude Opus 5, unos **0,08 € por prenda** más las búsquedas de
Serper. Entre **4 y 24 € al mes**. Contra prendas que vendes a 15–40 €, es un 0,2–0,5% de
los ingresos.

Si en algún momento se dispara, el sitio donde mirar es el número de reintentos del nodo de
Claude: `maxTries` está en 3, y cada reintento es una llamada completa que se paga.
