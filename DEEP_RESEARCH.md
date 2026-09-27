# Deep Research in the main app

> The original Deep Research workspace remains the stable V1 workflow. **Deep Research V2 · Cost Pilot** is isolated in its own navigation entry and session history so lighter-model experiments cannot change or overwrite V1 results.

## V2 cost pilot

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

Run `python -m unittest discover -s tests -p "test_deep_research*.py"` with the
app's dependencies installed. Tests use synthetic data and mocked provider/model
responses; they do not consume API credits. The main app also has existing pytest tests.
