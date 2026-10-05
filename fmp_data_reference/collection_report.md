# FMP collection report

Generated UTC: 2026-10-03T05:10:35.257718+00:00

## Coverage totals

- Workbook API references inventoried and tracked: **259 / 259**, across all five workbook tabs.
- Collection cases (API ID × ticker/input × request variant): **1816**.
- API references with nonempty actual parseable samples: **218**.
- API references with nonempty samples for all 11 sector stocks: **99**.
- Field/path dictionary entries: **17314** (17228 observed live; 86 workbook-only).
- Original complete/bounded raw bodies with validated SHA-256 metadata: **1631**.
- Persisted request attempts across smoke/full/resume/selected runs: **1631** (cache hits do not count).

| Case status | Count |
| --- | --- |
| api_error | 1 |
| bounded_download | 17 |
| empty | 18 |
| not_found | 11 |
| not_present_in_bounded_bulk | 4 |
| restricted | 283 |
| success | 1467 |
| success_non_json | 15 |

Counts include request variants and local bulk extractions, not just unique endpoints or network calls. A success row is not a universal entitlement or quality claim. `empty` may represent legitimate absence; `not_present_in_bounded_bulk` does not establish provider noncoverage.

## Source and mapping verification

The available workbook lacked the requested `(1)` suffix; the project workbook with the same base title was used. All API IDs and original references were retained. Current route facts were extracted from the [official FMP catalogue](https://site.financialmodelingprep.com/developer/docs). Direct requests to the documentation site returned HTTP 403; web access supplied the official catalogue. The catalogue proves listed routes/example parameter names, not all optional/required parameter rules or exact legacy equivalence. Inventory notes preserve narrower/changed mappings. Unmapped original HTTP routes were live-tested rather than assumed deprecated. Three WebSocket references received separate bounded live probes using official legacy protocols; all returned entitlement restrictions. Original key-free server responses were retained.

API authorization used the documented header form. No configured key was persisted. No application files, dependencies, databases or configuration were modified.

## Sampling, observed schemas and interpretation limits

Time-series projections aim for five returned records; core statements request five annual and eight quarterly records. The collector preserves complete raw response bytes where within the 3 MiB limit, and explicitly labels bounded prefixes otherwise. Original CSV strings are not coerced into numbers/nulls. Binary spreadsheets remain actual raw responses with no invented JSON schema. JSON array samples are recursively limited; nested fields/values remain unchanged. Request/cache metadata can be shared among workbook IDs with equivalent requests.

Quarterly key-metrics/ratios were restricted by subscription. Annual variants are attempted separately and prior quarter restriction rows retained in current coverage. Different request controls and variants are separate cases. Some documented/example historical years and filer inputs yield older records; retrieval time is not the data date. Full recent-history completeness is not claimed.

Definitions/units are inferred or unknown unless supported explicitly. Path/type schemas are observed unions; no universal requiredness/non-nullability claim is made. Parent-object missing counts and sector differences reflect only collected bounded records. Monetary scaling, cross-currency joins, exact provider formulas, ratio-percent scaling and price adjustments require further verification. CIK/CUSIP/ISIN strings remain uncoerced. No total-return or application normalization is performed.

Bulk partition/pagination is capped at one, so not every selected stock necessarily appears. No unbounded bulk/history/WebSocket download is attempted. Account restrictions, unsupported controls and old legacy response differences remain visible below and in coverage.

## Restrictions, empty results, partial coverage and failures

| API ID | Case statuses | Nonempty sector stock samples |
| --- | --- | --- |
| FMP-004 | {"empty": 3, "success": 9} | 8 / 11 |
| FMP-008 | {"bounded_download": 1} | 0 / 11 |
| FMP-010 | {"bounded_download": 1} | 0 / 11 |
| FMP-012 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-014 | {"empty": 1} | 0 / 11 |
| FMP-016 | {"bounded_download": 1, "restricted": 1} | 0 / 11 |
| FMP-019 | {"restricted": 5, "success": 17} | 11 / 11 |
| FMP-020 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-021 | {"empty": 6, "success": 5} | 5 / 11 |
| FMP-033 | {"not_found": 11, "success_non_json": 11} | 0 / 11 |
| FMP-049 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-053 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-054 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-058 | {"bounded_download": 1} | 0 / 11 |
| FMP-072 | {"bounded_download": 2, "success": 9} | 9 / 11 |
| FMP-073 | {"bounded_download": 7, "success_non_json": 4} | 0 / 11 |
| FMP-074 | {"restricted": 11, "success": 22} | 11 / 11 |
| FMP-076 | {"restricted": 11, "success": 22} | 11 / 11 |
| FMP-095 | {"api_error": 1} | 0 / 11 |
| FMP-099 | {"bounded_download": 1} | 0 / 11 |
| FMP-106 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-107 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-111 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-112 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-118 | {"empty": 2, "success": 9} | 9 / 11 |
| FMP-127 | {"empty": 1, "success": 10} | 10 / 11 |
| FMP-129 | {"empty": 1, "success": 10} | 10 / 11 |
| FMP-130 | {"bounded_download": 1} | 0 / 11 |
| FMP-134 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-146 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-147 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-148 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-152 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-153 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-154 | {"empty": 1, "restricted": 1} | 0 / 11 |
| FMP-155 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-157 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-158 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-159 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-164 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-172 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-173 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-174 | {"bounded_download": 1, "restricted": 1} | 0 / 11 |
| FMP-175 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-176 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-177 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-178 | {"restricted": 1} | 0 / 11 |
| FMP-179 | {"restricted": 2} | 0 / 11 |
| FMP-180 | {"restricted": 1} | 0 / 11 |
| FMP-181 | {"restricted": 1} | 0 / 11 |
| FMP-182 | {"restricted": 2} | 0 / 11 |
| FMP-183 | {"restricted": 2} | 0 / 11 |
| FMP-184 | {"restricted": 22} | 0 / 11 |
| FMP-185 | {"restricted": 11} | 0 / 11 |
| FMP-186 | {"restricted": 2} | 0 / 11 |
| FMP-187 | {"restricted": 2} | 0 / 11 |
| FMP-188 | {"restricted": 11} | 0 / 11 |
| FMP-189 | {"restricted": 2} | 0 / 11 |
| FMP-197 | {"empty": 1} | 0 / 11 |
| FMP-213 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-218 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-223 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-227 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-228 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-229 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-230 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-231 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-232 | {"restricted": 1, "success": 1} | 0 / 11 |
| FMP-233 | {"restricted": 11, "success": 22} | 11 / 11 |
| FMP-234 | {"empty": 2, "restricted": 11, "success": 20} | 10 / 11 |
| FMP-235 | {"restricted": 11} | 0 / 11 |
| FMP-236 | {"restricted": 1} | 0 / 11 |
| FMP-237 | {"restricted": 1} | 0 / 11 |
| FMP-238 | {"restricted": 11, "success": 11} | 11 / 11 |
| FMP-239 | {"bounded_download": 1, "not_present_in_bounded_bulk": 4, "restricted": 1, "success": 7} | 7 / 11 |
| FMP-240 | {"restricted": 2} | 0 / 11 |
| FMP-241 | {"restricted": 2} | 0 / 11 |
| FMP-242 | {"restricted": 2} | 0 / 11 |
| FMP-243 | {"restricted": 1} | 0 / 11 |
| FMP-244 | {"restricted": 1} | 0 / 11 |
| FMP-245 | {"restricted": 2} | 0 / 11 |
| FMP-246 | {"restricted": 1} | 0 / 11 |
| FMP-247 | {"restricted": 2} | 0 / 11 |
| FMP-248 | {"restricted": 2} | 0 / 11 |
| FMP-249 | {"restricted": 2} | 0 / 11 |
| FMP-250 | {"restricted": 2} | 0 / 11 |
| FMP-251 | {"restricted": 2} | 0 / 11 |
| FMP-252 | {"restricted": 2} | 0 / 11 |
| FMP-253 | {"restricted": 1} | 0 / 11 |
| FMP-254 | {"restricted": 2} | 0 / 11 |
| FMP-255 | {"restricted": 2} | 0 / 11 |
| FMP-256 | {"restricted": 2} | 0 / 11 |
| FMP-257 | {"restricted": 1} | 0 / 11 |
| FMP-258 | {"restricted": 1} | 0 / 11 |
| FMP-259 | {"restricted": 1} | 0 / 11 |

The 11-stock denominator applies only to stock-specific or local bulk extraction cases; market-wide, macroeconomic, ETF, forex, crypto and other alternative-input APIs do not require 11 independent stock requests. See per-case applicability notes.

## Verification and recovery

The collector first completed a small profile/quote/income-statement/Treasury smoke test, then proceeded through the inventory. A nonstandard spreadsheet/CSV response stopped one run; the parser was corrected to separate binary responses and use bounded CSV field sizes. Cached requests were reused on resume, preserving earlier raw/samples.

Four offline unittest checks passed: preservation of zero/null/leading-zero IDs/nesting; refusal to write outside the reference root; HTTP-200 API-error detection and configured-key reflection quarantine; bounded transient retries and cache reuse. Scripts compile in memory. Integrity checks verify all 259 IDs/schema files, local sample/raw paths, array limits, raw hashes and absence of the configured credential. No app/full-suite/browser checks were performed because this task changes only the new reference folder.

## Unresolved questions and future use

- Exhaustive official required/optional parameter rules and field-level provider definitions remain unverified where not present in accessible official material; successful requests alone do not establish them.
- Which missing symbols are outside the bounded bulk prefix/partition versus unavailable? Expand only explicitly chosen partitions with the same safeguards.
- Which premium/quarterly parameters or WebSocket services are included in a different entitlement? Do not infer availability from another endpoint’s success.
- What are the exact monetary/ratio scaling, adjusted-price methodology, and fiscal-period alignment for each future application use? Check before calculation.
- Older inputs should be refreshed with documented recent report/filer dates when needed; all saved dates and successful controls are evidence, not a live guarantee.

For future work, tell Codex: **Consult `fmp_data_reference/context_index.md` before planning FMP sourcing or validation; inspect the exact coverage, dictionary paths and raw/sample evidence, and do not change the application unless separately requested.**


## Additional route/protocol verification

- Official legacy company-image documentation corrected the workbook’s missing `.png` suffix. All 11 actual logos were collected as binary samples, retaining the original failed-route cases.
- Complete binary samples cover 2 API references; combined nonempty JSON or complete binary coverage is **220 / 259**.
- Stock, crypto and forex WebSocket probes each used one connection with documented login/subscription frames. All three were restricted; no market ticks were fabricated. The stock denial is recorded for all 11 requested symbols, with the shared received server frame. Outbound login payloads were never persisted.
- Official protocol sources: [stock](https://site.financialmodelingprep.com/developer/docs/websocket-api), [crypto](https://site.financialmodelingprep.com/developer/docs/crypto-websocket), [forex](https://site.financialmodelingprep.com/developer/docs/forex-websocket).
- Reusable collection enforces bulk-specific cooldowns after official FAQ verification. Initial general-rate bulk requests and all restrictions remain recorded.
- Coverage reconciliation preserves distinct endpoints/controls and corrects early global RSS ticker aliases and redundant batch postprocessing. Raw response bodies were not changed; corrections are recorded in `documentation/processing_notes.json`.
- Request-attempt total above counts REST requests. Three additional bounded WebSocket connection/protocol probes are recorded separately.

## Environment and final scope checks

Verification used the existing Python 3.12.7 environment, requests 2.34.2 and openpyxl 3.1.5; nothing was installed. All reference scripts compiled in memory, four offline checks passed, and the query helper returned a live-observed financial field. Git status retained the original user changes and added only `fmp_data_reference/` for this task. Public certificate resources and every temporary file were confined to this folder.

Complete ZIP/spreadsheet archives were inspected for the configured credential without extraction to disk. Bounded incomplete ZIP prefixes cannot be fully inspected as archives; that limitation is recorded in `integrity_verification.json`. Plain-byte checks covered every saved file. No configured credential was found.

The observed dictionary/schema union considers all 2132 historical collected JSON sample files. Counts may include repeated cached projections and are not independent statistical observations. Current coverage provides the retrieval/source controls for choosing dated evidence.
