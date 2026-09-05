#!/usr/bin/env python3
"""Convierte las respuestas pegadas del GPT en un CSV con precios y score calculados.

Uso:
    python3 parsear_respuestas.py /ruta/salida/lote-prendas [/ruta/a/respuestas.txt]

No llama a ninguna API ni gasta ningun token: solo procesa texto local.

Que hace:
  1. Lee respuestas.txt (por defecto, el fichero "respuestas.txt" dentro de la
     carpeta de salida que genero agrupar_fotos.py) y lo separa en bloques, uno
     por prenda, cortando en cada linea "===".
  2. Cruza cada bloque con manifiesto.csv (numero de fotos, aviso de agrupacion)
     usando el ID_PRENDA.
  3. Calcula el precio final y el score de fiabilidad con formulas fijas, NO
     preguntandoselo al modelo: la autoconfianza que declara un LLM esta mal
     calibrada, así que aqui se suman senales que el propio GPT ya reporto
     (leyo una etiqueta o no, cuantos comparables encontro...).
  4. Escribe prendas.csv en la misma carpeta de salida, listo para abrir en
     Excel, Numbers o importar a Google Sheets si quieres.

Si una prenda no aparece en respuestas.txt, o el bloque esta mal formado, se avisa
por pantalla y se omite en vez de romper todo el lote.
"""

import csv
import re
import sys
from pathlib import Path

MULTIPLICADOR_POR_CONDICION = {
    "Nuevo con etiquetas": 1.25,
    "Nuevo sin etiquetas": 1.10,
    "Muy bueno": 1.00,
    "Bueno": 0.85,
    "Satisfactorio": 0.65,
}
BASE_TIER_C = 12
FACTOR_PEDIDO_PAGADO = 0.65  # ajustalo cuando tengas ventas reales, ver docs/05

CAMPOS_ESPERADOS = [
    "ID", "CATEGORIA", "TIPO_PRENDA", "MARCA", "MARCA_ORIGEN", "TALLA",
    "TALLA_ORIGEN", "TALLA_ES", "COLOR_PRINCIPAL", "COLOR_SECUNDARIO",
    "MATERIAL", "MATERIAL_LEGIBLE", "PATRON", "ESTILO", "TEMPORADA",
    "CONDICION", "DEFECTOS", "FOTO_NITIDA", "N_COMPARABLES", "RANGO_PRECIOS",
    "PRECIO_SUGERIDO", "JUSTIFICACION_PRECIO", "TITULO", "DESCRIPCION", "KEYWORDS",
]

COLUMNAS_SALIDA = [
    "id_prenda", "n_fotos", "carpeta", "categoria", "tipo_prenda", "marca",
    "marca_origen", "talla", "talla_es", "talla_origen", "color_principal",
    "color_secundario", "material", "patron", "estilo", "temporada", "condicion",
    "defectos", "medidas", "titulo", "descripcion", "keywords", "precio_objetivo",
    "precio_min", "precio_suelo", "n_comparables", "rango_comparables",
    "fuente_precio", "tier_marca", "score", "score_desglose", "flags", "estado",
    "plataforma", "precio_publicado", "fecha_publicacion", "precio_venta", "fecha_venta",
]


def cargar_marcas(ruta_csv: Path) -> dict:
    tabla = {}
    if not ruta_csv.exists():
        return tabla
    with open(ruta_csv, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            nombre = (fila.get("marca") or "").strip().lower()
            if not nombre:
                continue
            try:
                mult = float(fila.get("multiplicador") or 1)
            except ValueError:
                mult = 1.0
            tabla[nombre] = {"tier": (fila.get("tier") or "C").strip(), "multiplicador": mult}
    return tabla


def cargar_manifiesto(ruta_csv: Path) -> dict:
    manifiesto = {}
    with open(ruta_csv, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            manifiesto[fila["id_prenda"]] = fila
    return manifiesto


def parsear_bloques(texto: str) -> list:
    """Separa el texto pegado en bloques de campo:valor, uno por prenda."""
    bloques = []
    actual = {}
    ultimo_campo = None
    patron_campo = re.compile(r"^([A-Z_]+):\s?(.*)$")

    for linea_cruda in texto.splitlines():
        linea = linea_cruda.rstrip()
        if linea.strip() == "===":
            if actual:
                bloques.append(actual)
            actual = {}
            ultimo_campo = None
            continue
        m = patron_campo.match(linea.strip())
        if m and m.group(1) in CAMPOS_ESPERADOS:
            actual[m.group(1)] = m.group(2).strip()
            ultimo_campo = m.group(1)
        elif ultimo_campo and linea.strip():
            # continuacion de un campo multilinea (p.ej. la descripcion se pego con saltos)
            actual[ultimo_campo] = (actual.get(ultimo_campo, "") + " " + linea.strip()).strip()

    if actual:
        bloques.append(actual)
    return bloques


def es_si(valor: str) -> bool:
    return (valor or "").strip().lower() in ("si", "sí", "true", "yes")


def parsear_numero(texto: str):
    if not texto:
        return None
    m = re.search(r"\d+(?:[.,]\d+)?", texto)
    if not m:
        return None
    return float(m.group(0).replace(",", "."))


def parsear_rango(texto: str):
    numeros = re.findall(r"\d+(?:[.,]\d+)?", texto or "")
    numeros = [float(n.replace(",", ".")) for n in numeros]
    if len(numeros) >= 2:
        return min(numeros), max(numeros)
    if len(numeros) == 1:
        return numeros[0], numeros[0]
    return None, None


def redondear(v: float) -> float:
    return max(3, round(v * 2) / 2)


def calcular_fila(bloque: dict, fila_manifiesto: dict, tabla_marcas: dict) -> dict:
    id_prenda = bloque.get("ID", "").strip()
    n_fotos = int(fila_manifiesto["n_fotos"]) if fila_manifiesto else None
    flag_agrupacion = bool(fila_manifiesto and fila_manifiesto.get("aviso") == "revisar")

    marca = bloque.get("MARCA", "").strip()
    marca_origen = bloque.get("MARCA_ORIGEN", "desconocido").strip().lower() or "desconocido"
    talla_origen = bloque.get("TALLA_ORIGEN", "desconocido").strip().lower() or "desconocido"
    material_legible = es_si(bloque.get("MATERIAL_LEGIBLE", ""))
    foto_nitida = es_si(bloque.get("FOTO_NITIDA", ""))
    condicion = bloque.get("CONDICION", "").strip()

    n_comparables = parsear_numero(bloque.get("N_COMPARABLES", "")) or 0
    n_comparables = int(n_comparables)
    precio_min_rango, precio_max_rango = parsear_rango(bloque.get("RANGO_PRECIOS", ""))
    precio_sugerido = parsear_numero(bloque.get("PRECIO_SUGERIDO", ""))

    info_marca = tabla_marcas.get(marca.lower())
    tier = info_marca["tier"] if info_marca else "sin_clasificar"
    mult_marca = info_marca["multiplicador"] if info_marca else 1.0
    mult_estado = MULTIPLICADOR_POR_CONDICION.get(condicion, 0.85)

    if precio_sugerido:
        objetivo = precio_sugerido
        fuente = "GPT (busqueda web)"
    else:
        objetivo = BASE_TIER_C * mult_marca * mult_estado
        fuente = "tier de marca (sin precio del GPT)"

    precio_objetivo = redondear(objetivo)
    precio_min = redondear(objetivo * 0.75)
    precio_suelo = redondear(objetivo * 0.6)

    dispersion = None
    if precio_min_rango and precio_max_rango and precio_sugerido:
        dispersion = (precio_max_rango - precio_min_rango) / precio_sugerido

    score = 0
    desglose = []
    if marca_origen == "etiqueta":
        score += 25; desglose.append("+25 marca leida de etiqueta")
    elif marca_origen == "logo":
        score += 10; desglose.append("+10 marca por logo")
    elif marca_origen == "inferido":
        score -= 15; desglose.append("-15 marca solo inferida")

    if talla_origen == "etiqueta":
        score += 20; desglose.append("+20 talla leida de etiqueta")

    if n_fotos is not None and n_fotos >= 3 and foto_nitida:
        score += 15; desglose.append("+15 fotos suficientes y nitidas")

    if material_legible:
        score += 10; desglose.append("+10 composicion legible")

    if n_comparables >= 3:
        score += 20; desglose.append(f"+20 {n_comparables} comparables")
    elif n_comparables > 0:
        score += 8; desglose.append(f"+8 solo {n_comparables} comparables")

    if dispersion is not None and dispersion < 0.4:
        score += 10; desglose.append("+10 precios consistentes")

    if flag_agrupacion:
        score -= 20; desglose.append("-20 agrupacion dudosa (revisar carpeta)")

    score = max(0, min(100, score))

    flags = []
    if flag_agrupacion:
        flags.append("agrupacion_dudosa")
    if not marca:
        flags.append("sin_marca")
    if not bloque.get("TALLA", "").strip():
        flags.append("sin_talla")
    if n_comparables == 0:
        flags.append("sin_comparables")
    if tier == "sin_clasificar" and marca:
        flags.append("marca_no_esta_en_la_tabla")
    if fila_manifiesto is None:
        flags.append("id_no_encontrado_en_manifiesto")

    return {
        "id_prenda": id_prenda,
        "n_fotos": n_fotos if n_fotos is not None else "",
        "carpeta": fila_manifiesto["carpeta"] if fila_manifiesto else "",
        "categoria": bloque.get("CATEGORIA", ""),
        "tipo_prenda": bloque.get("TIPO_PRENDA", ""),
        "marca": marca,
        "marca_origen": marca_origen,
        "talla": bloque.get("TALLA", ""),
        "talla_es": bloque.get("TALLA_ES", ""),
        "talla_origen": talla_origen,
        "color_principal": bloque.get("COLOR_PRINCIPAL", ""),
        "color_secundario": bloque.get("COLOR_SECUNDARIO", ""),
        "material": bloque.get("MATERIAL", ""),
        "patron": bloque.get("PATRON", ""),
        "estilo": bloque.get("ESTILO", ""),
        "temporada": bloque.get("TEMPORADA", ""),
        "condicion": condicion,
        "defectos": bloque.get("DEFECTOS", ""),
        "medidas": "",
        "titulo": bloque.get("TITULO", ""),
        "descripcion": bloque.get("DESCRIPCION", ""),
        "keywords": bloque.get("KEYWORDS", ""),
        "precio_objetivo": precio_objetivo,
        "precio_min": precio_min,
        "precio_suelo": precio_suelo,
        "n_comparables": n_comparables,
        "rango_comparables": bloque.get("RANGO_PRECIOS", ""),
        "fuente_precio": fuente,
        "tier_marca": tier,
        "score": score,
        "score_desglose": " | ".join(desglose),
        "flags": ", ".join(flags),
        "estado": "pendiente",
        "plataforma": "",
        "precio_publicado": "",
        "fecha_publicacion": "",
        "precio_venta": "",
        "fecha_venta": "",
    }


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 parsear_respuestas.py /ruta/salida/lote-prendas [/ruta/a/respuestas.txt]")
        sys.exit(1)

    carpeta_salida = Path(sys.argv[1]).expanduser().resolve()
    ruta_manifiesto = carpeta_salida / "manifiesto.csv"
    ruta_respuestas = (
        Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) > 2 else carpeta_salida / "respuestas.txt"
    )
    ruta_marcas = Path(__file__).parent / "marcas.csv"

    if not ruta_manifiesto.exists():
        print(f"No encuentro {ruta_manifiesto}. ¿Corriste antes agrupar_fotos.py?")
        sys.exit(1)
    if not ruta_respuestas.exists():
        print(f"No encuentro {ruta_respuestas}. Pega ahi las respuestas del GPT (ver plantilla_gpt.md).")
        sys.exit(1)

    manifiesto = cargar_manifiesto(ruta_manifiesto)
    tabla_marcas = cargar_marcas(ruta_marcas)
    texto = ruta_respuestas.read_text(encoding="utf-8")
    bloques = parsear_bloques(texto)

    if not bloques:
        print("No se encontro ningun bloque valido en respuestas.txt. ¿Falta la linea '===' al final de cada respuesta?")
        sys.exit(1)

    filas = []
    vistos = set()
    for bloque in bloques:
        id_prenda = bloque.get("ID", "").strip()
        if not id_prenda:
            print("Aviso: un bloque no tiene ID, se omite.")
            continue
        if id_prenda in vistos:
            print(f"Aviso: {id_prenda} aparece dos veces en respuestas.txt, me quedo con la primera.")
            continue
        vistos.add(id_prenda)
        fila_manifiesto = manifiesto.get(id_prenda)
        if fila_manifiesto is None:
            print(f"Aviso: {id_prenda} no esta en manifiesto.csv (¿lo escribiste bien?), se procesa igual sin esa info.")
        filas.append(calcular_fila(bloque, fila_manifiesto, tabla_marcas))

    faltantes = set(manifiesto) - vistos
    if faltantes:
        print(f"\nAviso: {len(faltantes)} prenda(s) del manifiesto no tienen respuesta todavia: {', '.join(sorted(faltantes))}")

    ruta_salida = carpeta_salida / "prendas.csv"
    with open(ruta_salida, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS_SALIDA)
        escritor.writeheader()
        escritor.writerows(filas)

    total = len(filas)
    publicables = sum(1 for f in filas if f["score"] >= 85)
    revisar = sum(1 for f in filas if 50 <= f["score"] < 85)
    refotografiar = sum(1 for f in filas if f["score"] < 50)
    valor = sum(f["precio_objetivo"] for f in filas)

    print(f"\n{total} prendas procesadas -> {ruta_salida}")
    print(f"Publicables sin revisar (score 85+): {publicables}")
    print(f"Revisar 1-2 campos (score 50-84): {revisar}")
    print(f"Refotografiar o repasar a mano (score <50): {refotografiar}")
    print(f"Valor estimado del lote: {valor:.2f} EUR")


if __name__ == "__main__":
    main()
