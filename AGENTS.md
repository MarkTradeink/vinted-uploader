# Working on this repository

Use this repository to prepare bulk resale listings and maintain the owner's
existing master spreadsheet. Read `config.local.json`, `prompts/bulk-items.md`,
`docs/master-sheet.md`, and `docs/data-contract.md` before a batch.

## Inventory workflow

- Keep photos and actual inventory data in ignored local directories. Never commit
  personal config, a Google Sheets identifier/link, photo hashes, exports or credentials.
- Read the latest master before allocating IDs. The baseline XLSX and registry are
  historical. Preserve existing item IDs, user edits, extra columns, listing URLs,
  sale prices and statuses. Do not recreate the master as a new spreadsheet.
- Use `prepare` to index all photos. View all contact sheets and inspect original
  labels/defects as needed. Visually group photos into actual items, never solely
  by elapsed time. Record every photo once or explicitly exclude it with a reason.
- Do not infer authenticity, materials, dimensions, sizes or pristine condition
  from brand appearance. Separate observation from uncertainty. Read labels exactly.
- Research comparable asking prices in Spain/EUR, favor matching model and condition,
  and disclose differences. Distinguish asking, sold and retail prices. Label an
  estimate when no suitable comparable is available. Do not invent links or use
  universal brand multipliers/confidence scores as evidence.
- Draft Spanish titles (our shared conservative limit is 50 characters) and concise
  descriptions valid for both platforms. Include known defects in public copy.
  Put unresolved details in `confirm`; do not publish items with unresolved essentials.
- Use the applicable spreadsheet skill for artifact authoring or connected Google
  Sheets editing. The CLI reads XLSX and produces plans/CSVs; it does not author XLSX.
- A request to append to the master authorizes the scoped additions. Prepare and
  verify them, then proceed without redundant confirmation. Publication to Vinted
  or Wallapop requires an explicit user request covering those items; a spreadsheet
  append is not marketplace publication permission.
- Before applying a plan, re-read the relevant master values/formulas. A fingerprint
  documents the baseline but is not a lock. If it changed, rebuild the plan. Ensure
  target cells are empty, use RAW literal values, and apply formula updates separately.
- After updating, re-read the cells, check totals/filter ranges and inspect layout.
  Save a verified receipt; do not claim an upload or a Google update without evidence.
- If Sheets access is unavailable, finish the local reviewed append plan and explain
  the access requirement. Do not silently replace the master or fabricate a live read.

## Code changes

Run `python -m unittest discover -s tests -v`. Add meaningful tests when changing
deduplication, ID allocation, photo coverage or preservation behavior. Keep scripts
portable; don't hardcode desktop runtime paths. Avoid live credentials in CI.
