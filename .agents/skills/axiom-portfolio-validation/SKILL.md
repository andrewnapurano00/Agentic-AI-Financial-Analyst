---
name: axiom-portfolio-validation
description: "Validate Axiom Portfolio Lab allocation caps, residual cash, rebalance arithmetic, optimizer assumptions, and risk metrics."
---

# Axiom Portfolio Validation

Keep allocation and trade math correct after constraints, with explicit cash and risk assumptions.

Read the repository AGENTS.md. This skill works on research software and simulated recommendations; it does not authorize brokerage activity.

## Calculation ownership

Under `src/langgraphagenticai/`:

- `portfolio_manager/constraint_validator.py`: validate_agentic_weights and cap-aware allocation.
- `portfolio_manager/rebalance_engine.py`: proposed trades and cash rows.
- `portfolio_manager/analytics.py`: position/asset analytics.
- `portfolio_manager/schemas.py`: portfolio data contracts.
- `ui/portfolio_optimizer_tab.py`: current optimizer calculations and assumptions.
- `portfolio_manager/portfolio_reporting.py`: allocation/trade reporting.
- `portfolio_manager/hybrid_workflow.py`: orchestration.

Avoid adding more responsibilities to decision_engine.py or data_sources.py. Extract a focused deterministic boundary when the requested repair needs one.

## Check invariants

1. Determine weight units, whether cash is explicit, whether shorts are supported, and whether the values are proposed or validated. Do not silently treat 20 as 20% if the schema expects 0.20.
2. Validate finite weights and allowed signs. Check position and sector caps after every adjustment. Preserve residual cash when available positions cannot absorb the investable budget; renormalizing capped securities to 100% can reintroduce violations.
3. Check that securities plus cash sum to the stated budget within a documented tolerance. Reject or clearly describe infeasible constraints; do not repair them by inventing securities.
4. Reconcile current value, target value, trade value, share change, and post-trade cash. Missing/zero prices cannot produce executable share counts. Account for fractional-share and minimum-trade policies when used.
5. Align observations before covariance, benchmark, beta, Sharpe, or drawdown calculations. Show the benchmark, sampling window, return basis, risk-free-rate basis, and annualization convention. Do not assume 252 applies to every asset calendar without labeling the convention.
6. Exclude CASH from security exposure metrics where appropriate, while including it in budget reconciliation. Surface currency mismatches before aggregation.

Read [portfolio-cases.md](references/portfolio-cases.md) for small hand-checkable fixtures.

## Verify and hand off

Start with `tests/test_hardening.py` for the existing cap regression. Add focused domain tests for changed allocation/analytics; do not call an LLM to test deterministic math.

For an optimizer defect, use a small known return sequence or covariance matrix and compare to an independent calculation. Explain any material assumption change in the UI/export.

Report the before/after allocation, constraints, residual cash, reconciled trade arithmetic, and validation evidence. Clearly distinguish a repaired mathematical constraint from a new investment opinion.
