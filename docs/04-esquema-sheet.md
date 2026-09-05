# Esquema del Google Sheet

Cuatro pestañas. `Prendas` la escribe el sistema; `Marcas` y `Config` las mantienes tú;
`Ventas` la rellenas al vender y es la que hace que el sistema mejore con el tiempo.

---

## Pestaña `Prendas` — una fila por prenda

Las columnas están ordenadas en el orden en que Vinted te pide los datos, para que subir un
anuncio sea copiar de izquierda a derecha sin saltar.

### Identidad
| Columna | Tipo | Notas |
|---|---|---|
| `id_prenda` | texto | Hash de las fotos. Hace la escritura idempotente |
| `fecha_lote` | fecha | |
| `n_fotos` | entero | |
| `carpeta_drive` | URL | Enlace directo a las fotos |
| `foto_principal` | URL | Para vista previa dentro del Sheet |

### Clasificación
| Columna | Tipo | Notas |
|---|---|---|
| `categoria` | enum | Mujer/Hombre/Niño → Ropa/Calzado/Accesorios |
| `tipo_prenda` | texto | camiseta, vaqueros, cazadora… |
| `marca` | texto | |
| `marca_origen` | enum | `etiqueta` \| `logo` \| `inferido` — **alimenta el score** |
| `talla` | texto | Tal cual figura en la etiqueta |
| `talla_es` | texto | Equivalente español normalizado |
| `talla_origen` | enum | `etiqueta` \| `inferido` |
| `color_principal` | texto | |
| `color_secundario` | texto | |
| `material` | texto | De la etiqueta de composición |
| `patron` | texto | liso, rayas, estampado… |
| `estilo` | texto | casual, deportivo, vintage… |
| `temporada` | enum | verano / invierno / entretiempo |
| `medidas` | texto | **Manual.** `pecho 52 / largo 68` |

### Estado
| Columna | Tipo | Notas |
|---|---|---|
| `condicion` | enum | Etiquetas exactas de Vinted (ver nota abajo) |
| `defectos` | texto | Lo que el modelo detecta; confírmalo tú |

### Contenido del anuncio
| Columna | Tipo | Notas |
|---|---|---|
| `titulo` | texto | ≤60 caracteres. Formato `Marca + tipo + color + talla` |
| `descripcion` | texto | Bloque listo para copiar, con medidas y defectos incluidos |
| `keywords` | texto | Términos de búsqueda para el cuerpo del anuncio |

### Precio
| Columna | Tipo | Notas |
|---|---|---|
| `precio_objetivo` | número | Con el que publicas |
| `precio_min` | número | Venta rápida |
| `precio_suelo` | número | No aceptes por debajo |
| `n_comparables` | entero | Cuántos anuncios reales se encontraron |
| `rango_comparables` | texto | `12–28 €` |
| `justificacion_precio` | texto | Una frase: en qué se basa el número |

### Fiabilidad
| Columna | Tipo | Notas |
|---|---|---|
| `score` | 0–100 | Determinista. Ver `01-analisis.md` §1.4 |
| `score_desglose` | texto | Qué señales sumaron y cuáles restaron |
| `flags` | texto | `agrupacion_dudosa`, `sin_etiqueta_marca`, `sin_comparables`… |

### Operación (la rellenas tú)
| Columna | Tipo | Notas |
|---|---|---|
| `estado` | enum | pendiente / revisado / publicado / vendido / descartado |
| `plataforma` | enum | Vinted / Wallapop / ambas |
| `precio_publicado` | número | |
| `fecha_publicacion` | fecha | |
| `precio_venta` | número | **Esta columna es la que entrena el sistema** |
| `fecha_venta` | fecha | |

> **Formato condicional recomendado:** `score` ≥85 verde, 50–84 ámbar, <50 rojo. De un
> vistazo sabes qué filas puedes publicar sin mirar y cuáles hay que revisar.

> **Nota sobre `condicion`:** Vinted usa un conjunto cerrado de etiquetas (del orden de
> "Nuevo con etiquetas" / "Nuevo sin etiquetas" / "Muy bueno" / "Bueno" / "Satisfactorio").
> Confírmalas en la app antes de congelar el enum — las cambian de vez en cuando y por país.
> Se configuran en la pestaña `Config`, no en el código.

---

## Pestaña `Marcas` — la mantienes tú

| `marca` | `tier` | `multiplicador` | `notas` |
|---|---|---|---|
| Shein | D | 0.4 | Fast fashion muy barata |
| Zara | C | 1.0 | Referencia base |
| Levi's | B | 1.6 | El denim vintage sube más |
| Ralph Lauren | A | 2.4 | |

Empieza con las ~40 marcas que más manejas. Es media hora de trabajo y es la variable más
predictiva del precio en todo el sistema.

## Pestaña `Config`

Parámetros que ajustas sin tocar código: factor pedido→pagado (empieza en `0.65`), umbral
de agrupación, tope de gasto por lote, etiquetas de condición de Vinted, modelo a usar.

## Pestaña `Ventas`

Histórico plano: `id_prenda`, `marca`, `tipo`, `precio_estimado`, `precio_venta`,
`dias_hasta_venta`, `plataforma`. Es la fuente del informe de sesgo de la Fase 5 y, a
partir de ~100 filas, el mejor predictor de precio que vas a tener.
