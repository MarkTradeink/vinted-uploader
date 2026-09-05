#!/usr/bin/env python3
"""Agrupa un lote de fotos en prendas usando la hora de disparo (EXIF).

Uso:
    python3 agrupar_fotos.py /ruta/a/fotos/lote-2026-09-05 [/ruta/de/salida]

No llama a ninguna API ni gasta ningun token: solo lee metadatos EXIF locales.

Que hace:
  1. Lee la fecha/hora de disparo de cada foto (EXIF DateTimeOriginal; si falta,
     usa la fecha de modificacion del fichero como respaldo).
  2. Ordena las fotos por ese instante.
  3. Corta en una prenda nueva cuando el hueco entre dos fotos consecutivas supera
     3 veces la mediana de huecos de todo el lote (minimo 8 segundos). Ese umbral
     se adapta solo: si ese dia fotografiaste rapido, corta mas fino; si fuiste
     despacio, no confunde tus propias pausas con un cambio de prenda.
  4. Copia (nunca mueve) las fotos de cada grupo a salida/prenda-001/, prenda-002/...
     numeradas en orden, listas para arrastrar juntas a un GPT personalizado.
  5. Escribe salida/manifiesto.csv con una fila por prenda: cuantas fotos tiene,
     la carpeta, y un aviso si el numero de fotos es sospechoso (muy pocas o
     demasiadas), para que sepas cuales revisar antes de pasarlas al GPT.

Formatos leidos: .jpg .jpeg .heic .heif .png. Los iPhone guardan en HEIC por
defecto: para leer su EXIF hace falta el paquete opcional "pillow-heif"
(pip install pillow-heif). Sin el, un .heic se abre igual pero sin fecha de
disparo, y el script avisa por pantalla y usa la fecha del fichero como
respaldo, que es menos fiable si copiaste todas las fotos de golpe.
"""

import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_DISPONIBLE = True
except ImportError:
    HEIF_DISPONIBLE = False

EXTENSIONES = {".jpg", ".jpeg", ".heic", ".heif", ".png"}
FOTOS_MINIMAS = 3
FOTOS_MAXIMAS = 8
UMBRAL_MINIMO_SEGUNDOS = 8

TAG_FECHA_ORIGINAL = next(
    (k for k, v in ExifTags.TAGS.items() if v == "DateTimeOriginal"), 36867
)


def leer_instante(ruta: Path) -> datetime:
    """Devuelve el instante de disparo de la foto, o la fecha del fichero si no hay EXIF.

    DateTimeOriginal casi siempre vive en el sub-IFD Exif (0x8769), no en el IFD
    principal, asi que hay que pedirselo explicitamente con get_ifd(). Se comprueba
    tambien el IFD principal por si acaso, y como ultimo recurso se usa la fecha de
    modificacion del fichero.
    """
    try:
        with Image.open(ruta) as img:
            exif = img.getexif()
            sub_exif = exif.get_ifd(ExifTags.IFD.Exif)
            valor = sub_exif.get(TAG_FECHA_ORIGINAL) or exif.get(TAG_FECHA_ORIGINAL)
            if valor:
                return datetime.strptime(valor, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return datetime.fromtimestamp(ruta.stat().st_mtime)


def agrupar(fotos_con_instante):
    """Recibe [(ruta, instante), ...] ordenado y devuelve una lista de grupos."""
    if not fotos_con_instante:
        return [], 0

    huecos = [
        (fotos_con_instante[i][1] - fotos_con_instante[i - 1][1]).total_seconds()
        for i in range(1, len(fotos_con_instante))
    ]
    if huecos:
        ordenados = sorted(huecos)
        mediana = ordenados[len(ordenados) // 2]
    else:
        mediana = 0
    umbral = max(mediana * 3, UMBRAL_MINIMO_SEGUNDOS)

    grupos = [[fotos_con_instante[0]]]
    for i in range(1, len(fotos_con_instante)):
        hueco = (fotos_con_instante[i][1] - fotos_con_instante[i - 1][1]).total_seconds()
        if hueco > umbral:
            grupos.append([])
        grupos[-1].append(fotos_con_instante[i])
    return grupos, umbral


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 agrupar_fotos.py /ruta/a/fotos/del/lote [/ruta/de/salida]")
        sys.exit(1)

    entrada = Path(sys.argv[1]).expanduser().resolve()
    if not entrada.is_dir():
        print(f"No existe la carpeta: {entrada}")
        sys.exit(1)

    salida = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) > 2 else entrada.parent / (entrada.name + "-prendas")
    salida.mkdir(parents=True, exist_ok=True)

    archivos = sorted(p for p in entrada.iterdir() if p.suffix.lower() in EXTENSIONES)
    if not archivos:
        print(f"No hay fotos ({', '.join(sorted(EXTENSIONES))}) en {entrada}")
        sys.exit(1)

    heic_sin_soporte = [p for p in archivos if p.suffix.lower() in (".heic", ".heif")]
    if heic_sin_soporte and not HEIF_DISPONIBLE:
        print(
            f"AVISO: {len(heic_sin_soporte)} foto(s) .heic/.heif detectadas, pero falta el "
            "paquete 'pillow-heif' para leer su fecha de disparo. Su agrupacion se hara "
            "por la fecha del fichero, que es poco fiable si copiaste todas las fotos de "
            "golpe. Instala con: pip install pillow-heif  (o cambia el ajuste de la camara "
            "del movil a 'Mas compatible' para que guarde en JPG desde el principio).\n"
        )

    fotos_con_instante = sorted(((p, leer_instante(p)) for p in archivos), key=lambda x: x[1])
    grupos, umbral = agrupar(fotos_con_instante)

    filas = []
    for i, grupo in enumerate(grupos, start=1):
        id_prenda = f"prenda-{i:03d}"
        carpeta_prenda = salida / id_prenda
        carpeta_prenda.mkdir(parents=True, exist_ok=True)

        for j, (ruta, _instante) in enumerate(grupo, start=1):
            destino = carpeta_prenda / f"{id_prenda}_{j}{ruta.suffix.lower()}"
            shutil.copy2(ruta, destino)

        n = len(grupo)
        aviso = "revisar" if (n < FOTOS_MINIMAS or n > FOTOS_MAXIMAS) else ""
        filas.append(
            {
                "id_prenda": id_prenda,
                "n_fotos": n,
                "carpeta": str(carpeta_prenda),
                "aviso": aviso,
            }
        )

    manifiesto = salida / "manifiesto.csv"
    with open(manifiesto, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=["id_prenda", "n_fotos", "carpeta", "aviso"])
        escritor.writeheader()
        escritor.writerows(filas)

    revisar = [f for f in filas if f["aviso"]]
    print(f"\n{len(filas)} prendas detectadas en {entrada.name}")
    print(f"Umbral de corte usado: {umbral:.0f} segundos (adaptado a este lote)")
    print(f"Carpetas creadas en: {salida}")
    print(f"Manifiesto: {manifiesto}")
    if revisar:
        print(f"\n{len(revisar)} prenda(s) con numero de fotos sospechoso, revisa antes de pasarlas al GPT:")
        for f in revisar:
            print(f"  - {f['id_prenda']}: {f['n_fotos']} fotos -> {f['carpeta']}")
    else:
        print("\nTodas las prendas tienen un numero de fotos razonable (3-8).")


if __name__ == "__main__":
    main()
