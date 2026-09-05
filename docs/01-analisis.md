# Análisis: sistema de clasificación automática de prendas

> Documento de decisión previo a escribir código. Responde a: *¿dónde está el valor
> real de este sistema, dónde están los riesgos, y qué arquitectura los gestiona mejor?*

## 0. TL;DR

- La fontanería (Drive → LLM → Sheets) es el 10% fácil. El valor y el riesgo están en
  **agrupar fotos en prendas**, **leer la etiqueta**, **fundamentar el precio** y **saber
  cuándo el sistema no sabe**.
- **No construyas una app.** Eres el único usuario. Una app añade UI, auth y hosting, y
  cero precisión a las estimaciones.
- **n8n solo se queda corto en el sitio equivocado.** Es excelente como disparador y
  conectores, pero malísimo para lo que aquí decide la calidad: iterar el prompt y *medir*
  si una versión es mejor que la anterior.
- **Recomendación: híbrido, y el orden importa.** Primero un script local que puedas
  ejecutar contra un set conocido y medir. Cuando el prompt se estabilice, n8n encima como
  disparador. Al revés se itera a ciegas.
- Coste real: **~0,08 € por prenda** con Opus 5 (0,2–0,5% del precio de venta). El coste
  no es un problema aquí; un precio mal estimado sí.

---

## 1. Los cuatro problemas que realmente importan

### 1.1 Agrupar fotos en prendas — el problema que nadie ve venir

Subes 200 fotos a una carpeta. El sistema tiene que saber que las fotos 7 a 11 son la
misma cazadora. Este paso, si falla, contamina todo lo demás: mezclas la etiqueta de una
prenda con las fotos de otra y obtienes una ficha convincente y falsa.

| Opción | Fiabilidad | Coste para ti |
|---|---|---|
| Una subcarpeta por prenda | 100% | Disciplina alta al organizar |
| Convención de nombre (`001_frontal.jpg`) | 100% | Renombrar 200 ficheros: inviable |
| **Clustering por timestamp EXIF** | ~90–95% | Cero: solo fotografía con ritmo |
| Clustering visual con LLM | ~80% | Caro; falla con prendas parecidas |

**Decisión: clustering por EXIF con validación LLM.** Agrupas por hueco temporal (si pasan
más de N segundos entre dos fotos, empieza prenda nueva). Es determinista, gratis y no te
obliga a nada. Luego, en la misma llamada de visión que ya vas a hacer, el modelo confirma
"¿son todas estas la misma prenda?" y marca las que sobran. Los casos dudosos no se
adivinan: se marcan en el Sheet con `flag_agrupacion` para que los revises.

Detalle práctico: `N` no debe ser fijo. Calcúlalo del propio lote (mediana de los huecos ×
3). Fotografiar despacio un día y rápido otro no debería romper el sistema.

### 1.2 Marca y talla: dependen al 100% de la foto de la etiqueta

Los modelos de visión leen logos bien y etiquetas de composición regular: letra pequeña,
tela arrugada, poco contraste. **Esta es la palanca más grande de todo el sistema y no es
código, es protocolo.** Dos fotos obligatorias por prenda: etiqueta de marca y etiqueta de
talla/composición, de cerca y enfocadas.

Sin esas dos fotos, la marca pasa a ser "inferida por estilo" — y una marca inferida
arrastra el precio a la basura, porque el precio *es* mayormente la marca. El sistema debe
distinguir siempre entre **marca leída** y **marca inferida**, y decírtelo en una columna.
Ver `03-protocolo-fotos.md`.

### 1.3 El precio: aquí es donde estos sistemas mienten

Si le preguntas a un LLM "¿cuánto vale esta chaqueta Zara?", te da un número plausible y
sin ningún fundamento. Suena bien, no está anclado en nada. Tres niveles de anclaje:

1. **Prior del modelo (gratis, error ±100%).** Inútil como número final. Vale como control
   de cordura: si el resto del sistema dice 180 € por una camiseta de Zara, algo falla.
2. **Búsqueda web con Serper (ya la tienes).** Consultas del tipo
   `"<marca> <tipo> <talla> vinted"` devuelven anuncios reales y vivos. **Ojo con la trampa:
   son precios *pedidos*, no *pagados*.* En Vinted lo que se pide suele estar un 30–50%
   por encima de lo que acaba vendiéndose. Hay que corregirlo explícitamente, no usar la
   mediana en crudo.
3. **Tu propio histórico.** Una pestaña con lo que vendiste, a cuánto y en cuántos días.
   A partir de 50–100 ventas esto gana a todo lo demás, porque es tu mercado, tus fotos y
   tu reputación de vendedor. Por eso el Sheet nace ya con esas columnas aunque tarden
   meses en llenarse.

**Decisión: precio = f(tier de marca, tipo de prenda, estado, comparables).** El tier de
marca vive en una pestaña que mantienes tú (Shein→D, Zara→C, Levi's→B, Ralph Lauren→A);
es la variable más predictiva y la más barata de mantener. Los comparables vienen de
Serper. El modelo reconcilia y **justifica** por escrito.

Y no devuelve un precio, devuelve tres:
- `precio_objetivo` — con el que publicas
- `precio_min` — venta rápida si tienes prisa
- `precio_suelo` — por debajo, no aceptes contraofertas

Eso es lo que de verdad usas al negociar; un número solo no sirve.

> **Sobre raspar la API interna de Vinted:** no lo hagas. No es pública, va contra sus
> términos, cambia sin aviso y te arriesga la cuenta de vendedor. Serper sobre resultados
> públicos de búsqueda cubre el 90% del valor por la vía correcta, y ya la pagas.

### 1.4 El score de fiabilidad: no se lo preguntes al LLM

Si le pides al modelo que puntúe su propia confianza, te dirá "90%" casi siempre. La
autoconfianza declarada de un LLM está mal calibrada y deriva entre versiones del prompt.

**Decisión: el score se calcula, no se pregunta.** Suma determinista de señales que el
pipeline realmente ha observado:

| Señal observada | Puntos |
|---|---|
| Marca **leída** de una etiqueta visible | +25 |
| Talla **leída** de una etiqueta visible | +20 |
| ≥3 fotos, al menos una nítida de la prenda entera | +15 |
| Composición/material legible | +10 |
| ≥3 comparables encontrados online | +20 |
| Dispersión de comparables baja (rango < 40% de la mediana) | +10 |
| Marca solo inferida por logo o estilo | −15 |
| Agrupación de fotos dudosa | −20 |

Ahora el número significa algo accionable:
- **≥85** → publica tal cual
- **50–84** → revisa los 2 campos que el sistema marca como flojos
- **<50** → el protocolo de fotos falló en esa prenda; refotografía

Y, crucialmente, **puedes subir tu score cambiando tu comportamiento**, que es todo el
sentido de tener un score.

---

## 2. Arquitectura: n8n, código, o app completa

### App completa — **no, todavía no**
Eres el único usuario. Una app son meses de UI, autenticación, hosting y estado que no
mejoran ni un punto la calidad de las estimaciones. Solo tiene sentido si acabas
vendiéndoselo a otros revendedores, y esa decisión la tomas con datos dentro de 6 meses,
no ahora.

### n8n en solitario — **se queda corto donde más duele**
A favor: ya tienes cableado Drive, Sheets, Anthropic y Serper. Cero hosting.

En contra, y es lo que decide: la calidad de este sistema vive en el prompt de visión y en
la lógica de precio. Para mejorarlos necesitas poder coger 30 prendas cuyo resultado
correcto ya conoces, cambiar el prompt, relanzar y **ver un número que dice si has
mejorado o empeorado**. En n8n ese bucle es doloroso, así que en la práctica no lo haces —
y acabas ajustando el prompt por intuición, que es exactamente como se construyen sistemas
que parecen funcionar y estiman mal.

También: reintentos por prenda, validación de JSON, reanudar un lote a medias y no
reprocesar lo ya hecho. Todo posible en n8n, todo más frágil.

### **Recomendación: híbrido, en este orden**

**Fase 1 — el núcleo en código local (Python).** Un comando: apuntas a una carpeta y
escribe en el Sheet. Lo lanzas tú desde la terminal. Dos tardes de trabajo. La razón de
que vaya *primero* es el bucle de medición: con el núcleo en código puedes montar un set
de 30 prendas conocidas y saber si un cambio mejora. Ahí es donde se gana la precisión.

**Fase 2 — n8n encima, cuando el prompt ya no cambie.** Disparador de Drive → llamada a tu
servicio → aviso por Telegram cuando el lote está listo. n8n hace de fontanería, que es en
lo que es excelente.

Si prefieres no tocar código nunca, se puede hacer todo en n8n — asúmelo como una decisión
de "no voy a optimizar la precisión", y compénsalo revisando manualmente todo lo que baje
de score 70.

---

## 3. Modelo y coste

Precios API (por millón de tokens): **Opus 5** $5 / $25 · **Sonnet 5** $2 / $10 ·
**Haiku 4.5** $1 / $5.

Cuentas por prenda (5 fotos redimensionadas a ~1000px ≈ 1.300 tokens cada una, más prompt
de sistema y resultados de búsqueda):

| Modelo | Entrada ~10,5k | Salida ~1,2k | **Por prenda** | **200 prendas** |
|---|---|---|---|---|
| Opus 5 | $0,053 | $0,030 | **~$0,08** | **~$16** |
| Sonnet 5 | $0,021 | $0,012 | ~$0,03 | ~$6,6 |
| Haiku 4.5 | $0,011 | $0,006 | ~$0,017 | ~$3,4 |

**Decisión: Opus 5.** Ocho céntimos contra una prenda que vendes a 15–40 € es un 0,2–0,5%
de los ingresos. Lo que compras con esa diferencia es leer etiquetas borrosas y razonar el
precio, que es literalmente el producto. Bajar de modelo antes de haber medido la calidad
es optimizar lo que no cuesta.

Dos reductores de coste que sí valen la pena y no tocan la calidad:
- **Prompt caching** sobre el prompt de sistema y la tabla de tiers de marca (la parte
  fija y grande de cada llamada; las lecturas de caché cuestan una fracción).
- **Batch API**, 50% de descuento. Encaja perfecto: lanzas el lote y recoges resultados
  más tarde, no necesitas respuesta inmediata.

Con ambos, 200 prendas bajan del entorno de los 16 $ a menos de 8 $.

---

## 4. La subida a Vinted/Wallapop: tu instinto es correcto

Ninguna de las dos tiene API pública de publicación. Automatizar la subida significa
automatizar el navegador contra sus sistemas anti-bot, y el riesgo real no es técnico:
**es perder una cuenta de vendedor con valoraciones**, que vale mucho más que los dos
minutos de copiar y pegar que te ahorras.

Así que el Sheet se diseña para que subir sea mecánico: columnas en el mismo orden en que
Vinted te las pide, `condicion` ya traducida a las etiquetas exactas de Vinted, y la
descripción en un único bloque listo para copiar.

Opción futura y de riesgo bajo (Fase 6, opcional): una extensión de navegador que rellene
el formulario desde la fila del Sheet. Tú ya estás logueado, tú pulsas el botón, ella
escribe. Muy distinto de un bot headless.

---

## 5. Lo que este sistema *no* va a hacer bien (dilo desde el principio)

- **Medidas reales** (ancho de pecho, largo). No se estiman de una foto con fiabilidad, y
  las devoluciones en Vinted vienen sobre todo de la talla. Columna manual, cinta métrica,
  30 segundos por prenda. Merece la pena.
- **Detectar defectos pequeños**: bolitas, manchas leves, costuras abiertas. El modelo ve
  lo evidente. La condición final la confirmas tú.
- **Autenticar marcas de lujo.** Si vendes premium, la verificación es humana. El sistema
  no debe dar un veredicto de autenticidad ni sugerirlo.
- **Precios de nicho** (vintage, piezas de colección, deportivas raras). El precio depende
  de detalles que la búsqueda genérica no captura. Esas prendas saldrán con score bajo,
  que es exactamente el comportamiento correcto.
