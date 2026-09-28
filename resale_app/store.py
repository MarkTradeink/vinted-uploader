"""Private SQLite drafts. Import never overwrites local work or publication receipts."""
import hashlib
import json
import math
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from vinted_batch.master import read_xlsx, check_master


def now():
    return datetime.now(timezone.utc).isoformat()


def draft(photos=()):
    return dict(id='local-' + uuid.uuid4().hex[:12], title='', description='', price='',
                notes='', photos=list(photos), status='borrador', url='', reviewed=False,
                provenance='Creado en la app', research='')


def photo_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate(item):
    if not item['title'].strip() or len(item['title']) > 50:
        raise ValueError('El título debe tener entre 1 y 50 caracteres.')
    if not item['description'].strip():
        raise ValueError('Falta la descripción.')
    try:
        price = float(str(item['price']).replace(',', '.'))
    except (ValueError, TypeError):
        raise ValueError('Introduce un precio válido en euros.') from None
    if not math.isfinite(price) or price <= 0:
        raise ValueError('El precio debe ser mayor que cero.')
    if not 1 <= len(item['photos']) <= 20:
        raise ValueError('Selecciona entre 1 y 20 fotos.')
    if not all(Path(p).is_file() for p in item['photos']):
        raise ValueError('Faltan archivos de fotos; revisa sus rutas.')
    if not item['reviewed']:
        raise ValueError('Revisa fotos, texto, precio y dudas; marca la casilla de revisión.')
    if item['url'] or item['status'] in ('publicado', 'en navegador'):
        raise ValueError('Ya tiene un enlace o una carga pendiente. Comprueba Vinted antes de repetir.')


def listing_url(url):
    p = urlparse(url)
    import re
    return (p.scheme == 'https' and p.hostname in ('www.vinted.es', 'vinted.es')
            and bool(re.fullmatch(r'/items/\d+(?:-[^/]*)?/?', p.path)))


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS photos (hash TEXT PRIMARY KEY, owner TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (at TEXT, item TEXT, action TEXT, detail TEXT)')
        self.db.commit()

    def all(self):
        return [json.loads(r[0]) for r in self.db.execute('SELECT data FROM items ORDER BY rowid')]

    def save(self, item):
        hashes = {photo_hash(p) for p in item['photos']}
        with self.db:
            for h in hashes:
                row = self.db.execute('SELECT owner FROM photos WHERE hash=?', (h,)).fetchone()
                if row and row[0] != item['id']:
                    raise ValueError('Foto duplicada: ya pertenece al artículo ' + row[0])
            old = self.db.execute('SELECT data FROM items WHERE id=?', (item['id'],)).fetchone()
            if old:
                previous = json.loads(old[0])
                if previous['url'] and item['url'] != previous['url']:
                    raise ValueError('No se puede borrar ni sustituir un recibo de publicación.')
            self.db.execute('INSERT OR REPLACE INTO items VALUES (?,?)',
                            (item['id'], json.dumps(item, ensure_ascii=False)))
            self.db.execute('DELETE FROM photos WHERE owner=?', (item['id'],))
            self.db.executemany('INSERT INTO photos VALUES (?,?)', [(h, item['id']) for h in hashes])

    def event(self, item, action, detail=''):
        with self.db:
            self.db.execute('INSERT INTO events VALUES (?,?,?,?)', (now(), item, action, detail))

    def import_xlsx(self, path, root):
        master = read_xlsx(path)
        check_master(master)
        sheets = master['sheets']
        prices = {r[0]: r for r in sheets['Precios']['rows'][1:] if r and r[0]}
        photos = {}
        root = Path(root).resolve()
        for r in sheets['Fotos']['rows'][1:]:
            if len(r) >= 3 and r[0]:
                p = (root / str(r[2])).resolve()
                if not p.is_relative_to(root) or not p.is_file():
                    raise ValueError('Foto ausente o fuera de la carpeta: ' + str(r[2]))
                photos.setdefault(r[0], []).append(str(p))
        existing = {i['id'] for i in self.all()}
        pending = []
        for row in sheets['Anuncios']['rows'][1:]:
            if not row or not row[0] or row[0] in existing:
                continue
            r = list(row) + [''] * 5
            price = prices[r[0]]
            item = draft(photos.get(r[0], []))
            item.update(id=r[0], title=r[1] or '', description=r[2] or '',
                        notes=str(r[3] or ''), price=price[3],
                        provenance=f'Exportación XLSX: {Path(path).name}; importada {now()}')
            if r[4]:
                main = str((root / str(r[4])).resolve())
                if main in item['photos']:
                    item['photos'].remove(main)
                    item['photos'].insert(0, main)
            pending.append(item)
        # Preflight entire import, avoiding partially imported batches.
        claimed = {h: owner for h, owner in self.db.execute('SELECT hash,owner FROM photos')}
        for item in pending:
            for p in item['photos']:
                h = photo_hash(p)
                if h in claimed and claimed[h] != item['id']:
                    raise ValueError('Foto duplicada entre ' + claimed[h] + ' y ' + item['id'])
                claimed[h] = item['id']
        for item in pending:
            self.save(item)
        return len(pending)
