# AAFA-1 - Deep Research V2 diagnostic

**Date:** 2026-10-02 (America/New_York). **Code baseline:** `619494c`. **Scope:** investigation and recommended repair, not implementation or deployment.

Issue: [AAFA-1](https://bigmeatpete717.atlassian.net/browse/AAFA-1), "Determine the issues causing Deep Research v2 to not run/ output any analysis". The description appears to omit "not"; this investigation follows the title. No comments, attachments, failing request settings or run diagnostics were present in the issue when read.

## Conclusion

V2 can produce and render a report in the mocked successful path. Its failure-state presentation and recovery are defective: incomplete generation and pending review are labelled ready, stored warnings are not displayed, and neither state has a retry action. The reduced completion budget combined with the unchanged long V1 memo prompt is a plausible trigger for missing output, but the original user's provider response is needed to establish that trigger for their run.

Do not claim that all runs fail, that credentials are invalid, or that the original incident was definitively a token exhaustion. No paid model or live financial-provider run was performed.

## Findings and evidence

### F1 - Confirmed: failure is presented as ready and recovery is missing

Locations: [V2 UI](../../src/langgraphagenticai/ui/deep_research_v2_tab.py), lines 192-195 and 218-241; [manager](../../src/langgraphagenticai/deep_research/manager.py), lines 630-664.

The manager catches drafting failures, returns `status=incomplete`, preserves evidence/partial text and adds an actionable warning. Review failure returns `review_pending` with the draft and warning preserved. V2 calls `run_status.update(... state="complete")` for either result and uses "V2 research ready" for every state except `evidence_ready`. The status metric does show the actual status, but the prominent completion banner contradicts it.

V2 does not render `warnings`, `report_warnings` or `gaps` as a failure/recovery summary. It renders `report` rather than the status-qualified `markdown`. Only `evidence_ready` exposes "Generate report from saved evidence"; `incomplete` and `review_pending` expose no retry. The fallback report tells the user to use **Retry report writing**, a control that V2 never renders. V1 already supplies retry/review/finalize controls that can guide a repair.

**Impact:** a model failure is obscured and valid collected evidence cannot be retried through V2 without starting again. Starting another failed run can repeat paid work/provider requests.

### F2 - Confirmed configuration mismatch; original-run trigger remains unverified

Locations: [V2 modes/limits](../../src/langgraphagenticai/deep_research/v2.py), lines 32-89; [manager invocation and memo prompt](../../src/langgraphagenticai/deep_research/manager.py), lines 242-249 and 405-446.

Economy Standard drafting allows 1,800 completion tokens; Economy Extended allows 3,000. Balanced/Maximum allow 2,200/3,500. However, the shared writer still asks for roughly 1,000-1,400 words Standard or 1,600-2,000 Extended, plus extensive mandatory sections, tables and inline citations. V2 has no matching short-form prompt. The manager sets minimal reasoning only for supported planning/review stages, not for drafting.

OpenAI's completion limit covers visible and non-visible generated tokens, including reasoning. This makes an exhausted limit with little or no visible output a plausible outcome, not a proven occurrence in the original incident. See [OpenAI token-counting documentation](https://developers.openai.com/api/docs/guides/token-counting).

The diagnostic supplied a synthetic stream with empty content, `finish_reason=length`, 1,800 output tokens and 1,800 reasoning tokens. The real manager returned `incomplete`; the V2 UI then reproduced F1. This proves handling of that failure, not how a live GPT-5-mini request would behave.

**Recommended direction:** size the V2 memo to its selected mode and company count, and configure supported per-stage reasoning explicitly. Measure a usable visible-output allowance within the chosen budget. Do not simply raise every cap or change the user's model silently.

### F3 - Confirmed: optional decision failure reports the entire pilot as failed

Location: [V2 submission and decision stages](../../src/langgraphagenticai/ui/deep_research_v2_tab.py), lines 160-195.

Quick decision and committee calls share the outer report-run exception handler. A decision timeout or budget rejection therefore shows "V2 pilot could not complete" even when the report checkpoint is complete. The report can survive in history, so this is not proven report deletion. The exception exits before the normal final save/active-run selection and leaves the overall status panel without a precise decision failure outcome.

The conditional guard is merely `result.get("report")`, so fallback or incomplete report text can also enter a paid decision stage. Truthy text is not evidence that synthesis/review succeeded.

**Recommended direction:** save/select the research result before optional decisions, gate decisions on an explicitly allowed report status, isolate decision errors and record a decision-specific retry/warning. Preserve successful analysis regardless of committee failure.

### F4 - Confirmed: setup errors lose useful configuration context

Locations: [V2 manager factory](../../src/langgraphagenticai/ui/deep_research_v2_tab.py), lines 25-46; [stage factory](../../src/langgraphagenticai/deep_research/v2.py), lines 38-60; [error categorizer](../../src/langgraphagenticai/deep_research/manager.py), lines 122-138.

The factory constructs all four plan/draft/review/follow-up models before `manager.run` creates its first checkpoint, even for evidence-only work. A missing Groq key raises a meaningful `ValueError` from the stage factory, but the outer generic categorizer discards that detail. There is no saved run for a pre-checkpoint setup failure.

Missing selected-provider keys, unavailable optional imports and invalid configuration should be distinguished from a model response failure. Do not show arbitrary exception bodies: return allowlisted safe configuration messages and the failing stage/provider.

**Recommended direction:** preflight the stages actually required, retain safe reasons, and construct optional/resume models only when needed. For evidence-only mode clarify whether planning is intended to require a model; it currently still plans/investigates before stopping.

### F5 - Coverage gap and additional review items

The five tests in `test_deep_research_v2.py` cover helpers/configuration/fixtures, not actual V2 submissions, recovery buttons or optional-stage failure. The nine existing Deep Research interaction tests exercise V1.

Static review also found budget rejection occurs before `_invoke`'s diagnostic `try/finally`, so a blocked stage may lack its own diagnostic row. V2 exposes numeric performance rows but not their saved report warning reasons. Mechanical checks are not rerun after review patches; this is a validation-quality concern, not an established cause of no output. Saved-result reuse can also ignore changed decision/runtime options; keep that separate from the generation incident.

## Offline diagnostic results

The custom harness generated results with the real `ResearchManager`, synthetic company evidence and mocked model responses, then submitted the real V2 Streamlit fragment using a patched manager factory. Optional PDF generation and decision models were mocked; no live provider/model calls occurred. Assertions checked the outcomes below.

| Case | Observed result | Recovery/presentation |
| --- | --- | --- |
| Valid report | `complete`, report rendered, no UI exception | Ready label is appropriate |
| Empty stream ending at token limit | `incomplete`; failure diagnostic saved | "V2 research ready"; saved warning hidden; no retry |
| Review timeout | `review_pending`; report retained | "V2 research ready"; saved warning hidden; no retry |
| Optional quick-decision timeout | Completed report retained in checkpoint | Entire-pilot failure message; no decision retry |
| Setup exception | No saved result; safe but generic error | Does not identify configuration/stage |

A separate factory check confirmed missing Groq credentials abort construction at the planning model; an Economy evidence-only factory constructs four models. These checks cover local control flow, not external-provider availability.

Existing focused suite: **60 passed in 32.48 seconds**. Python 3.12.7, existing local environment; dependency drift recorded in PLAN remains applicable. Command:

```powershell
$env:PYTHONPATH = (Resolve-Path "src").Path
python -m pytest tests/test_deep_research.py tests/test_deep_research_recovery.py tests/test_deep_research_ui.py tests/test_deep_research_v2.py -q
```

Custom scenarios were run as an ad hoc diagnostic, not added to the permanent pytest inventory. Therefore this investigation does not change the recorded total of 85 tests.

## Proposed repair and acceptance criteria

1. **Restore honest status and recovery first.** Render warnings/gaps and distinguish complete, needs-review, review-pending, incomplete and evidence-ready. Add retry-writing and retry-review using `resume(saved)`, checkpoints and saved runtime configuration. Preserve drafts/diagnostics, avoid provider recollection, and keep reruns/downloads free of new model calls.
2. **Align generation settings.** Add compact mode-specific prompts, model-supported reasoning settings and measured token allocations. Surface finish reason, actual usage and blocked-stage budget diagnostics safely. Preserve V1 defaults; require explicit user action for retries or budget increases.
3. **Isolate decisions and preflight.** Save/select the report before decisions; gate on valid status. Record separate decision failure/retry. Show safe selected-provider configuration errors before charging for work and avoid unused-stage construction.
4. **Add permanent V2 interaction/recovery contracts.** Cover success, empty/length/timeout draft, failed review, malformed review, budget block, no usable evidence, invalid symbols/missing provider key, saved-result reuse, evidence-only resume, decision failure, history selection and no calls on rerun/download. Assertions should express repaired behavior, not preserve these bugs.

Minimum release acceptance: failed generation never says ready; every retained evidence/draft state has an appropriate visible recovery action; review retry performs no new drafting/collection; decision failure never masks a valid report; required settings errors identify the stage; V1 tests still pass. A paid live smoke/evaluation is optional and requires explicit scope; helper tests alone cannot establish report quality or cost savings.

## Evidence still needed for the original incident

Use saved audit JSON or sanitized Performance details: run ID/status, cost mode/depth/tickers, light provider/model, decision/stop options, warnings/gaps, failed stage, finish reason, token usage including reasoning, and provider error category. Never export keys or raw credentials. These distinguish token exhaustion, missing evidence, timeouts/access errors, setup failure and optional-decision failure.

No Jira status/comment changes, application fixes, Git commits or pushes were performed as part of this investigation.
