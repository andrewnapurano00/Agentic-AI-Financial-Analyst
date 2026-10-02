---
name: axiom-safe-refactor
description: "Extract focused Axiom provider, calculation, scoring, rendering, or export modules while preserving existing behavior."
---

# Axiom Safe Refactoring

Reduce mixed responsibilities with an observable behavior-preservation contract.

Read the repository AGENTS.md. The known large modules are `src/langgraphagenticai/ui/equity_report_tab.py`, `src/langgraphagenticai/portfolio_manager/decision_engine.py`, and `src/langgraphagenticai/portfolio_manager/data_sources.py`. Their size does not authorize a full rewrite.

## Pick the seam

Locate the requested responsibility and its actual callers with rg. Prefer a pure calculation, adapter, scorecard, formatter, export builder, or service boundary with clear inputs/outputs.

Before extraction, identify hidden dependencies: Streamlit session keys, cache decorators and .clear callers, module constants, provider calls, model calls, class identity during reloads, imports, and mutable DataFrames.

Large modules may define the same function name more than once. Python binds the last definition; confirm the active implementation and every relevant runtime consumer. Do not extract an obsolete shadowed function as if it were active.

## Preserve the contract

- Establish synthetic characterization fixtures for meaningful outputs, schema/column order, zero/missing behavior, sector policies, warnings, and error states.
- Separate pure transformations from retrieval and UI. Choose dependency direction that prevents circular imports or Streamlit/network initialization in domain imports.
- Move one coherent responsibility; keep compatibility imports/wrappers if existing callers need them. Avoid duplicate implementations as a permanent migration strategy.
- Preserve cache lifetime and invalidation behavior. An extracted cached function with a lost .clear call can keep stale results.
- Check pandas index alignment and copy/mutation behavior, not just equal displayed values.
- Preserve saved-result/session payload contracts and export consumers. If a behavior correction is necessary, identify it explicitly and test it separately from the extraction.

For review-only requests, describe candidate seams and risks without editing.

## Verify and hand off

Run focused characterization/domain tests before and after extraction. Shared provider infrastructure, routing, or common contracts require the full suite under repository rules. Compile/import affected modules, then perform health/browser checks when app behavior is involved.

Report the old responsibility, new module, compatibility strategy, evidence of preserved behavior, and remaining coupling. Update PLAN.md only if a milestone was completed or materially rescoped; splitting one helper does not complete the architecture roadmap.
