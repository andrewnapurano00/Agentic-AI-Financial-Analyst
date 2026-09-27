# TODO: Deep Research Cost Optimization

## Goal

Reduce Deep Research and CrewAI model costs without materially weakening the quality, auditability, or usefulness of investment reports.

## V2 pilot implementation status — 2026-09-27

The roadmap is implemented behind the separate **Deep Research V2 · Cost Pilot** workspace; V1 remains unchanged. The pilot includes cost modes and stage routing, bounded output/context sizes, deterministic validation with conditional interpretive review, compact quick/full decisions, session result reuse and force-refresh, stop-after-evidence/later synthesis, Groq and Ollama light-stage routing, explicit provider failures, per-stage and session cost diagnostics, a run budget guard, and the fixed five-case evaluation fixture in `tests/fixtures/deep_research_v2_eval_cases.json`. CrewAI stage attribution is labeled estimated when CrewAI exposes aggregate rather than per-agent usage. Production-default promotion remains intentionally pending real, paid evaluation runs across the fixture.

## Current cost drivers

- A complete workflow can make at least six model calls:
  1. Research planning
  2. Report drafting
  3. Report review
  4. CrewAI fundamental analysis
  5. CrewAI risk analysis
  6. CrewAI final decision
- CrewAI agents repeatedly receive much of the same research report.
- Standard reports can receive up to 36,000 evidence characters and Extended reports up to 48,000.
- Standard report generation allows up to 4,500 output tokens; Extended allows up to 6,000.
- Review allows up to 3,000 output tokens.
- The cost shown in the Deep Research UI does not include CrewAI committee usage.
- Identical or materially unchanged research can be rerun without a result cache.

## Recommended target architecture

```text
Evidence collection       No LLM
Evidence compression      Python + low-cost model when necessary
Research planning         GPT-5 nano or free/local model
Executive report          GPT-5 mini
Mechanical validation     Python
Interpretive review       GPT-5 nano
CrewAI specialists        GPT-5 nano, Groq free tier, or local model
Final committee decision  GPT-5 mini
```

## Phase 1: Immediate savings

- [ ] Add a Deep Research cost mode selector:
  - Economy
  - Balanced
  - Maximum quality
- [ ] Use stage-specific models instead of one model for the entire workflow.
- [ ] Configure the recommended model routing:

| Mode | Planning | Report | Review | Crew specialists | Crew lead |
|---|---|---|---|---|---|
| Economy | GPT-5 nano | GPT-5 mini | GPT-5 nano | GPT-5 nano | GPT-5 mini |
| Balanced | GPT-5 nano | GPT-5 mini | GPT-5 nano | GPT-5 nano | GPT-5 mini |
| Maximum quality | GPT-5 mini | GPT-5 | GPT-5 mini | GPT-5 mini | GPT-5 |

- [ ] Lower output-token limits:
  - Planning: 500–700
  - Standard report: 1,800–2,200
  - Extended report: 3,000–3,500
  - Review: 1,000–1,500
  - Follow-up: 800–1,200 unless a longer answer is explicitly requested
- [ ] Shorten Standard reports while retaining the executive thesis, material financial trends, valuation, catalysts, risks, and invalidation conditions.
- [ ] Keep CrewAI disabled by default.
- [ ] Add a “Quick decision” option that uses one structured decision call instead of the full three-agent committee.

### Phase 1 acceptance criteria

- Standard Deep Research uses no more than three model calls unless recovery is required.
- Quick decision uses one additional call.
- Full committee remains opt-in.
- The report still includes material dates, currencies, risks, limitations, and source traceability.
- Token and estimated cost tests cover every model stage.

## Phase 2: Reduce prompt size

- [ ] Reduce evidence context limits:
  - Standard report: 18,000–24,000 characters
  - Extended report: 30,000–36,000 characters
  - Review: 10,000–14,000 characters
  - CrewAI decision packet: 8,000–12,000 characters
- [ ] Build a compact decision brief once and share it with CrewAI agents.
- [ ] Do not send the complete report independently to every CrewAI agent.
- [ ] Prioritize these records in model context:
  - Calculated financial trends
  - Valuation snapshot
  - Most recent earnings and guidance
  - Two or three decision-relevant news items per ticker
  - Material catalysts and risks
  - Missing or stale evidence
- [ ] Keep raw provider payloads in the Sources tab but exclude them from prompts unless specifically relevant.
- [ ] Deduplicate repeated metrics, provider aliases, boilerplate, URLs, and metadata before prompt construction.
- [ ] Add a prompt-size diagnostic showing characters and estimated tokens by context category.

### Phase 2 acceptance criteria

- Standard draft input is reduced by at least 40% from the current baseline.
- CrewAI agents receive a compact decision brief rather than the full report.
- Evidence selection remains deterministic and testable.
- Critical evidence IDs remain available for internal review even when omitted from executive presentation.

## Phase 3: Replace LLM checks with Python

- [ ] Move mechanical review rules into deterministic validators:
  - Referenced evidence IDs exist
  - Every selected ticker is discussed
  - Recommendation values are valid
  - Required report sections exist
  - Dates and currencies are present where required
  - Directional claims agree with calculated changes
  - Scenario arithmetic is internally consistent
  - TTM values are not treated as directly comparable growth periods
  - Comparison tables contain expected companies and columns
- [ ] Send only validator failures and genuinely interpretive questions to the review model.
- [ ] Skip the review-model call when all deterministic checks pass and no interpretive review is requested.

### Phase 3 acceptance criteria

- Mechanical errors are detected without consuming model tokens.
- Review prompts contain only the passages and evidence relevant to detected issues.
- Existing recovery and caveat behavior remains intact.

## Phase 4: Cache and reuse results

- [ ] Create a research cache key from:
  - Tickers
  - User question
  - Investment horizon
  - Statement period
  - Research depth
  - Provider-data dates
  - News lookback
  - Model configuration
- [ ] Reuse evidence when only report formatting changes.
- [ ] Reuse the report when neither evidence nor the research request changed.
- [ ] Reuse the CrewAI decision when its source research ID and committee configuration are unchanged.
- [ ] Add “Use saved result” and “Force fresh research” controls.
- [ ] Ensure Streamlit reruns never trigger paid model calls automatically.

### Phase 4 acceptance criteria

- Reopening a completed result incurs no model cost.
- Reformatting or downloading a report incurs no model cost.
- Cache status and source-data age are visible to the user.

## Phase 5: Free and local model support

- [ ] Introduce a provider-neutral LLM factory instead of hardcoding `ChatOpenAI`.
- [ ] Support provider and model selection independently for each stage.
- [ ] Add optional Groq support using the existing `GROQ_API_KEY` and `langchain_groq` dependency.
- [ ] Evaluate Groq free-tier models for:
  - Planning
  - Evidence summarization
  - CrewAI specialist analysis
  - First-pass review
- [ ] Add optional Ollama support for local inference.
- [ ] Evaluate local models for:
  - Classification
  - Evidence selection
  - News summarization
  - Planning
  - Formatting cleanup
- [ ] Keep a stronger hosted model available for final investment synthesis until local-model quality is validated.
- [ ] Add automatic fallback behavior for provider rate limits and unavailable local models.
- [ ] Clearly label local/free model output and its limitations.

### Phase 5 acceptance criteria

- Planning and specialist analysis can run without per-token OpenAI charges.
- Provider failures do not silently switch models or produce incomplete reports.
- Structured-output validation works consistently across providers.
- Financial quality is compared against a fixed evaluation set before changing defaults.

## Phase 6: Cost visibility and controls

- [ ] Include CrewAI usage in total cost reporting.
- [ ] Display cost separately for:
  - Planning
  - Drafting
  - Review
  - Follow-ups
  - CrewAI specialists
  - CrewAI lead
- [ ] Show actual or estimated input, cached-input, output, and reasoning tokens.
- [ ] Add a maximum estimated cost per run.
- [ ] Warn before expensive four-ticker Extended runs.
- [ ] Add a “Stop after evidence collection” option.
- [ ] Add a “Generate report later” action that reuses saved evidence.
- [ ] Add per-session and cumulative cost summaries.
- [ ] Clearly identify estimated token counts versus provider-reported counts.

### Phase 6 acceptance criteria

- Displayed total cost includes every model call made by the workflow.
- A configured budget prevents additional calls before the budget is exceeded.
- Users can distinguish model cost from third-party data-provider cost.

## Evaluation plan

- [ ] Create a fixed evaluation set containing:
  - One large-cap single-ticker analysis
  - One smaller or sparsely covered ticker
  - One same-sector comparison
  - One cross-sector comparison
  - One report with intentionally missing data
- [ ] Compare Economy, Balanced, and Maximum quality modes on:
  - Factual accuracy
  - Numerical accuracy
  - Recommendation consistency
  - Risk coverage
  - Citation correctness
  - Executive readability
  - Latency
  - Total input/output tokens
  - Total estimated cost
- [ ] Do not make a cheaper mode the default until it passes the evaluation threshold.

## Recommended implementation order

1. Add complete cost accounting, including CrewAI.
2. Add stage-specific model routing and Economy/Balanced/Maximum modes.
3. Reduce output limits and evidence context sizes.
4. Add the compact CrewAI decision brief and Quick decision mode.
5. Move mechanical review checks into Python.
6. Add cache keys and result reuse.
7. Add Groq support.
8. Add Ollama/local-model support.
9. Run the evaluation suite and select safe defaults.

## Expected outcome

Target a 60–90% reduction in model cost for typical Standard runs, depending on ticker count, output length, selected models, cache hits, and whether the full CrewAI committee is enabled.

## Reference links

- OpenAI model catalog: https://developers.openai.com/api/docs/models
- GPT-5 pricing: https://developers.openai.com/api/docs/models/gpt-5
- GPT-5 nano: https://developers.openai.com/api/docs/models/gpt-5-nano
- Groq rate limits: https://console.groq.com/docs/rate-limits
- Groq supported models: https://console.groq.com/docs/models
