import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from PIL import Image
from vinted_batch.photos import scan, contacts, digest
from vinted_batch.master import HEADERS, fingerprint, read_xlsx
from vinted_batch.inventory import validate, make_plan, verify_applied
from vinted_batch.__main__ import csv_safe, save_new


def fixture():
    manifest = {'photos': [{'photo_id': 'P0001', 'file': 'new.jpg', 'sha256': 'a' * 64, 'error': None}]}
    batch = json.loads((Path(__file__).parents[1] / 'examples/review.json').read_text(encoding='utf-8'))
    sheets = {name: {'rows': [headers.copy()], 'formulas': {}} for name, headers in HEADERS.items()}
    sheets['Precios']['rows'].append(['V38', 'Old', 'M', 5, 7, 3, 5, 'Used', 'Estimate', ''])
    sheets['Anuncios']['rows'].append(['V38', 'Old', 'Old description', '', 'old.jpg'])
    sheets['Fotos']['rows'].append(['V38', 212, 'old.jpg', 'Principal propuesta'])
    sheets['Fuentes']['rows'].append(['S15', 'Old source', 1, 2, 'EUR', 'Other model', 'https://example.org'])
    sheets['Guía'] = {'rows': [], 'formulas': {f'B{r}': f"=SUM('Precios'!{c}2:{c}2)" for r, c in zip(range(16, 20), 'DEFG')}}
    master = {'sheets': sheets, 'fingerprint': fingerprint(sheets), 'captured_at': '2026-09-05T00:00:00Z'}
    return manifest, batch, master


def apply_in_memory(plan, master):
    result = copy.deepcopy(master)
    for entry in plan['appends']:
        result['sheets'][entry['sheet']]['rows'].extend(copy.deepcopy(entry['values']))
    for entry in plan['summary_updates']:
        result['sheets'][entry['sheet']]['formulas'][entry['cell']] = entry['formula']
    result['fingerprint'] = fingerprint(result['sheets'])
    return result


class InventoryTests(unittest.TestCase):
    def test_allocate_after_highest_id_and_preserve_input(self):
        manifest, batch, master = fixture()
        original = copy.deepcopy(master)
        plan = make_plan(manifest, batch, master)
        self.assertEqual(plan['allocated'][0]['item_id'], 'V39')
        self.assertEqual(plan['appends'][0]['range'], "'Precios'!A3:J3")
        self.assertEqual(master, original)
        self.assertEqual(len(plan['summary_updates']), 4)

    def test_retry_is_noop_including_renamed_photo(self):
        manifest, batch, master = fixture()
        plan = make_plan(manifest, batch, master)
        after = apply_in_memory(plan, master)
        verify_applied(plan, after)
        registry = {'photos': plan['registry_additions']}
        manifest['photos'][0]['file'] = 'renamed.jpg'
        retry = make_plan(manifest, batch, after, registry)
        self.assertEqual(retry['appends'], [])
        self.assertEqual(retry['skipped'], [{'key': 'item-001', 'existing_id': 'V39'}])

    def test_changed_listing_is_not_silently_skipped(self):
        m, b, s = fixture()
        plan = make_plan(m, b, s)
        s = apply_in_memory(plan, s)
        b['items'][0]['description'] = 'Changed description'
        with self.assertRaisesRegex(ValueError, 'different listing'):
            make_plan(m, b, s)

    def test_filename_reused_with_changed_bytes(self):
        m, b, s = fixture()
        plan = make_plan(m, b, s)
        s = apply_in_memory(plan, s)
        m['photos'][0]['sha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'changed content'):
            make_plan(m, b, s, {'photos': plan['registry_additions']})

    def test_partial_master_write_is_rejected(self):
        m, b, s = fixture()
        plan = make_plan(m, b, s)
        s['sheets']['Precios']['rows'].extend(plan['appends'][0]['values'])
        s['fingerprint'] = fingerprint(s['sheets'])
        with self.assertRaisesRegex(ValueError, 'disagree'):
            make_plan(m, b, s)

    def test_missing_photo_is_rejected(self):
        m, b, _ = fixture()
        m['photos'].append({'photo_id': 'P0002', 'file': 'back.jpg', 'sha256': 'b' * 64})
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            validate(m, b)
        b['excluded_photos'] = [{'photo_id': 'P0002', 'reason': 'Unrelated screenshot, visually reviewed'}]
        validate(m, b)

    def test_unreviewed_group_and_unreadable_photo(self):
        m, b, _ = fixture()
        b['items'][0]['grouping_reviewed'] = False
        with self.assertRaisesRegex(ValueError, 'visually review'):
            validate(m, b)
        b['items'][0]['grouping_reviewed'] = True
        m['photos'][0]['error'] = 'Unknown format'
        with self.assertRaisesRegex(ValueError, 'unreadable'):
            validate(m, b)

    def test_duplicate_photo_assignment(self):
        m, b, _ = fixture()
        second = copy.deepcopy(b['items'][0]); second['key'] = 'second'
        b['items'].append(second)
        with self.assertRaisesRegex(ValueError, 'multiple items'):
            validate(m, b)

    def test_duplicate_bytes_across_new_items(self):
        m, b, s = fixture()
        m['photos'].append({'photo_id': 'P0002', 'file': 'copy.jpg', 'sha256': 'a' * 64})
        second = copy.deepcopy(b['items'][0]); second.update(key='second', photo_ids=['P0002'], primary_photo_id='P0002')
        b['items'].append(second)
        with self.assertRaisesRegex(ValueError, 'Duplicate content'):
            make_plan(m, b, s)

    def test_partial_old_new_group(self):
        m, b, s = fixture()
        m['photos'].append({'photo_id': 'P0002', 'file': 'old.jpg', 'sha256': 'b' * 64})
        b['items'][0]['photo_ids'].append('P0002')
        with self.assertRaisesRegex(ValueError, 'mix of existing'):
            make_plan(m, b, s)

    def test_numeric_prices_and_ranges(self):
        for bad in ('6', float('nan'), float('inf'), -1, True):
            m, b, _ = fixture(); b['items'][0]['prices']['vinted'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(m, b)
        m, b, _ = fixture(); b['items'][0]['prices']['low'] = 100
        with self.assertRaisesRegex(ValueError, 'range'):
            validate(m, b)

    def test_source_required_and_remapped(self):
        m, b, s = fixture(); b['items'][0]['pricing_basis'] = 'comparables'
        with self.assertRaisesRegex(ValueError, 'needs sources'):
            validate(m, b)
        b['sources'] = [{'source_id': 'local-1', 'url': 'https://example.org/listing', 'reference': 'Fictional source',
                         'low': 5, 'high': 8, 'currency': 'EUR', 'checked_at': '2026-09-05',
                         'kind': 'asking', 'limitations': 'Different model; example only'}]
        b['items'][0]['source_ids'] = ['local-1']
        plan = make_plan(m, b, s)
        source = next(x for x in plan['appends'] if x['sheet'] == 'Fuentes')
        self.assertEqual(source['values'][0][0], 'S16')

    def test_fingerprint_and_header_mismatch(self):
        m, b, s = fixture(); s['sheets']['Precios']['rows'][0][1] = 'Changed'
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            make_plan(m, b, s)
        s['fingerprint'] = fingerprint(s['sheets'])
        with self.assertRaisesRegex(ValueError, 'headers'):
            make_plan(m, b, s)

    def test_extra_columns_and_custom_summary_preserved(self):
        m, b, s = fixture()
        s['sheets']['Precios']['rows'][0].append('Sale price')
        s['sheets']['Precios']['rows'][1].append(99)
        s['sheets']['Guía']['formulas']['B16'] = '=99'
        s['fingerprint'] = fingerprint(s['sheets'])
        plan = make_plan(m, b, s)
        self.assertEqual(len(plan['appends'][0]['values'][0]), 10)
        self.assertEqual(len(plan['summary_updates']), 3)
        self.assertTrue(any('B16' in n for n in plan['manual_notes']))

    def test_verify_rejects_changed_cell_or_missing_formula(self):
        m, b, s = fixture(); plan = make_plan(m, b, s)
        s = apply_in_memory(plan, s)
        s['sheets']['Precios']['rows'][-1][3] = 999
        s['fingerprint'] = fingerprint(s['sheets'])
        with self.assertRaisesRegex(ValueError, 'Not applied'):
            verify_applied(plan, s)
        s = apply_in_memory(plan, fixture()[2])
        s['sheets']['Guía']['formulas']['B16'] = '=0'
        s['fingerprint'] = fingerprint(s['sheets'])
        with self.assertRaisesRegex(ValueError, 'Summary'):
            verify_applied(plan, s)

    def test_paths_cannot_escape(self):
        for path in ('../photo.jpg', '/photo.jpg', 'C:/photo.jpg', '..\\photo.jpg'):
            m, b, _ = fixture(); m['photos'][0]['file'] = path
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'Unsafe'):
                validate(m, b)

    def test_csv_formula_escape_and_numeric_preservation(self):
        self.assertEqual(csv_safe('=HYPERLINK("bad")'), '\'=HYPERLINK("bad")')
        self.assertEqual(csv_safe('  +1'), "'  +1")
        self.assertEqual(csv_safe(6.5), 6.5)
        self.assertEqual(csv_safe('Jersey azul'), 'Jersey azul')


class FileTests(unittest.TestCase):
    def test_photo_scan_hashes_errors_and_contacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); photos = root / 'photos'; photos.mkdir()
            Image.new('RGB', (60, 90), 'blue').save(photos / 'one.jpg')
            (photos / 'broken.png').write_bytes(b'not an image')
            before = digest(photos / 'one.jpg')
            manifest = scan(photos)
            self.assertEqual(len(manifest['photos']), 2)
            self.assertEqual(sum(bool(p['error']) for p in manifest['photos']), 1)
            contacts(manifest, root)
            self.assertTrue((root / 'contact-001.jpg').exists())
            self.assertEqual(digest(photos / 'one.jpg'), before)

    def test_output_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.json'; save_new(path, {'first': True})
            with self.assertRaises(FileExistsError):
                save_new(path, {'first': False})

    def test_xlsx_reader_inline_shared_numeric_and_formula(self):
        ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'minimal.xlsx'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Test" sheetId="1" r:id="rId1"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
                z.writestr('xl/sharedStrings.xml', f'<sst xmlns="{ns}"><si><t>Shared</t></si></sst>')
                z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Inline</t></is></c><c r="C1" t="s"><v>0</v></c></row><row r="3"><c r="A3"><v>6.5</v></c><c r="B3"><f>A3*2</f><v>13</v></c></row></sheetData></worksheet>')
            result = read_xlsx(path)
            self.assertEqual(result['sheets']['Test']['rows'], [['Inline', None, 'Shared'], [], [6.5, 13]])
            self.assertEqual(result['sheets']['Test']['formulas'], {'B3': '=A3*2'})


if __name__ == '__main__':
    unittest.main()
