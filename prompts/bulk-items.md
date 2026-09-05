# Bulk resale batch prompt

Copy this prompt into a new task opened in this repository. Replace the bracketed inputs.

---

Process a new batch of items for Vinted and Wallapop using this repository.

**Inputs**

- Photo folder: `[absolute path]`
- Batch name: `[YYYY-MM-DD-short-name]`
- Mode: `[prepare / append]` (default: prepare)
- Master inventory: use `config.local.json`; if missing, I will provide the existing sheet link.
- Market/language/currency: Spain / Spanish / EUR unless I specify otherwise.
- Seller notes: `[known sizes, flaws, condition, included accessories, urgency; optional]`

Read `AGENTS.md` and the repository documentation. Use the existing master inventory
as the source of truth. Inspect its current tabs, IDs, headers and user edits before
allocating IDs. Keep the same Google Sheet and preserve existing rows, sales data,
listing links, formulas and custom columns.

Index all input photos with the local scripts. Review all contact sheets and enlarge
labels and defect photos as needed. Group photos by physical item, accounting for every
file. Check filenames and saved hashes against previous batches. Flag uncertain visual
duplicates or retaken photos instead of creating another item automatically.

For each new item, identify what the photos actually establish: item type, brand,
label size, color, visible condition and defects. Record unknowns explicitly. Do not
invent material, measurements, authenticity, original price or condition claims.

Research useful resale comparisons, preferably the same model, size and condition
in Spain/EUR. Record URLs, prices, currency, date checked, asking/sold/retail status,
and differences. Recommend a Vinted asking price, a Wallapop asking price and a
negotiation range. Explain estimates honestly when direct evidence is unavailable.

Write a Spanish title of at most 50 characters and a concise Spanish description
for both platforms. Describe known flaws and included contents accurately. Keep
seller questions separate from listing copy. Select a main photo and retain the
photo-to-item mapping.

Populate and validate `review.json`, then produce an append plan using a fresh
master snapshot and the local hash registries/verified receipts. Allocate IDs after
the highest current ID. Never restart at V01 or assume the next ID is V39.

In **prepare** mode, deliver the reviewed plan and CSV files without changing the
master. In **append** mode, apply the scoped new rows to the existing master through
the connected Sheets tools after rechecking that it has not changed. Preserve formatting
and custom columns; extend filters and summaries. Re-read the result, verify exact
rows and totals, and save a receipt. If access is unavailable, finish the local plan
and state what is missing. Do not claim a live update.

Report new/skipped item counts, suggested asking total, estimated proceeds range,
the master link if updated, and unresolved details. Do not add the two platforms'
totals together. Do not publish marketplace listings as part of this prompt.

---

For a later publication task, explicitly name the reviewed item IDs and platform,
and request publication. The preparation CLI itself has no marketplace uploader.
