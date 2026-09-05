"""Read a Google Sheets XLSX export without rewriting the source workbook."""
import hashlib
import json
import posixpath
import re
import zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
HEADERS = {
    'Precios': ['ID', 'Artículo', 'Talla de etiqueta', 'Vinted EUR', 'Wallapop EUR',
                'Cierre desde EUR', 'Cierre hasta EUR', 'Estado visible', 'Base del precio', 'Fuente URL'],
    'Anuncios': ['ID', 'Título para ambas plataformas', 'Descripción para ambas plataformas',
                 'Antes de publicar', 'Foto principal'],
    'Fotos': ['ID', 'N.º en revisión', 'Archivo original', 'Uso'],
    'Fuentes': ['ID fuente', 'Referencia', 'Precio desde', 'Precio hasta', 'Moneda',
                'Comparabilidad y limitaciones', 'URL'],
}


def fingerprint(sheets):
    return hashlib.sha256(json.dumps(sheets, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def read_xlsx(path):
    sheets = {}
    with zipfile.ZipFile(path) as z:
        strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            strings = [''.join(t.text or '' for t in si.findall('.//s:t', NS))
                       for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        rels = {r.attrib['Id']: r.attrib['Target']
                for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        for sheet in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', NS):
            target = rels[sheet.attrib[f"{{{NS['r']}}}id"]]
            target = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
            rows, formulas = [], {}
            for r in ET.fromstring(z.read(target)).findall('s:sheetData/s:row', NS):
                cells = []
                for c in r.findall('s:c', NS):
                    address = c.attrib['r']
                    col = 0
                    for char in re.match('[A-Z]+', address)[0]:
                        col = col * 26 + ord(char) - 64
                    while len(cells) < col:
                        cells.append(None)
                    v, f = c.find('s:v', NS), c.find('s:f', NS)
                    kind = c.get('t')
                    raw = v.text if v is not None else None
                    if kind == 's':
                        value = strings[int(raw)] if raw is not None else None
                    elif kind == 'inlineStr':
                        value = ''.join(t.text or '' for t in c.findall('s:is//s:t', NS))
                    elif kind == 'b':
                        value = raw == '1'
                    elif kind in ('str', 'e'):
                        value = raw
                    else:
                        value = float(raw) if raw is not None else None
                        if isinstance(value, float) and value.is_integer():
                            value = int(value)
                    cells[col - 1] = value
                    if f is not None:
                        formulas[address] = '=' + (f.text or '')
                while cells and cells[-1] is None:
                    cells.pop()
                if cells or any(re.search(rf'\D{r.attrib["r"]}$', a) for a in formulas):
                    n = int(r.attrib['r'])
                    while len(rows) < n:
                        rows.append([])
                    rows[n - 1] = cells
            sheets[sheet.attrib['name']] = {'rows': rows, 'formulas': formulas}
    return {'schema_version': 1, 'captured_at': datetime.now(timezone.utc).isoformat(),
            'sheets': sheets, 'fingerprint': fingerprint(sheets)}


def check_master(master):
    sheets = master['sheets']
    if master.get('fingerprint') != fingerprint(sheets):
        raise ValueError('Master snapshot fingerprint does not match its contents.')
    for name, headers in HEADERS.items():
        rows = sheets.get(name, {}).get('rows', [])
        if not rows or rows[0][:len(headers)] != headers:
            raise ValueError(f'{name}: master headers changed; map them explicitly before planning.')
    prices = [r[0] for r in sheets['Precios']['rows'][1:] if r and r[0]]
    listings = [r[0] for r in sheets['Anuncios']['rows'][1:] if r and r[0]]
    if len(prices) != len(set(prices)) or len(listings) != len(set(listings)):
        raise ValueError('Master has duplicate item IDs.')
    if set(prices) != set(listings) or any(not re.fullmatch(r'V\d+', str(i)) for i in prices):
        raise ValueError('Master item IDs disagree across Precios and Anuncios, or use an unknown format.')
    photo_owners = {}
    for row in sheets['Fotos']['rows'][1:]:
        if not row or not row[0]:
            continue
        if row[0] not in prices or len(row) < 3 or not row[2]:
            raise ValueError('Fotos contains an orphan ID or missing filename.')
        key = str(row[2]).casefold()
        if key in photo_owners:
            raise ValueError(f'Duplicate master photo filename: {row[2]}')
        photo_owners[key] = row[0]
    return set(prices), photo_owners
