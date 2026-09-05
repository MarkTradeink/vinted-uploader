# Review data

`prepare` creates `manifest.json` with relative file paths, stable photo IDs for that
scan, dimensions, SHA-256 hashes and decoding errors. It also creates an empty
`review.json`. Fill that file after reviewing the images; it is not an AI classifier.
See `examples/review.json` for a complete fictional item.

Each item has a batch-local `key`, a visually reviewed photo selection, one primary
photo, a shared title/description, label size, visible condition, pending questions,
four numeric EUR prices, pricing basis and rationale, and optional source IDs.
Unknown size should be `Sin confirmar` plus a specific question. `grouping_reviewed`
means the grouping was inspected, not that the item is approved for publication.

Prices must be finite, nonnegative numbers. The negotiation lower bound cannot
exceed the upper bound, and the upper bound cannot exceed either asking price.
Different platform prices are a seller strategy unless evidence demonstrates a
market difference. This tool does not calculate prices from a brand tier.

Each source has its own batch-local ID, URL, reference, numeric low/high prices,
currency, `checked_at` date, `kind` (`asking`, `sold`, or `retail`) and limitations.
Retail is context, not the item's original price. A sold badge is not proof of the
negotiated amount. Record indexed/stale evidence as such. No confidence scores.

`excluded_photos` contains `{ "photo_id": "P0002", "reason": "..." }` entries.
Photo coverage is exhaustive: every manifest photo is assigned once or excluded once.
Never exclude a defect photo simply because it makes the item less attractive.

The master uses the original five tabs: `Guía`, `Precios`, `Anuncios`, `Fotos` and
`Fuentes`. Required header prefixes live in `vinted_batch/master.py`; extra columns
may follow. Header changes require explicit mapping, not silently creating new tabs.
The planner writes only the original columns of newly appended rows.

Item IDs follow V01, V02, …, V100, etc. Source IDs follow S01, S02, … and are allocated
from the current master. `batch_id` and the receipt are local audit information.
Known duplicates are skipped only when core title/description/price data also matches;
different data requires an intentional update. Mixed old/new photo groups stop planning.

CSV strings beginning with formula characters are escaped. JSON row values should be
written as RAW literal values. Summary formula updates are explicit, separate entries.
