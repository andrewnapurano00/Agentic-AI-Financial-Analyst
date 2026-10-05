# Deep Research in the main app

> The original Deep Research workspace remains the stable V1 workflow. **Deep Research V2 · Cost Pilot** is isolated in its own navigation entry and session history so lighter-model experiments cannot change or overwrite V1 results.

## V2 cost pilot

### Recovery and generation controls (AAFA-2)

V2 distinguishes completed reports, unresolved review issues, pending review, incomplete generation, and saved evidence. Warnings and evidence gaps remain visible. **Retry report writing** uses saved evidence; **Retry review** reuses the saved draft. **Generate report from saved evidence** completes an evidence-only run. Recovery preserves the original routes, budget, Ollama URL, history and diagnostics. Retries require an explicit click; ordinary reruns and downloads make no model calls.

Evidence-only mode includes collection, planning and targeted investigation, but no report writing or decision. Models are constructed only when their stage is invoked; missing required provider settings receive a safe stage-specific message. Resume paths do not construct collection tools. V2 uses compact company-count-aware prompts and minimal reasoning for supported GPT-5 planning/drafting/review stages, within the existing token caps. V1's long-form prompt and generation defaults remain unchanged. Completion limits cover reasoning as well as visible output; the new prompt targets are not a live quality or savings benchmark.

Optional quick decisions and committees run only after a completed report is saved and selected. Their errors do not change the research result; **Retry decision** retries that stage alone. After report recovery, a requested decision requires a separate **Run saved decision stage** click. Reports with unresolved review issues require explicit finalization with caveats before a decision is eligible. Failed requests with unavailable usage reserve projected cost for retry budgeting; estimates remain labelled, and unknown-price models are not a universal hard-dollar guarantee. Blocked stages record diagnostics without being counted as model calls. Mechanical report checks run again after review patches.

Saved-result lookup includes runtime/decision options and allowlisted saved app context; changing those inputs cannot silently reuse incompatible results. It still does not automatically refresh live provider evidence. Use **Force fresh research** when new evidence is required. Download controls do not rerun the workflow. History labels use stable creation times; the current status is displayed separately.

Offline V2 recovery/interaction coverage lives in `tests/test_deep_research_v2_recovery.py`. Live model/provider quality and the original AAFA-1 generation trigger remain unverified.

V2 adds Economy, Balanced, and Maximum quality profiles; stage-specific OpenAI/Groq/Ollama routing; reduced report and evidence limits; deterministic report validation; optional interpretive review; compact quick-decision and CrewAI paths; exact-result reuse; stop-after-evidence/later-generation controls; fixed evaluation cases; and per-stage/session token, latency, and estimated-cost diagnostics. Groq and Ollama failures are surfaced and never silently rerouted. The final report and committee lead stay on the configured hosted OpenAI model until the evaluation set supports changing that policy.

Launch the existing app with `streamlit run app.py`, then open **Deep Research**.
Install `requirements.txt` if needed; the tab uses Streamlit 1.61 or newer to
retain the selected research view across reruns.
The integrated implementation lives in `src/langgraphagenticai/deep_research/`
and uses the
plan → investigate → write approach with the main app's models, tools, and data.
It does not require Gradio, the Agents SDK, email delivery, or a second app server.

## Configuration

Use the sidebar, the root `.env`, or Streamlit secrets:

```dotenv
OPENAI_API_KEY=your-key
FMP_API_KEY=your-key
SERPER_API_KEY=your-key
# Optional: existing finance-tool news capabilities
MARKETAUX_API_KEY=your-key
```

Research uses the model selected in the sidebar. Serper is used for recent news
and additional web discovery via its [search API](https://serper.dev/).
Missing keys and provider coverage are reported as data gaps. OpenAI is required
by the main app; FMP is needed for fresh financial and technical analysis.

If your Python environment reports `CERTIFICATE_VERIFY_FAILED` (for example,
behind a corporate HTTPS proxy), set `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE`
to your organization's trusted PEM certificate bundle before starting Streamlit.
Keep TLS verification enabled. These settings apply to the existing app's API
connections as well as Deep Research.

## Workflow

1. Enter one to four tickers, or import the equity report's tickers or the screener's
   top results. Set a question, horizon, annual/quarterly statements, and news window.
2. Choose whether to include saved app data and Serper research. Start the run explicitly.
3. The collector requests profile, quote, five statement periods, TTM ratios/metrics,
   analyst estimates/targets, and approximately 18 months of prices for every company.
4. It computes SMA 20/50/200, Wilder RSI 14, MACD, price returns, volatility and
   drawdown where enough observations exist. Each dataset retains its date and price basis.
5. A research planner selects targeted follow-ups from the existing finance-tool
   registry, including earnings transcripts, valuation, calendars, peers and ESG.
   Standard permits up to four additional tool calls; Extended permits up to eight.
   These are tool-call limits, not underlying API-request limits: some tools bundle requests.
   Additional investigations have a cumulative 60-second FMP request budget each.
6. Serper performs one recent-news query per company and up to one additional web
   query per company. Results are explicitly labelled as snippets, not full articles.
7. The writer produces a polished executive thesis, a dedicated forward-estimates
   and valuation section, comparisons, assumptions/scenarios, counterarguments,
   risk and monitoring criteria. The saved audit record retains evidence IDs for
   validation, while the executive view and PDF omit those internal references.
   Inspect the raw sources under **Sources & evidence**. Inline citation checking
   detects missing/unknown IDs; it does not prove that every interpretation is correct.
8. A second model pass returns targeted corrections for arithmetic, directional
   growth claims, citations and unsupported targets. Corrections must match unique
   passages exactly; invalid corrections cannot overwrite the draft. Like-for-like
   financial growth is calculated in Python and provided to both passes. This
   improves checking but does not guarantee that every model claim is correct.

## Performance and recovery

- Model packets contain selected financial fields and bounded, question-weighted
  evidence excerpts rather than repeatedly serializing full raw datasets. Original
  evidence remains available in the JSON download. Standard targets 1,000–1,400
  words; Extended targets 1,600–2,000 words.
- The correction pass receives evidence cited by the draft, calculated financial
  trends, unavailable-data records, and the compact comparison table. It does not
  resend the entire writer packet. Serper results are grouped by query and transcript
  excerpts are bounded before synthesis.
- When GPT-5 writes the memo, GPT-5 Mini performs planning and correction. The run
  details record input, cached-input, output, and reasoning tokens when the provider
  returns them. The result header shows an estimated OpenAI model cost; it excludes
  FMP and Serper charges and uses a text-size fallback when provider usage is absent.
- GPT-5, GPT-5 mini and GPT-5 nano use minimal reasoning for structured tool selection
  and correction passes, and low reasoning for writing the analysis, with output budgets that include
  reasoning tokens. The selected model is retained. See the official
  [GPT-5 model documentation](https://developers.openai.com/api/docs/models/gpt-5).
- News searches run concurrently across companies. Targeted web and finance
  investigations share a bounded worker pool. Already-covered core tools are
  omitted from the planner's catalog.
- Draft text streams into the page. Provider evidence, partial text and completed
  drafts are checkpointed in the session before the next stage runs.
- If writing fails, **Retry report writing** uses saved evidence. If review fails,
  the draft stays visible with a pending label and **Retry review** runs only the
  correction pass. Failed model requests are not silently repeated by the SDK.
- A completed review that flags unresolved evidence issues has its own status.
  It shows the findings instead of offering retries that cannot fill source gaps.
- Research controls rerun their own Streamlit fragment. Report views are rendered
  on demand, and only the selected raw evidence record is rendered.
- **Research notebook → Run details** records model-stage duration, input size,
  and safe error categories to distinguish timeouts from quota or access errors.

## Shared data and retention

The bridge reads explicit result fields from the equity report, portfolio manager,
stock screener and portfolio optimizer. It filters company rows to selected tickers
where ticker columns are available, includes portfolio-level context, and records
the saved result's original timestamp. It never dumps the whole session or keys.
Generate results in those tabs first to make them available. Old session results
without timestamps are labelled as having unknown freshness.

Research history retains the latest five runs in the current Streamlit session.
Download a formatted executive PDF, clean Markdown, JSON (including the audited
report, plan, and source data), or comparison CSV for persistence. Follow-ups use
the saved evidence only.
If synthesis fails, **Retry report writing** reuses collected data without fetching
it again. A pending review can be retried without rewriting the draft. A new run
refreshes provider data; saved context retains its original dates.

## Validation

Use the project's installed Python environment and pytest so both pytest-style and unittest-style cases are collected:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -m pytest tests/test_deep_research.py tests/test_deep_research_recovery.py tests/test_deep_research_ui.py tests/test_deep_research_v2.py -q
```

Tests use synthetic data and mocked provider/model responses; they do not consume API credits. See [PLAN.md](PLAN.md#verification-ledger) for the current inventory and limits. V2 helper tests and fixture presence do not establish end-to-end quality or achieved savings.


### V2 quarterly-derived TTM (2026-10-03)

V2 now collects up to eight quarterly income, cash-flow and balance-sheet statements through the shared FMP REST transport. It sums four consecutive, unique fiscal quarters for TTM flows, uses the matched end balance snapshot, and calculates supported margins and valuation ratios with explicit currency/window checks. Annual selections still collect annual history for CAGR. No dedicated TTM endpoint or TTM-backed investigation bundle is used in V2; V1 retains its existing behavior.

Sources retain fiscal quarters, dates, reporting currency, retrieval time, calculation formulas and missing-data limitations. Market-cap valuation requires matching known quote/report currency and positive denominators. Simplified EV subtracts cash equivalents and excludes preferred/minority interests; shares/EPS are not summed and unsupported provider formulas remain unavailable. Invalid or ambiguous quarters leave the affected TTM dataset missing while successful datasets survive.

The cache key includes the quarterly methodology version. Earlier saved runs remain readable; recovery from their earlier financial evidence requires an explicit legacy-evidence acknowledgment. Start fresh research to obtain the quarterly-derived basis. All saved cross-workspace app packets are excluded from new V2 collection to prevent older provider TTM facts overriding calculated evidence. This change does not establish live provider entitlement or measured cost savings.

Review corrections (2026-10-03): prior-TTM growth requires eight consecutive quarters with one security and currency, including the boundary between current and prior windows; invalid prior history preserves current TTM. Quote/profile security identities must match the requested ticker. Calculated ROE/ROA use TTM net income divided by the average of positive matched end and same-quarter prior-year equity/assets, with the balance dates and formula retained; this is a two-snapshot average, not a provider-equivalent quarterly average. ROIC and per-share provider formulas remain unavailable.

### Saved V2 generation timestamp (AAFA-5)

`result_generated_at` records explicit V2 research or recovery completion in timezone-aware UTC, separately from the run start (`created_at`), stage updates (`updated_at`) and evidence dates. The result panel shows **Saved result generated**, UTC time and age in minutes, hours or days. Evidence-only and incomplete returned results also receive this operation timestamp; it does not mean that a report is complete. Optional decisions and finalization preserve it, as do history selection, cache reuse and ordinary reruns. Missing, malformed or timezone-naive legacy timestamps show unavailable; future timestamps disclose a clock mismatch. No date is backfilled and no provider/model call is triggered by the display.

### Serper evidence coverage delivery (2026-10-04)

V1 and V2 request up to five Serper news results per company when news is enabled; planner-requested web evidence uses the separate search endpoint. The key remains in the HTTP header. Successful evidence retains the transport retrieval timestamp separately from each article's provider-supplied publication date. Non-list news/search collections return structured missing evidence instead of stopping financial research; malformed rows are skipped. Saved coverage captions disclose requested lookback, usable result count, companies covered, and available UTC retrieval dates. Missing and partial news are explicit. Saved reuse and report recovery preserve the original evidence without recollection; fresh research is required to refresh news.

Offline regression sources: `tests/test_serper_deep_research.py` exercises real V1/V2 factories and Serper transport with synthetic HTTP/model/financial boundaries, including disabled news, partial HTTP failure, invalid collections, source fields and saved report recovery. No live provider entitlement or publication-age verification is established by these tests.

### Serper follow-up correction (2026-10-04)

The user reported live AAPL and MSFT news evidence saying ?No matching search results returned,? alongside two separate missing investigation records. No live reproduction was authorized or performed. The earlier company-news query appended many topic words, which may restrict matching; that is a hypothesis, not an established live root cause. Company news now queries only company name plus ticker (ticker alone if the name is unavailable), preserving the same news endpoint, requested lookback, five-result cap, bounded timeouts and include-news gate. No additional requests or web fallback were introduced. The adapter now distinguishes a genuinely empty collection from a missing expected response collection and a nonempty collection whose rows lack usable safe links. Provider/model failures in investigation remain separate evidence gaps.

Previously saved results are preserved, including their original news gaps. Select **Force fresh research** in V2, or start a new V1 research run, to apply the new query; reopening or reusing a saved result does not silently refresh news or incur calls. Offline tests verify exact company/ticker and ticker-only queries and the three response diagnostics. These checks cannot establish live news coverage, entitlement or the cause of the reported empty responses.
