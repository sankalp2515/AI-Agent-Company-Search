# Envelope and evidence model

`schemas/envelope.schema.json` describes the public terminal envelope. Every unique supplied nine-digit organisation number receives one result in input order, even when individual sources fail. Run completion is separate from information availability.

Claims have stable IDs keyed by entity, field, value and reporting period. Every available claim links to evidence IDs. Evidence links to preserved source snapshots with requested/final URL, redirects, HTTP status, retrieval time and SHA-256. Locators are JSON pointers, visible-text quotes, HTML selectors/attributes or embedded JSON-LD nodes. The source hash covers exact bytes, not a summary.

Official original-object JSONL frozen registries use `source_row_key` plus a JSON pointer within that entity row. CSV is sniffed for comma or semicolon; dotted BRREG columns are normalized into nested keys. Locator pointers in that case refer to the normalized row, with explicit `snapshot_format: csv` and original organisation row key. The raw original file is preserved and hashed. Supply its actual retrieval timestamp and declare it in the run report.

Missing fields are absent from claims; availability is explicit at family level and selected field level. Financial claims retain original currency, company/group account type and full reporting period. `financial_freshness` compares fetched period end to the registry's latest filing year and warns when the latest filing is not covered.

Refresh compares stable value/period sets. Changed/removed/added claims reference both sides. Previous evidence and snapshot metadata remain in `refresh`; earlier snapshot directories must be retained. Failed, blocked and ambiguous refreshes preserve old supported facts as stale last-known claims, never as newly verified claims.

The viewer only interpolates result values using text nodes. The JSON payload escapes script-breaking angle brackets and source links allow HTTP(S) only. It executes no collected JavaScript.

