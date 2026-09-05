"""Validate reviewed batches and build append-only plans, without network writes."""
import math
import re
from datetime import date
from pathlib import PurePosixPath
from urllib.parse import urlparse
from .master import HEADERS, check_master


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate(manifest, batch):
    require(batch.get('schema_version') == 1, 'Unsupported batch schema.')
    require(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', batch.get('batch_id', ''))), 'Invalid batch_id.')
    date.fromisoformat(batch['evaluated_at'])
    photos = {p['photo_id']: p for p in manifest['photos']}
    require(len(photos) == len(manifest['photos']), 'Duplicate photo IDs in manifest.')
    require(bool(photos), 'Empty photo manifest.')
    for p in photos.values():
        require(bool(re.fullmatch('[a-f0-9]{64}', p.get('sha256', ''))), 'Invalid photo hash.')
        path = PurePosixPath(p['file'])
        require(not path.is_absolute() and '..' not in path.parts and ':' not in p['file'] and '\\' not in p['file'], 'Unsafe photo path.')
    sources = {s['source_id']: s for s in batch.get('sources', [])}
    require(len(sources) == len(batch.get('sources', [])), 'Duplicate source IDs.')
    for s in sources.values():
        require(urlparse(s['url']).scheme in ('http', 'https') and bool(urlparse(s['url']).netloc), 'Invalid source URL.')
        require(s['kind'] in ('asking', 'sold', 'retail'), 'Source kind must distinguish asking/sold/retail.')
        require(all(number(s[k]) for k in ('low', 'high')) and s['low'] <= s['high'], 'Invalid source prices.')
        require(bool(s.get('limitations')) and bool(s.get('reference')), 'Source needs reference and limitations.')
        require(bool(re.fullmatch('[A-Z]{3}', s['currency'])), 'Source currency must be a three-letter code.')
        date.fromisoformat(s['checked_at'])
    assigned, keys = set(), set()
    for item in batch['items']:
        key = item['key']
        require(key and key not in keys, 'Duplicate or empty item key.')
        keys.add(key)
        require(item.get('grouping_reviewed') is True, f'{key}: visually review the grouping first.')
        require(0 < len(item.get('title', '')) <= 50, f'{key}: title must be 1–50 characters.')
        for field in ('description', 'size', 'condition_visible', 'pricing_reason'):
            require(isinstance(item.get(field), str) and bool(item[field].strip()), f'{key}: missing {field}.')
        require(isinstance(item.get('confirm'), list) and all(isinstance(v, str) for v in item['confirm']), f'{key}: confirm must be a text list.')
        pp = item['prices']
        require(all(number(pp.get(k)) for k in ('vinted', 'wallapop', 'low', 'high')), f'{key}: prices must be finite nonnegative numbers.')
        require(pp['low'] <= pp['high'] <= min(pp['vinted'], pp['wallapop']), f'{key}: inconsistent negotiation range.')
        require(item.get('pricing_basis') in ('comparables', 'estimate'), f'{key}: identify the pricing basis.')
        refs = item.get('source_ids', [])
        require(isinstance(refs, list) and all(s in sources for s in refs), f'{key}: unknown source.')
        require(item['pricing_basis'] != 'comparables' or bool(refs), f'{key}: comparable pricing needs sources.')
        ids = item['photo_ids']
        require(bool(ids) and len(ids) == len(set(ids)), f'{key}: duplicate or empty photo selection.')
        require(set(ids) <= photos.keys(), f'{key}: unknown photo ID.')
        require(not assigned.intersection(ids), f'{key}: photos assigned to multiple items.')
        require(not any(photos[i].get('error') for i in ids), f'{key}: unreadable photo; exclude with reason or fix decoder.')
        require(item['primary_photo_id'] in ids, f'{key}: primary photo must belong to item.')
        assigned.update(ids)
    for row in batch.get('excluded_photos', []):
        require(row['photo_id'] in photos and row['photo_id'] not in assigned and bool(row.get('reason')), 'Invalid/duplicate excluded photo.')
        assigned.add(row['photo_id'])
    require(assigned == photos.keys(), f'Unreviewed photos: {sorted(photos.keys() - assigned)}')


def make_plan(manifest, batch, master, registry=None):
    validate(manifest, batch)
    existing, names = check_master(master)
    registry = registry or {'photos': []}
    hashes = {}
    for record in registry['photos']:
        require(record['item_id'] in existing, 'Local registry contains an ID absent from the current master.')
        hashes.setdefault(record['sha256'], set()).add(record['item_id'])
    photos = {p['photo_id']: p for p in manifest['photos']}
    next_id = max((int(i[1:]) for i in existing), default=0) + 1
    old_sources = [r[0] for r in master['sheets']['Fuentes']['rows'][1:] if r and r[0]]
    require(len(old_sources) == len(set(old_sources)), 'Duplicate source IDs in master.')
    require(all(re.fullmatch(r'S\d+', str(s)) for s in old_sources), 'Unknown master source ID format.')
    next_source = max((int(s[1:]) for s in old_sources), default=0) + 1
    rows = {name: [] for name in HEADERS}
    used_sources, allocated, skipped, new_registry = {}, [], [], []
    source_map = {s['source_id']: s for s in batch.get('sources', [])}
    numbers = [r[1] for r in master['sheets']['Fotos']['rows'][1:] if len(r) > 1 and type(r[1]) in (int, float)]
    photo_number = int(max(numbers, default=0)) + 1
    new_hashes, new_names = set(), set()
    for item in batch['items']:
        selected = [photos[i] for i in item['photo_ids']]
        owners, hits = set(), 0
        for p in selected:
            owners_here = set(hashes.get(p['sha256'], set()))
            if p['file'].casefold() in names:
                name_owner = names[p['file'].casefold()]
                old = [r for r in registry['photos'] if r['file'].casefold() == p['file'].casefold()]
                require(not old or any(r['sha256'] == p['sha256'] for r in old), f"Filename reused with changed content: {p['file']}")
                owners_here.add(name_owner)
            owners.update(owners_here)
            hits += bool(owners_here)
        if owners:
            require(len(owners) == 1 and hits == len(selected), f"{item['key']}: mix of existing/new photos or multiple existing items; reconcile before append.")
            owner = next(iter(owners))
            pr = next(r for r in master['sheets']['Precios']['rows'][1:] if r and r[0] == owner)
            ar = next(r for r in master['sheets']['Anuncios']['rows'][1:] if r and r[0] == owner)
            p = item['prices']
            require(pr[1:7] == [item['title'], item['size'], p['vinted'], p['wallapop'], p['low'], p['high']]
                    and ar[1:3] == [item['title'], item['description']],
                    f"{item['key']}: existing {owner} has different listing data; use an explicit update, not append.")
            skipped.append({'key': item['key'], 'existing_id': owner})
            continue
        require(not any(p['sha256'] in new_hashes or p['file'].casefold() in new_names for p in selected), 'Duplicate content or filename across new items.')
        new_hashes.update(p['sha256'] for p in selected)
        new_names.update(p['file'].casefold() for p in selected)
        item_id = f'V{next_id:02d}'
        next_id += 1
        for sid in item.get('source_ids', []):
            if sid not in used_sources:
                s = source_map[sid]
                used_sources[sid] = f'S{next_source:02d}'
                next_source += 1
                rows['Fuentes'].append([used_sources[sid], s['reference'], s['low'], s['high'], s['currency'],
                                       f"{s['kind']}; consulta {s['checked_at']}. {s['limitations']}", s['url']])
        pp = item['prices']
        urls = '\n'.join(source_map[s]['url'] for s in item.get('source_ids', []))
        rows['Precios'].append([item_id, item['title'], item['size'], pp['vinted'], pp['wallapop'], pp['low'], pp['high'],
                               item['condition_visible'], item['pricing_reason'], urls or 'Sin comparable cercano verificado'])
        primary = photos[item['primary_photo_id']]['file']
        rows['Anuncios'].append([item_id, item['title'], item['description'], '\n'.join(item['confirm']), primary])
        for p in selected:
            rows['Fotos'].append([item_id, photo_number, p['file'], 'Principal propuesta' if p['file'] == primary else 'Detalle o vista adicional'])
            photo_number += 1
            new_registry.append({'item_id': item_id, 'file': p['file'], 'sha256': p['sha256']})
        allocated.append({'key': item['key'], 'item_id': item_id})
    appends = []
    for name, values in rows.items():
        if values:
            first = len(master['sheets'][name]['rows']) + 1
            last_col = chr(64 + len(HEADERS[name]))
            appends.append({'sheet': name, 'range': f"'{name}'!A{first}:{last_col}{first + len(values) - 1}",
                            'start_row': first, 'values': values})
    summary_updates, notes = [], []
    guide = master['sheets'].get('Guía', {})
    if allocated:
        old_end = len(master['sheets']['Precios']['rows'])
        new_end = old_end + len(rows['Precios'])
        for row, col in zip(range(16, 20), 'DEFG'):
            address = f'B{row}'
            old_formula = f"=SUM('Precios'!{col}2:{col}{old_end})"
            if guide.get('formulas', {}).get(address) == old_formula:
                summary_updates.append({'sheet': 'Guía', 'cell': address, 'expected_formula': old_formula,
                                        'formula': f"=SUM('Precios'!{col}2:{col}{new_end})"})
            else:
                notes.append(f'Guía!{address}: summary is customized or absent; review manually.')
        notes.append('Refresh static batch counts/date text in Guía separately; preserve user edits.')
        notes.append('Extend existing table/filter ranges and copy formatting to appended rows; preserve extra columns.')
    return {'schema_version': 1, 'batch_id': batch['batch_id'], 'base_fingerprint': master['fingerprint'],
            'base_captured_at': master['captured_at'], 'allocated': allocated, 'skipped': skipped,
            'appends': appends, 'summary_updates': summary_updates, 'manual_notes': notes,
            'registry_additions': new_registry, 'value_input_option': 'RAW'}


def verify_applied(plan, master):
    check_master(master)
    for entry in plan['appends']:
        actual = master['sheets'][entry['sheet']]['rows']
        for offset, expected in enumerate(entry['values']):
            index = entry['start_row'] - 1 + offset
            # Sheets omits trailing blanks and returns empty cells as null or empty text.
            received = actual[index] if index < len(actual) else None
            require(received is not None and
                    [(received[i] if i < len(received) and received[i] is not None else '') for i in range(len(expected))]
                    == [('' if v is None else v) for v in expected],
                    f"Not applied exactly: {entry['sheet']} row {index + 1}")
    for entry in plan['summary_updates']:
        require(master['sheets'].get(entry['sheet'], {}).get('formulas', {}).get(entry['cell']) == entry['formula'],
                f"Summary not updated: {entry['sheet']}!{entry['cell']}")
