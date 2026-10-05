# Standalone FMP data reference

This folder holds actual FMP responses, a workbook inventory, observed schemas, and a searchable field dictionary for future data sourcing and validation. It does not implement application changes, update an application database, or establish financial correctness. Collection started October 3, 2026 (America/New_York); each request carries its actual UTC retrieval timestamp. This is a dated reference, not a live source.

Source workbook: `FMP_API_References_and_Example_Schemas.xlsx`, found in the repository root. The requested `(1)` filename was not found in the supplied project; this available workbook has five tabs and 259 API IDs. All five tabs are preserved as records in `documentation/workbook_tabs.json`; workbook-supplied examples are separate from live samples and never passed off as collected data.

## Start here

Read [context_index.md](context_index.md), then [collection_report.md](collection_report.md) and [coverage_matrix.csv](coverage_matrix.csv). The dictionary describes limited observed samples, not universally required fields or provider contracts. Check units, currency, dates, fiscal basis, price adjustments and coverage before future use.

## Folder contents

- `endpoint_inventory.csv`: all workbook API IDs, original routes/examples, current mappings, official sources and mapping caveats.
- `coverage_matrix.csv`: every collection case, ticker/input, variant, result, request controls, dates, counts, and file paths.
- `sector_tickers.csv`: the 11 requested stocks and exact FMP-returned sectors, industries, currencies and identifiers.
- `data_dictionary.csv` / `data_dictionary.md`: searchable and readable field/path definitions with inferred/unknown labels, observed types, examples, null/missing counts, joins and sector differences.
- `schemas/`: one observed path/type union per API ID. These deliberately do not assert universal requiredness/non-nullability.
- `raw/`: original decompressed response bodies and sanitized metadata. `.partial` files are byte-bounded prefixes, never complete-body claims. `request_cache.json` enables resuming without repeat calls.
- `samples/`: actual parsed/extracted responses by API ID, UTC run and ticker/input. These are bounded projections, not fabricated or numerically normalized records.
- `documentation/`: official endpoint facts, all workbook tabs and local diagnostic/certificate resources. Direct HTML fetching returned HTTP 403; the current official catalogue was inspected through web access, and endpoint facts were extracted without copying its explanatory prose.
- `scripts/`: collector, dictionary refresh, offline checks, and integrity verification. No dependency installation is needed with the existing environment.
- `collection_totals.json` / `collection_report.md`: scope, coverage, limitations and verification evidence.

## Collection controls and transformations

REST requests are sequential, defaulting to 0.75 seconds between starts, a 10-second connection timeout, 25-second read timeout, one bounded transient retry, one page/partition and a 3 MiB decompressed download ceiling per request. Following the official FAQ check, reusable scripts additionally enforce 10-second bulk spacing and 60-second profile/ETF-bulk cooldowns; the earlier full pass used the general rate and recorded its outcomes. No unlimited history/bulk download is opened. Use slower rates as required by the account; 429s receive bounded backoff.

`collect_websockets.py` separately probes the three officially documented legacy streams, sequentially, for at most 12 seconds/128 frames/64 KiB per frame and five market records per input, closing each connection afterward. Outbound login payloads are never saved. Lowercase subscription names are documented protocol requirements; returned fields/casing are unchanged. Empty short-window results, entitlement denials and transport failures remain explicit, without fabricated ticks.

JSON response bytes are saved before parsing. Samples retain provider field names, numeric values, strings/leading zeros, nulls and nested structure, while recursively limiting arrays to five records (eight for quarterly statement variants). Annual statement variants request five records. CSV samples retain every original field as a string, including empty strings: CSV does not establish JSON numeric or null types. Binary/text responses stay in raw files. Large truncated JSON arrays contribute only fully parsed records; incomplete records are discarded. Truncated CSV prefixes contribute complete lines only. Byte limits and incomplete coverage remain explicit.

No universal field definitions or scaling are invented. Common financial terms have cautious inferred interpretations; unknown provider formulas remain unknown. Returned currency labels are recorded rather than applied automatically to every field. Candidate joins are inferred and must be checked for identity, period and cardinality. No arithmetic, total-return construction, schema normalization or currency conversion is performed.

Bulk APIs are fetched once per selected documented partition/year/period where practical, with local extraction of the 11 stocks. A missing symbol in a bounded prefix/partition is `not_present_in_bounded_bulk`, not proof the provider lacks it. Non-stock APIs use documented/example inputs; sector stocks are not automatically substituted into ETF/forex/crypto/macroeconomic requests. Historical/example years may be retained where a safe recent input is not established; always inspect data dates.

Mappings verified in the official catalogue establish a documented route, not exact legacy equivalence or account entitlement. Some replacements have narrower/different semantics, recorded in the inventory. Parameters appearing in official endpoint examples are documented; workbook controls and extra sampling limits/date/period controls are labeled separately. A successful live request alone does not establish that every optional control was honored, or a complete required/optional parameter contract.

## Refresh or resume

Use the project's already installed interpreter from the repository root:

```powershell
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/reference.py --smoke
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/reference.py
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/reference.py --legacy-fallback
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/collect_websockets.py
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/refresh_dictionary.py
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/verify_reference.py
```

The collector reads `FMP_API_KEY` from the execution environment, with read-only fallback to the parent `.env` or `.streamlit/secrets.toml`. Set `FMP_API_KEY` locally if unavailable; never paste a key into chat. Requests use the officially documented `apikey` authorization header, not a key-bearing URL. The key is not persisted; reflected credentials are quarantined rather than saved. TLS remains verified, using a public trust bundle derived into this folder from the installed system trust store; no system trust/configuration is modified.

Default reruns reuse cached responses, including recorded restrictions/failures. For selected genuinely fresh requests:

```powershell
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/reference.py --ids FMP-018 FMP-061 --refresh --interval 1.5
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/refresh_dictionary.py
```

Each network collection and extracted sample goes into a fresh UTC run directory. Earlier raw bodies and samples are never overwritten by default. The top-level inventory/dictionary/coverage files are regenerated indexes; all earlier samples remain available, and coverage snapshots are retained by run. Current coverage retains distinct request controls/variants, including unsuccessful current-route and successful legacy-route cases. `--legacy-fallback` selects documented workbook originals for restricted/error cases; the variants/routes remain separate. Dictionary freshness follows the current coverage index, not every historical run. If the workbook is no longer alongside this folder, its preserved tab records allow refresh without it. Script outputs are constrained to this reference root; moving the folder does not authorize writes elsewhere. To add mappings, inspect official documentation first and edit only these reference scripts/catalogue.

Observed schemas/dictionary unions include every saved historical JSON sample, not just the latest projection. Counts may therefore include repeated cached observations; use current coverage timestamps when choosing an evidence file. Search large dictionaries with `scripts/query_reference.py --api FMP-061 --field revenue --limit 5` rather than loading the entire file into a future prompt.

## Future Codex request

> Consult `fmp_data_reference/context_index.md` and its linked inventory, coverage, dictionary and actual samples before planning FMP data changes. Treat this reference as dated evidence; verify current entitlement, field meaning, units and fiscal basis. Do not modify my application unless my new request explicitly authorizes it.

## GitHub source snapshot

Raw response bodies/request caches, scraped HTML diagnostics, and the local Windows CA bundle are excluded from Git. They remain available in the original local collection. The repository includes bounded public-data samples, observed schemas, dictionary, inventories, collection records and scripts. Raw-file links in historical collection records describe local provenance and may not resolve in a fresh checkout. No provider keys are included; recollection is an explicit live operation.
