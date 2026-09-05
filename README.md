# vinted-uploader

Reusable workflow for reviewing batches of photos, preparing Spanish Vinted and
Wallapop listings, and extending one Google Sheets inventory.

The CLI indexes photos, creates contact sheets, validates reviewed item data and
prepares an append plan. The assistant identifies items visually and researches
prices. Google Sheets updates use the connected Sheets tools or a reviewed manual
import. **The scripts do not log into Google or publish marketplace listings.**

## Next batch

Open this repository with your assistant and paste [the bulk prompt](prompts/bulk-items.md).
Fill in the photo folder and choose `prepare` or `append`. The short version is:

> Process the new photos in `<folder>` using `prompts/bulk-items.md` and
> `config.local.json`. Read the latest master inventory, skip existing items,
> visually review each item, research euro prices and write Spanish listings.
> Append the new items to the same master sheet, preserving my edits and sales data.
> Report unresolved details. Do not publish marketplace listings.

`config.local.json` stores the owner's master spreadsheet reference locally and is
ignored by Git. On another machine, copy this file privately or create it from
`config.example.json`. Do not commit it to this public repository.

## Setup

Python 3.11 or newer:

```powershell
python -m pip install -r requirements.txt
python -m vinted_batch --help
python -m unittest discover -s tests -v
```

In the desktop workspace, the assistant can use the bundled Python and Pillow
runtime instead of installing dependencies. HEIC/HEIF decoding additionally needs
`pillow-heif`. Unreadable photos remain visible in the manifest and must be resolved
or explicitly excluded with a reason.

## Local workflow

Run from the repository root. Use a new output directory for each run.

```powershell
python -m vinted_batch prepare "C:/Photos/NewBatch" --out .local/batches/2026-10-01
```

Review the numbered contact sheets and original label/defect photos. Populate
`review.json` using [the example](examples/review.json). Every photo must belong to
one item or have an exclusion reason. Times and folders can help ordering; they do
not prove where one item ends and another begins.

Download a **fresh** XLSX export of the existing master Google Sheet, then:

```powershell
python -m vinted_batch snapshot .local/master-latest.xlsx --out .local/master-before.json
python -m vinted_batch validate --manifest .local/batches/2026-10-01/manifest.json --batch .local/batches/2026-10-01/review.json
python -m vinted_batch plan --manifest .local/batches/2026-10-01/manifest.json --batch .local/batches/2026-10-01/review.json --master .local/master-before.json --registry .local/baseline-registry.json --out .local/plans/2026-10-01
```

Omit `--registry` on first use if no photo hashes have been recorded yet. Repeat
`--registry` for receipts from later batches. Without hashes, duplicate detection
only uses exact relative filenames, not renamed files or visually similar photos.
Hash matching detects byte-identical renamed copies, not resized/re-encoded copies.

The plan contains exact proposed rows for `Precios`, `Anuncios`, `Fotos`, and
`Fuentes`, allocated IDs, summary formula updates and pending manual adjustments.
CSV files are review/import aids; do not replace the master sheets with them.
Read [the master-sheet procedure](docs/master-sheet.md) before applying a plan.

After applying and downloading a new export:

```powershell
python -m vinted_batch snapshot .local/master-after.xlsx --out .local/master-after.json
python -m vinted_batch verify-applied --plan .local/plans/2026-10-01/append-plan.json --master .local/master-after.json --receipt .local/receipts/2026-10-01.json
```

This checks appended cells and proposed summary formulas before recording hashes.
Do not record an append receipt before confirming that Google Sheets contains the rows.

## Files and boundaries

- [AGENTS.md](AGENTS.md): instructions for future assistants.
- [Bulk prompt](prompts/bulk-items.md): reusable task template.
- [Photo guide](docs/photos.md): useful angles, labels and measurements.
- [Data contract](docs/data-contract.md): review fields and pricing evidence.
- [Master-sheet procedure](docs/master-sheet.md): preserving the existing inventory.
- `vinted_batch/`: local scripts; no paid AI API keys, marketplace credentials or n8n dependency.
- `.local/`: private config, batches, snapshots, hash registries and receipts.

The September 2026 baseline contains 38 items and 212 photo files. It is a local
reference, not a substitute for reading the current Google Sheet. IDs always come
from the current master, never from that count.

The former implementation remains recoverable in Git history. Rebuilding this
repository does not modify any previously deployed external n8n workflow.
