"""Historical diagnostics, not predicted risk or a point-in-time strategy backtest."""
import numpy as np
import pandas as pd
from .schemas import RiskDiagnostics

CONVENTION = ("Simple daily price returns on common observed dates, no filling; at least 60 returns and 90% common-date coverage. "
              "Sample covariance (ddof=1), 20% diagonal shrinkage for sizing, 252 sessions/year. "
              "Static daily-rebalanced mix of current weights; cash return and risk-free assumption 0%, no Sharpe/alpha estimate. "
              "No fees, taxes or dividends; not a historical strategy backtest. ETF categories are not sector look-through.")


def aligned_returns(securities):
    if not securities or any(len(s.history) < 61 for s in securities):
        return None, "At least 61 positive closes per holding required."
    series = [pd.Series(s.history, name=s.ticker, dtype=float) for s in securities]
    combined = pd.concat(series, axis=1).sort_index()
    common = combined.dropna()
    # Only measure the common span; no invented returns on missing observations.
    if common.empty:
        return None, "No common historical dates."
    span = combined.loc[common.index[0]:common.index[-1]]
    if len(common) < 61 or len(common)/len(span) < .9:
        return None, "Insufficient aligned observations or common coverage below 90%."
    if (common <= 0).any().any() or not np.isfinite(common.to_numpy()).all():
        return None, "Invalid historical prices."
    returns = common.pct_change(fill_method=None).iloc[1:]
    return returns, f"Common coverage {len(common)}/{len(span)} observed dates; omitted dates can create multi-session returns."


def shrunk_covariance(returns):
    cov = returns.cov().to_numpy()
    return .8*cov + .2*np.diag(np.diag(cov))


def drawdown(returns):
    wealth = np.r_[1., np.cumprod(1.+np.asarray(returns, dtype=float))]
    return float(np.min(wealth/np.maximum.accumulate(wealth)-1.))


def sizing_signals(securities):
    returns, note = aligned_returns(securities)
    if returns is None:
        return None, note
    cov = shrunk_covariance(returns)
    vol = np.sqrt(np.diag(cov))
    if not np.isfinite(vol).all() or (vol < 1e-8).any():
        return None, "Zero/unstable variance; equal-weight fallback."
    corr = returns.corr().fillna(0).to_numpy()
    crowd = np.maximum(corr-np.eye(len(securities)), 0).sum(axis=1)/max(1, len(securities)-1)
    scores = 1./(vol*(1+crowd))
    return dict(zip(returns.columns, scores.tolist())), note


def diagnostics(securities, weights, benchmark=None):
    returns, note = aligned_returns(securities)
    warnings = [note]
    if returns is None:
        return RiskDiagnostics(status="unavailable", observations=0, start=None, end=None, annualized_volatility=None,
                               max_drawdown=None, benchmark_return=None, portfolio_return=None, high_correlations=[],
                               warnings=warnings, convention=CONVENTION)
    vector = np.array([weights[s] for s in returns.columns])
    portfolio = returns.to_numpy()@vector
    vol = float(np.std(portfolio, ddof=1)*np.sqrt(252))
    corr = returns.corr()
    pairs = [f"{a}/{b}: {corr.loc[a,b]:.2f}" for i,a in enumerate(returns.columns) for b in returns.columns[i+1:]
             if pd.notna(corr.loc[a,b]) and corr.loc[a,b] > .85]
    benchmark_return = None
    # Require exact dates for benchmark comparison; do not compare differing windows.
    if benchmark:
        dates = [min(set.intersection(*(set(s.history) for s in securities)))] + list(returns.index)
        if all(d in benchmark.history for d in dates):
            benchmark_return = benchmark.history[dates[-1]]/benchmark.history[dates[0]]-1
        else:
            warnings.append("Benchmark comparison suppressed: exact portfolio dates unavailable.")
    else:
        warnings.append("Benchmark unavailable.")
    return RiskDiagnostics(status="available", observations=len(returns), start=min(set.intersection(*(set(s.history) for s in securities))),
                           end=returns.index[-1], annualized_volatility=vol, max_drawdown=drawdown(portfolio),
                           portfolio_return=float(np.prod(1+portfolio)-1), benchmark_return=benchmark_return,
                           high_correlations=pairs[:12], warnings=warnings, convention=CONVENTION)
