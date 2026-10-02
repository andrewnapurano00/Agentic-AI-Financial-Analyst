---
name: axiom-cost-performance
description: "Measure and reduce Axiom rerun latency, repeated provider/model calls, prompt size, cache misses, and research cost."
---

# Axiom Cost and Performance

Improve measured latency or call counts while preserving the evidence and quality contract.

Read the repository AGENTS.md. Optimize the requested workflow before proposing provider/model replacement.

## Useful code boundaries

Under `src/langgraphagenticai/`:

- UI action gates and caches: `ui/introduction_tab.py`, `ui/top_movers_data.py`, `ui/deep_research_tab.py`, `ui/deep_research_v2_tab.py`.
- Shared bounded model clients: `providers/openai_client.py`, `LLMS/openaillm.py`.
- V1 stage diagnostics and budgets: `deep_research/manager.py`.
- V2 stage_configuration, research_cache_key, prompt_diagnostics, committee_diagnostics: `deep_research/v2.py`.
- Evidence compaction: `deep_research/prompt_context.py`.
- Equity/portfolio committees: `equity_committee.py`, `portfolio_manager/agentic_committee.py`.

Read TODO_DEEP_RESEARCH_COST_OPTIMIZATION.md only when the task concerns that subsystem's cost roadmap.

## Measure before changing

Record cold load, warm load, navigation, control change, download, and explicit regenerate/retry for the affected surface. Use test doubles/counters to separate provider calls, model calls, and deterministic work. Set a task-specific budget from the baseline and requested user outcome; do not invent a universal render target.

Ordinary reruns should make zero additional paid model calls. Cached evidence and cached narratives need separate ownership so formatting can reuse both, while explicit regeneration can reuse evidence.

Inspect cache dependencies: ticker set, fiscal basis, as-of/freshness, provider, model/prompt version, mode, and relevant constraints. Keys must distinguish materially different evidence. Metadata dates alone may not identify changed values; test collisions before trusting an existing cache-key helper. Keep credentials out of persisted artifacts and diagnostics.

Use batching and capped concurrency before adding more threads. Bound request/model retries, and preserve partial results. A process cache is not proof of automatic background refresh; make actual freshness behavior visible.

## AI stage economics

Preserve the user's selected model unless a model change is requested. If selection, pricing, or SDK behavior is part of the task, verify current official documentation.

Keep prompt compaction deterministic and retain cited evidence, dates, units, limitations, and opposing facts. Include planning, writing, review, follow-up, recovery, and committee calls in accounting. Distinguish measured usage, estimated tokens/cost, and unknown price; an unknown model price is not zero cost. Check the spending limit before launching a stage.

Validate quality using `tests/fixtures/deep_research_v2_eval_cases.json` and relevant mocked tests; do not use paid runs as the default benchmark.

## Handoff

Report a small before/after table of latency, call counts, prompt/output size, and measured or estimated cost with its assumptions. State any freshness/quality tradeoff and which task budget was achieved.
