"""Photo inventory and contact sheets. Originals are opened read-only."""
import hashlib
from pathlib import Path

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def scan(root, recursive=False):
    from PIL import Image
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    root = Path(root).resolve(strict=True)
    paths = root.rglob('*') if recursive else root.iterdir()
    paths = sorted((p for p in paths if p.is_file() and p.suffix.lower() in EXTENSIONS),
                   key=lambda p: p.relative_to(root).as_posix().casefold())
    if not paths:
        raise ValueError('No supported photos in the input folder.')
    records = []
    for i, path in enumerate(paths, 1):
        if not path.resolve().is_relative_to(root):
            raise ValueError(f'Photo symlink leaves input folder: {path.name}')
        row = {'photo_id': f'P{i:04d}', 'file': path.relative_to(root).as_posix(),
               'sha256': digest(path), 'width': None, 'height': None, 'error': None}
        try:
            with Image.open(path) as im:
                row['width'], row['height'] = im.size
                im.verify()
        except (OSError, ValueError, SyntaxError) as exc:
            row['error'] = str(exc)
        records.append(row)
    return {'schema_version': 1, 'photo_root': str(root), 'photos': records}


def contacts(manifest, output):
    from PIL import Image, ImageDraw, ImageOps
    output = Path(output)
    root = Path(manifest['photo_root'])
    photos = manifest['photos']
    for offset in range(0, len(photos), 24):
        page = Image.new('RGB', (1440, 1680), 'white')
        draw = ImageDraw.Draw(page)
        for j, row in enumerate(photos[offset:offset + 24]):
            x, y = (j % 4) * 360, (j // 4) * 280
            if row['error']:
                draw.text((x + 10, y + 100), 'Cannot decode: inspect original', fill='red')
            else:
                with Image.open(root / row['file']) as original:
                    im = ImageOps.exif_transpose(original).convert('RGB')
                    im.thumbnail((350, 245))
                    page.paste(im, (x + (350 - im.width) // 2, y))
            label = f"{row['photo_id']}  {Path(row['file']).name}"
            draw.text((x + 8, y + 249), label[:47], fill='black')
        page.save(output / f'contact-{offset // 24 + 1:03d}.jpg', quality=85)
