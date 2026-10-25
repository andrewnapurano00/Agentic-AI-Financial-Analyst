# Data Validation workspace

Date: 2026-10-24. Working-tree delivery, not a publication or deployment.

## User workflow

Data Validation is an additional sidebar utility alongside the retained nine research workspaces. Select a provider and registered endpoint, enter a ticker (or a search query), review permitted JSON parameters and click Fetch data. Market-wide operations visibly ignore the ticker. Inspect a table, JSON, original request metadata, returned symbols and retrieval time. Local field filtering, tabs, navigation and JSON downloads do not fetch again. A failed request retains the previous successful response and its original request; edited inputs show a mismatch notice. Different provider credentials suppress prior saved data/download until a new fetch.

## Design note: isolated diagnostics, not a financial handoff

`providers/data_validation_catalog.py` is a source-backed allowlist: 44 REST FMP routes, 65 retained read-only FMP MCP wrappers, two Marketaux operations, two Serper adapters and two Yahoo operations (115 total). MCP availability does not imply that every wrapper is currently exercised by a sidebar workflow or entitled by a subscription. Literal REST and MCP wrapper coverage have source-based regression checks. Model APIs, arbitrary HTTP destinations, dynamic remote tool execution and publisher article scraping are outside this checker.

`providers/data_validation.py` owns validation, routing and safe output. REST uses shared FMP transport with its existing bounded retries and local credential limits; MCP uses registered wrapper methods with zero checker retries and a 30-second operation timeout. Marketaux uses its existing host and key with connect/read timeout and redirects disabled. Serper uses the shared client and bounded limits. Yahoo uses the same download/info adapter family with a session timeout; downloads explicitly use auto_adjust=True, daily or five-minute intervals, and one symbol. Yahoo and MCP adapters may perform multiple underlying protocol requests; one Fetch means one selected operation, not necessarily one HTTP request. No automatic fallback or endpoint sweep is introduced.

Only endpoint-specific parameter names and scalar values are allowed; credentials/tickers cannot be overridden through JSON. Ranges, dates, periods and sample sizes are bounded. Historical controls are request windows, not assertions of complete observed coverage. Registry presence and retrieval success do not establish financial accuracy, period/currency compatibility, price-adjustment meaning, freshness or account entitlement.

Credential-like fields, configured key values and unsafe link forms are removed before session display/export. The retained body is limited to 1000 entries per list/dictionary, depth/node/text/serialized size bounds; oversized bodies receive a preview-limit disclosure. Non-finite numbers serialize as null; actual numeric zero remains zero and provider null remains null. Table preview is limited to 500 records and may flatten nested fields; JSON retains the bounded structure. JSON download is the same sanitized saved packet, not a fresh request. HTTP errors use safe categorical messages; provider error envelopes remain inspectable only after sanitization. Results stay session-backed and are not accepted as validated company financial packets in another workspace.

`ui/data_validation_tab.py` owns controls and saved display state. `main.py` routes this utility before the command bar/market ribbon so merely opening it cannot refresh unrelated quotes or enter a model workflow. Shared sidebar and shell header gain the utility entry; original research navigation and saved results remain.

## Verification and remaining limits

Commands/results are recorded in PLAN. Focused contracts cover the catalog, destinations, input bounds, source coverage, provider routing, redaction, size limits, credentials, errors, explicit Fetch, credential changes and saved-state recovery. Guarded browser exercised the actual new navigation route, success, table/JSON/request inspection, failed access recovery and laptop/mobile layout. The response file was served with HTTP 200 and its JSON content validated; native disk-save was canceled by the browser driver and remains unverified. All browser provider data was synthetic; no live account keys/provider/model calls or entitlement/freshness/financial-quality certification. Existing hosted/authentication/dependency/release gates remain open.


## Report and calculation lens

Report / workspace covers all sidebar workspaces, separating the two Deep Research formats and Portfolio Lab's Optimizer/AI Portfolio Manager. Metric / calculation family narrows the endpoint allowlist and provider choices. Thirty maintained family mappings identify display locations, provider fields, calculation/validation rules, fiscal/price basis, source modules and interpretation type. Where this endpoint is used supplies readable reverse usage. A downloadable JSON map carries the same metadata.

Calculation code index parses actual mapped source modules without importing/executing consumers, providers or AI. It lists definitions, current source lines and first docstrings, retaining the last same-name module definition to avoid pointing at overridden legacy functions. Helpers are included and are not asserted to execute for each endpoint.

This is reference-level metric-family coverage, not a complete per-cell runtime lineage system or financial correctness certificate. Provider registration/compatibility is not entitlement or actual invocation. Raw provider response state, credential scoping, exact request details and explicit Fetch remain separate. Report/family/provider reconciliation resets only dependent selection/parameter drafts, preserving saved responses. Filtering, browsing the map/index and downloading metadata make no provider/model calls. Existing retained tools without report-specific mappings remain available through All reports; an unmapped tool is not silently attributed to a research report.
