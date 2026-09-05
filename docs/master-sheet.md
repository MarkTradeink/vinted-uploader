# Extending the master Google Sheet

The master link belongs in ignored `config.local.json`. The spreadsheet ID and a
tab's `gid` are different: use the spreadsheet ID to open the document and inspect
all tabs by their current names. A stored link does not grant connector access.

## Before a batch

1. Open/read the existing Google Sheet through an available authenticated connector.
   When using a spreadsheet skill, follow its native editing/export workflow.
2. Obtain a fresh XLSX export for the read-only `snapshot` command, or construct the
   same snapshot shape from a complete connector read of current values and formulas.
   Do not use the original September workbook as if it were current.
3. Read local registries and all verified receipts. Use repeated `--registry` arguments
   when planning. A missing registry reduces detection to relative filenames.
4. Validate the reviewed batch and build a plan. Resolve inconsistent master IDs,
   changed headers, filename collisions and partial previous uploads before writing.

The snapshot extraction time is not proof of freshness: the user or connector must
have just exported the current document. Fingerprints exclude this timestamp and
represent values/formulas across all exported tabs.

## Apply an authorized append

The CLI never sends Google API requests. In append mode, the assistant applies the
reviewed `append-plan.json` using the connected Google Sheets editing tools:

- Re-read the master immediately before writing. Compare values/formulas or rebuild
  a snapshot and compare `base_fingerprint`. If anything changed, regenerate the plan.
- Verify target ranges are empty. Write each `appends[].values` block to its exact
  range, without its CSV header and using RAW literal text/numeric values.
- Never clear, replace, sort or recreate a populated tab. Preserve additional columns.
  Extend the existing table/filter range and copy formatting into new rows; copy user
  formulas in additional columns only when their intended fill pattern is established.
- Apply `summary_updates` only when the existing formula still equals
  `expected_formula`. Customized summaries are listed in `manual_notes` for review.
- Review static counts/date text in `Guía`, inspect the resulting layout, and preserve
  any user changes. The automated verifier checks data/formulas, not formatting.

Google Sheets connector writes may not be transactional. The fingerprint is a
preflight check, not a lock against concurrent edits. Keep the write/read interval
short. If a write fails partway, inspect the actual rows; do not retry every append
blindly. A mismatch between Precios and Anuncios deliberately blocks a new plan.

Afterward, export/read the master again. `verify-applied` checks exact planned rows
and formula updates before creating a hash receipt. Include that receipt on later
runs. It does not replace the need to inspect filters, formatting and custom columns.

## Without a connector

Complete the local plan. The user can paste each CSV's data rows into the exact
empty destination range, checking numeric prices and literal text. Do not choose an
import mode that replaces a sheet. Apply the summary changes and verify with a new
export. Be explicit that a local file is not an update to the Google Sheet.

## Baseline registration

`register-baseline` associates photos on disk with the IDs in an existing snapshot.
It verifies every referenced file exists and hashes it. It does not upload items or
prove that the snapshot is the current online version. Use it once for a trusted
existing export; retain subsequent `verify-applied` receipts.

```powershell
python -m vinted_batch register-baseline --master .local/master-before.json --photos "C:/Photos/ExistingBatch" --out .local/baseline-registry.json
```
