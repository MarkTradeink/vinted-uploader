import argparse
import csv
import json
import sys
from pathlib import Path
from .photos import scan, contacts, digest
from .master import read_xlsx, HEADERS, check_master
from .inventory import validate, make_plan, verify_applied


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as out:
        json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write('\n')


def csv_safe(value):
    return "'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')) else value


def main():
    p = argparse.ArgumentParser(description='Prepare reviewed Vinted / Wallapop batches; never publishes listings.')
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare', help='Index photos, create contact sheets and an empty review template.')
    a.add_argument('photos'); a.add_argument('--out', required=True); a.add_argument('--recursive', action='store_true')
    a = sub.add_parser('snapshot', help='Read a freshly downloaded master XLSX, without modifying it.')
    a.add_argument('xlsx'); a.add_argument('--out', required=True)
    a = sub.add_parser('register-baseline', help='Hash existing photos against a trusted master export.')
    a.add_argument('--master', required=True); a.add_argument('--photos', required=True); a.add_argument('--out', required=True)
    for name in ('validate', 'plan'):
        a = sub.add_parser(name)
        a.add_argument('--manifest', required=True); a.add_argument('--batch', required=True)
        if name == 'plan':
            a.add_argument('--master', required=True); a.add_argument('--registry', action='append', default=[]); a.add_argument('--out', required=True)
    a = sub.add_parser('verify-applied', help='Verify a post-write master export before saving a receipt.')
    a.add_argument('--plan', required=True); a.add_argument('--master', required=True); a.add_argument('--receipt', required=True)
    args = p.parse_args()
    try:
        if args.command == 'prepare':
            root, out = Path(args.photos).resolve(strict=True), Path(args.out).resolve()
            if out == root or (args.recursive and out.is_relative_to(root)):
                raise ValueError('Put output outside the recursively scanned photo folder.')
            out.mkdir(parents=True, exist_ok=False)
            manifest = scan(root, args.recursive)
            save_new(out / 'manifest.json', manifest)
            contacts(manifest, out)
            template = {'schema_version': 1, 'batch_id': 'CHANGE-ME', 'evaluated_at': 'YYYY-MM-DD',
                        'items': [], 'sources': [], 'excluded_photos': []}
            save_new(out / 'review.json', template)
            errors = sum(bool(p['error']) for p in manifest['photos'])
            print(f"Indexed {len(manifest['photos'])} photos; {errors} unreadable. Visually group them in review.json.")
        elif args.command == 'snapshot':
            save_new(args.out, read_xlsx(args.xlsx))
            print('Snapshot saved. Its timestamp records extraction, not the age of the downloaded export.')
        elif args.command == 'validate':
            validate(load(args.manifest), load(args.batch))
            print('Batch valid; all photos accounted for. No master or marketplace changes.')
        elif args.command == 'register-baseline':
            master = load(args.master)
            check_master(master)
            root = Path(args.photos).resolve(strict=True)
            records = []
            for row in master['sheets']['Fotos']['rows'][1:]:
                if not row or not row[0]:
                    continue
                path = (root / row[2]).resolve(strict=True)
                if not path.is_relative_to(root):
                    raise ValueError('Master photo path leaves input directory.')
                records.append({'item_id': row[0], 'file': row[2], 'sha256': digest(path)})
            save_new(args.out, {'schema_version': 1, 'master_fingerprint': master['fingerprint'], 'photos': records})
            print(f'Registered {len(records)} existing photos. No online changes.')
        elif args.command == 'plan':
            registry = {'photos': [photo for path in args.registry for photo in load(path)['photos']]}
            plan = make_plan(load(args.manifest), load(args.batch), load(args.master),
                             registry)
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=False)
            save_new(out / 'append-plan.json', plan)
            for entry in plan['appends']:
                with (out / f"{entry['sheet']}.csv").open('x', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(HEADERS[entry['sheet']])
                    writer.writerows([[csv_safe(v) for v in row] for row in entry['values']])
            print(f"Planned {len(plan['allocated'])} new items; skipped {len(plan['skipped'])} existing items. No writes to Google Sheets.")
        elif args.command == 'verify-applied':
            plan, master = load(args.plan), load(args.master)
            verify_applied(plan, master)
            save_new(args.receipt, {'batch_id': plan['batch_id'], 'master_fingerprint': master['fingerprint'],
                                    'photos': plan['registry_additions']})
            print('Verified exact appended cells and summary formulas; receipt saved.')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
