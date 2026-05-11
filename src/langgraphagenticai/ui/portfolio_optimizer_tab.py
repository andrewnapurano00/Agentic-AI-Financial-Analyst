import datetime as dt
from dataclasses import dataclass
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from sklearn.cluster import KMeans


# =========================================================
# CONFIG
# =========================================================
TRADING_DAYS = 252
INDEX_PROXY = "SPY"

CRISIS_WINDOWS = [
    ("GFC 2008-2009", dt.date(2007, 10, 1), dt.date(2009, 3, 9)),
    ("US_EU_Downgrade_2011", dt.date(2011, 7, 1), dt.date(2011, 10, 3)),
    ("China_Oil_2015_2016", dt.date(2015, 6, 1), dt.date(2016, 2, 11)),
    ("COVID_2020", dt.date(2020, 2, 1), dt.date(2020, 3, 23)),
    ("Rates_Inflation_2022", dt.date(2022, 1, 1), dt.date(2022, 10, 31)),
]

DEFAULT_TICKERS = "VTI, VTV, MGK, JPM, MSFT, CVX, LMT"


# =========================================================
# DATA STRUCTURES
# =========================================================
@dataclass
class PortfolioMetrics:
    ann_return: float
    ann_vol: float
    sharpe: float


# =========================================================
# GENERAL HELPERS
# =========================================================
def parse_tickers(text: str) -> List[str]:
    if not text:
        return []
    tokens = (
        text.replace("\n", " ")
        .replace("\t", " ")
        .replace(";", ",")
        .replace(",", " ")
        .split()
    )
    tickers = sorted({t.strip().upper() for t in tokens if t.strip()})
    return tickers


def format_pct(x) -> str:
    return "NA" if pd.isna(x) else f"{x * 100:.2f}%"


def format_num(x, decimals: int = 2) -> str:
    return "NA" if pd.isna(x) else f"{x:.{decimals}f}"


def max_drawdown_from_returns(returns_series: pd.Series) -> float:
    if returns_series.empty:
        return np.nan
    equity = (1 + returns_series).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return drawdown.min()


def normalize_weights(weights: np.ndarray) -> np.ndarray:
    weights = np.asarray(weights, dtype=float)
    total = weights.sum()
    if total <= 0:
        raise ValueError("Weights must sum to a positive number.")
    return weights / total


def parse_custom_weights(text: str, n_assets: int) -> Tuple[Optional[np.ndarray], Optional[str]]:
    if not text.strip():
        return None, "Please enter custom weights."

    try:
        raw = [x for x in text.replace(",", " ").split() if x.strip()]
        has_percent = any("%" in x for x in raw)

        vals = []
        for x in raw:
            vals.append(float(x.replace("%", "")))

        arr = np.array(vals, dtype=float)

        if has_percent:
            arr = arr / 100.0

        if len(arr) != n_assets:
            return None, f"Expected {n_assets} weights but got {len(arr)}."

        if arr.sum() <= 0:
            return None, "Weights must sum to a positive number."

        arr = normalize_weights(arr)
        return arr, None

    except Exception:
        return None, "Could not parse weights. Use values like 0.2 or 20%."


# =========================================================
# DATA ACCESS
# =========================================================
@st.cache_data(ttl=900, show_spinner=False)
def fetch_prices_yahoo(
    tickers: List[str],
    start: Optional[dt.date] = None,
    end: Optional[dt.date] = None,
    period: Optional[str] = None,
) -> pd.DataFrame:
    """
    Download adjusted close prices from Yahoo.
    """
    if not tickers:
        return pd.DataFrame()

    download_kwargs = {
        "tickers": tickers,
        "auto_adjust": True,
        "progress": False,
    }

    if period is not None:
        download_kwargs["period"] = period
    else:
        download_kwargs["start"] = start
        download_kwargs["end"] = end + dt.timedelta(days=1)

    data = yf.download(**download_kwargs)

    if data.empty or "Close" not in data:
        return pd.DataFrame()

    prices = data["Close"]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    prices = prices.dropna(how="all").ffill().dropna(how="all")
    return prices


# =========================================================
# RISK / RETURN ANALYTICS
# =========================================================
def build_returns(prices: pd.DataFrame) -> pd.DataFrame:
    if prices.empty:
        return pd.DataFrame()
    return prices.pct_change().dropna(how="all")


def build_risk_table(prices: pd.DataFrame, index_proxy: str = INDEX_PROXY) -> pd.DataFrame:
    rets = build_returns(prices)
    if rets.empty:
        return pd.DataFrame()

    ann_return = (1 + rets).prod() ** (TRADING_DAYS / len(rets)) - 1
    ann_vol = rets.std() * np.sqrt(TRADING_DAYS)
    sharpe = ann_return / ann_vol.replace(0, np.nan)

    mdds = [max_drawdown_from_returns(rets[col].dropna()) for col in rets.columns]

    try:
        proxy = yf.download(
            index_proxy,
            start=rets.index.min(),
            end=rets.index.max() + dt.timedelta(days=1),
            auto_adjust=True,
            progress=False,
        )
        proxy_px = proxy["Close"].dropna()
        proxy_rets = proxy_px.pct_change().reindex(rets.index).dropna()
    except Exception:
        proxy_rets = None

    betas = []
    downside_vols = []

    for col in rets.columns:
        r = rets[col].dropna()

        if proxy_rets is None or proxy_rets.empty:
            betas.append(np.nan)
            downside_vols.append(np.nan)
            continue

        aligned = pd.concat([r, proxy_rets], axis=1, join="inner").dropna()
        if aligned.shape[0] < 30:
            betas.append(np.nan)
            downside_vols.append(np.nan)
            continue

        rp = aligned.iloc[:, 0]
        rm = aligned.iloc[:, 1]

        market_var = np.var(rm)
        covar = np.cov(rp, rm)[0, 1]
        beta = covar / market_var if market_var > 0 else np.nan
        betas.append(beta)

        neg = rp[rp < 0]
        downside_vol = neg.std() * np.sqrt(TRADING_DAYS) if len(neg) > 0 else np.nan
        downside_vols.append(downside_vol)

    out = pd.DataFrame(
        {
            "Ticker": rets.columns,
            "AnnReturn": ann_return.values,
            "AnnVol": ann_vol.values,
            "Sharpe": sharpe.values,
            "MaxDrawdown": mdds,
            "Beta": betas,
            "DownsideVol": downside_vols,
        }
    )

    return out


def make_asset_summary_table(prices: pd.DataFrame, index_proxy: str = INDEX_PROXY) -> pd.DataFrame:
    """
    Wrapper used by the renderer.
    """
    return build_risk_table(prices=prices, index_proxy=index_proxy)


# =========================================================
# PORTFOLIO SIMULATION
# =========================================================
def calc_portfolio_perf(
    weights: np.ndarray,
    returns_df: pd.DataFrame,
    risk_free_annual: float,
) -> PortfolioMetrics:
    R = returns_df.values
    w = np.asarray(weights, dtype=float).reshape(-1, 1)

    port_ret = (R @ w).ravel()
    port_ret = pd.Series(port_ret).replace([np.inf, -np.inf], np.nan).dropna().values

    if port_ret.size == 0:
        return PortfolioMetrics(np.nan, np.nan, np.nan)

    log_r = np.log1p(port_ret)
    g = log_r.mean()
    ann_return = np.expm1(g * TRADING_DAYS)
    ann_vol = port_ret.std(ddof=0) * np.sqrt(TRADING_DAYS)
    sharpe = (ann_return - risk_free_annual) / ann_vol if ann_vol > 0 else np.nan

    return PortfolioMetrics(ann_return, ann_vol, sharpe)


def simulate_random_portfolios(
    num_portfolios: int,
    returns_df: pd.DataFrame,
    risk_free_annual: float,
    ticker_list: List[str],
) -> pd.DataFrame:
    R = returns_df.values
    _, n_assets = R.shape

    weights = np.random.random((n_assets, num_portfolios))
    weights /= weights.sum(axis=0, keepdims=True)

    port_returns = R @ weights
    port_returns = np.where(np.isfinite(port_returns), port_returns, np.nan)

    log_r = np.log1p(port_returns)
    g = np.nanmean(log_r, axis=0)
    ann_return = np.expm1(g * TRADING_DAYS)

    ann_vol = np.nanstd(port_returns, axis=0) * np.sqrt(TRADING_DAYS)
    sharpe = np.where(ann_vol > 0, (ann_return - risk_free_annual) / ann_vol, np.nan)

    results = np.vstack([ann_return, ann_vol, sharpe, weights])
    cols = ["ret", "stdev", "sharpe"] + list(ticker_list)

    return pd.DataFrame(results.T, columns=cols)


# =========================================================
# K-MEANS RISK BUCKETS
# =========================================================
def kmeans_risk_buckets(stats_df: pd.DataFrame, n_clusters: int = 3) -> Optional[pd.DataFrame]:
    if stats_df is None or stats_df.empty:
        return None

    feat_cols = ["AnnVol", "MaxDrawdown", "Beta", "DownsideVol"]
    df = stats_df.copy().reset_index(drop=True)

    X_df = df[feat_cols].replace([np.inf, -np.inf], np.nan)
    valid_mask = X_df.notna().all(axis=1)

    if valid_mask.sum() < 2:
        return None

    X = X_df.loc[valid_mask].values
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    Xs = (X - mu) / sigma

    k = min(n_clusters, len(X))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(Xs)

    df["Cluster"] = np.nan
    df.loc[valid_mask, "Cluster"] = labels.astype(int)

    summary = (
        df[df["Cluster"].notna()]
        .groupby("Cluster")
        .agg(
            MeanVol=("AnnVol", "mean"),
            MeanBeta=("Beta", "mean"),
            MeanDD=("MaxDrawdown", "mean"),
        )
        .reset_index()
    )

    summary["Cluster"] = summary["Cluster"].astype(int)
    order = summary.sort_values(["MeanBeta", "MeanVol"])["Cluster"].tolist()

    bucket_names = [
        "Defensive / low beta",
        "Core / market-like",
        "Growth / high beta",
        "Speculative / very high risk",
    ]

    label_map = {}
    for i, cid in enumerate(order):
        label_map[cid] = bucket_names[min(i, len(bucket_names) - 1)]

    df["BucketLabel"] = df["Cluster"].map(
        lambda x: label_map.get(int(x), "Unclustered") if pd.notna(x) else "Unclustered"
    )

    return df


# =========================================================
# CRISIS FINGERPRINTS
# =========================================================
def build_crisis_fingerprint(prices_long: pd.DataFrame) -> pd.DataFrame:
    if prices_long.empty:
        return pd.DataFrame()

    rets = prices_long.pct_change().dropna(how="all")
    if rets.empty:
        return pd.DataFrame()

    rows = []

    for ticker in rets.columns:
        r = rets[ticker].dropna()
        if r.empty:
            continue

        ann_ret = (1 + r).prod() ** (TRADING_DAYS / len(r)) - 1
        ann_vol = r.std(ddof=0) * np.sqrt(TRADING_DAYS)
        mdd = max_drawdown_from_returns(r)

        row = {
            "Ticker": ticker,
            "LongTermAnnRet": float(ann_ret),
            "LongTermAnnVol": float(ann_vol),
            "LongTermMaxDD": float(mdd),
            "DataDays": int(len(r)),
        }

        for crisis_name, start_d, end_d in CRISIS_WINDOWS:
            col = f"Ret_{crisis_name}"
            sub = r.loc[(r.index.date >= start_d) & (r.index.date <= end_d)]
            row[col] = float((1 + sub).prod() - 1) if len(sub) >= 10 else np.nan

        rows.append(row)

    return pd.DataFrame(rows)


def kmeans_crisis_clusters(crisis_df: pd.DataFrame, n_clusters: int = 3) -> Optional[pd.DataFrame]:
    if crisis_df is None or crisis_df.empty:
        return None

    df = crisis_df.copy()
    crisis_cols = [c for c in df.columns if c.startswith("Ret_")]
    if not crisis_cols:
        return None

    df["AvgCrisisRet"] = df[crisis_cols].mean(axis=1, skipna=True)

    feat_cols = crisis_cols + ["LongTermAnnRet", "LongTermAnnVol", "LongTermMaxDD", "AvgCrisisRet"]
    X_df = df[feat_cols].replace([np.inf, -np.inf], np.nan)

    valid_mask = X_df.notna().all(axis=1)
    if valid_mask.sum() < 2:
        return None

    X = X_df.loc[valid_mask].values
    mu = X.mean(axis=0)
    sigma = X.std(axis=0)
    sigma[sigma == 0] = 1.0
    Xs = (X - mu) / sigma

    k = min(n_clusters, len(X))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(Xs)

    df["CrisisCluster"] = np.nan
    df.loc[valid_mask, "CrisisCluster"] = labels.astype(int)

    cluster_perf = (
        df[df["CrisisCluster"].notna()]
        .groupby("CrisisCluster")["AvgCrisisRet"]
        .mean()
        .reset_index()
        .sort_values("AvgCrisisRet")
        .reset_index(drop=True)
    )

    label_map = {}
    for i, row in enumerate(cluster_perf.itertuples(index=False)):
        cid = int(row.CrisisCluster)
        if i == 0:
            label_map[cid] = "Crisis-vulnerable / pro-cyclical"
        elif i == 1:
            label_map[cid] = "Mixed / moderate"
        else:
            label_map[cid] = "Crisis-resilient / defensive"

    df["CrisisRole"] = df["CrisisCluster"].map(
        lambda x: label_map.get(int(x), "Unclustered") if pd.notna(x) else "Unclustered"
    )

    return df


def build_crisis_role_table(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Merge long-term risk stats, risk-bucket labels, and crisis-role diagnostics.
    """
    if prices is None or prices.empty:
        return pd.DataFrame()

    risk_df = build_risk_table(prices)
    if risk_df.empty:
        return pd.DataFrame()

    bucket_df = kmeans_risk_buckets(risk_df)
    if bucket_df is None or bucket_df.empty:
        bucket_df = risk_df.copy()
        if "Cluster" not in bucket_df.columns:
            bucket_df["Cluster"] = np.nan
        if "BucketLabel" not in bucket_df.columns:
            bucket_df["BucketLabel"] = "Unclustered"

    crisis_fp = build_crisis_fingerprint(prices)
    if crisis_fp.empty:
        out = bucket_df.copy()
        if "CrisisCluster" not in out.columns:
            out["CrisisCluster"] = np.nan
        if "CrisisRole" not in out.columns:
            out["CrisisRole"] = "Unavailable"
        return out

    crisis_cluster_df = kmeans_crisis_clusters(crisis_fp)
    if crisis_cluster_df is None or crisis_cluster_df.empty:
        crisis_cluster_df = crisis_fp.copy()
        if "CrisisCluster" not in crisis_cluster_df.columns:
            crisis_cluster_df["CrisisCluster"] = np.nan
        if "CrisisRole" not in crisis_cluster_df.columns:
            crisis_cluster_df["CrisisRole"] = "Unclustered"

    merge_cols = [
        "Ticker",
        "LongTermAnnRet",
        "LongTermAnnVol",
        "LongTermMaxDD",
        "DataDays",
        "CrisisCluster",
        "CrisisRole",
    ] + [c for c in crisis_cluster_df.columns if c.startswith("Ret_")]

    merge_cols = [c for c in merge_cols if c in crisis_cluster_df.columns]

    out = bucket_df.merge(
        crisis_cluster_df[merge_cols],
        on="Ticker",
        how="left",
    )

    return out


# =========================================================
# DISPLAY HELPERS
# =========================================================
def pretty_risk_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["AnnReturn", "AnnVol", "MaxDrawdown", "DownsideVol"]:
        if col in out.columns:
            out[col] = out[col].map(format_pct)
    if "Sharpe" in out.columns:
        out["Sharpe"] = out["Sharpe"].map(lambda x: format_num(x, 2))
    if "Beta" in out.columns:
        out["Beta"] = out["Beta"].map(lambda x: format_num(x, 2))
    return out


def pretty_crisis_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["LongTermAnnRet", "LongTermAnnVol", "LongTermMaxDD"]:
        if col in out.columns:
            out[col] = out[col].map(format_pct)

    crisis_cols = [c for c in out.columns if c.startswith("Ret_")]
    for col in crisis_cols:
        out[col] = out[col].map(lambda x: "NA" if pd.isna(x) else f"{x * 100:.1f}%")
    return out


def format_portfolio_row(row: pd.Series, tickers: List[str]) -> pd.DataFrame:
    df = pd.DataFrame(row).T.copy()
    if "ret" in df.columns:
        df["ret"] = df["ret"].map(format_pct)
    if "stdev" in df.columns:
        df["stdev"] = df["stdev"].map(format_pct)
    if "sharpe" in df.columns:
        df["sharpe"] = df["sharpe"].map(lambda x: format_num(x, 2))
    for t in tickers:
        if t in df.columns:
            df[t] = df[t].map(format_pct)
    return df


# =========================================================
# PLOTS
# =========================================================
def plot_efficient_frontier(
    results_frame: pd.DataFrame,
    max_sharpe_port: pd.Series,
    min_vol_port: pd.Series,
    test_metrics: Optional[PortfolioMetrics] = None,
    test_label: Optional[str] = None,
):
    fig, ax = plt.subplots(figsize=(10, 6))

    sc = ax.scatter(
        results_frame["stdev"],
        results_frame["ret"],
        c=results_frame["sharpe"],
        cmap="RdYlBu",
        alpha=0.7,
        s=10,
    )

    ax.scatter(
        max_sharpe_port["stdev"],
        max_sharpe_port["ret"],
        marker=(5, 1, 0),
        color="red",
        s=200,
        label="Max Sharpe",
    )

    ax.scatter(
        min_vol_port["stdev"],
        min_vol_port["ret"],
        marker=(5, 1, 0),
        color="green",
        s=200,
        label="Min Volatility",
    )

    if test_metrics is not None:
        ax.scatter(
            test_metrics.ann_vol,
            test_metrics.ann_return,
            marker="X",
            color="black",
            s=140,
            label=test_label or "Test Portfolio",
        )

    ax.set_xlabel("Annualized standard deviation")
    ax.set_ylabel("Annualized return")
    ax.set_title("Efficient Frontier")
    ax.grid(alpha=0.3)
    ax.legend()

    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Sharpe Ratio")

    return fig


def plot_risk_buckets(bucket_df: pd.DataFrame):
    valid = bucket_df[bucket_df["Cluster"].notna()].copy()
    if valid.empty:
        return None

    fig, ax = plt.subplots(figsize=(7, 5))
    sc = ax.scatter(
        valid["AnnVol"],
        valid["AnnReturn"],
        c=valid["Cluster"],
        cmap="viridis",
        s=60,
    )

    for _, row in valid.iterrows():
        ax.annotate(
            row["Ticker"],
            (row["AnnVol"], row["AnnReturn"]),
            textcoords="offset points",
            xytext=(5, 3),
            fontsize=8,
        )

    ax.set_xlabel("Annualized Volatility")
    ax.set_ylabel("Annualized Return")
    ax.set_title("K-means Risk Buckets")
    ax.grid(alpha=0.3)

    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Cluster ID")
    return fig


def plot_crisis_roles(cluster_df: pd.DataFrame):
    valid = cluster_df[cluster_df["CrisisCluster"].notna()].copy()
    if valid.empty:
        return None

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    sc = ax.scatter(
        valid["LongTermAnnVol"],
        valid["LongTermAnnRet"],
        c=valid["CrisisCluster"],
        cmap="viridis",
        s=70,
        alpha=0.9,
    )

    for _, row in valid.iterrows():
        ax.annotate(
            row["Ticker"],
            (row["LongTermAnnVol"], row["LongTermAnnRet"]),
            textcoords="offset points",
            xytext=(5, 3),
            fontsize=8,
        )

    ax.set_xlabel("Long-term annualized volatility")
    ax.set_ylabel("Long-term annualized return")
    ax.set_title("Long-term Risk/Return by Crisis Role")
    ax.grid(alpha=0.3)

    cbar = plt.colorbar(sc, ax=ax)
    cbar.set_label("Crisis Cluster ID")
    return fig


# =========================================================
# TAB RENDERER
# =========================================================
def render_portfolio_optimizer_tab() -> None:
    st.subheader("Portfolio Optimizer & Backtests")
    st.caption("Offline-first optimizer page with efficient frontier, risk buckets, and crisis-role diagnostics.")

    with st.form("portfolio_optimizer_form"):
        c1, c2 = st.columns([2, 1])
        with c1:
            tickers_text = st.text_area(
                "Tickers (comma / space / newline separated)",
                value=st.session_state.get("portfolio_optimizer_tickers", DEFAULT_TICKERS),
                height=110,
            )
        with c2:
            regime = st.selectbox(
                "Analysis period",
                ["Custom period", "2008-2009 Financial Crisis", "2020 COVID Crash"],
                index=0,
            )

        d1, d2, d3 = st.columns(3)
        today = dt.date.today()
        with d1:
            start_date = st.date_input("Start date", value=dt.date(2017, 1, 1), disabled=(regime != "Custom period"))
        with d2:
            end_date = st.date_input("End date", value=min(today, dt.date(2025, 12, 31)), disabled=(regime != "Custom period"))
        with d3:
            num_portfolios = st.slider("Number of random portfolios", 1000, 100000, 20000, 1000)

        s1, s2, s3 = st.columns(3)
        with s1:
            rf = st.number_input("Risk-free rate (annual, %)", min_value=-2.0, max_value=10.0, value=0.0, step=0.25) / 100.0
        with s2:
            test_mode = st.selectbox("Test portfolio", ["None", "Equal-weight (1/N)", "Custom weights"], index=0)
        with s3:
            custom_weights_str = st.text_input(
                "Custom weights",
                value="",
                help="Same order as the active ticker list. Use decimals or percents.",
                disabled=(test_mode != "Custom weights"),
            )

        run_btn = st.form_submit_button("Run Portfolio Analysis", type="primary")

    if not run_btn:
        st.info("Enter tickers and settings, then build the portfolio analysis.")
        return

    if regime == "2008-2009 Financial Crisis":
        start_date = dt.date(2007, 7, 1)
        end_date = dt.date(2009, 6, 30)
    elif regime == "2020 COVID Crash":
        start_date = dt.date(2020, 2, 1)
        end_date = dt.date(2020, 12, 31)

    tickers = parse_tickers(tickers_text)
    st.session_state["portfolio_optimizer_tickers"] = tickers_text

    if not tickers:
        st.error("Please enter at least one valid ticker.")
        return
    if start_date >= end_date:
        st.error("Start date must be before end date.")
        return

    st.subheader("1. Price Data")
    with st.spinner("Downloading price history..."):
        prices = fetch_prices_yahoo(tickers, start=start_date, end=end_date)

    if prices.empty or prices.shape[1] < 2:
        st.error("Need at least 2 tickers with usable price data.")
        return

    requested = set(tickers)
    available = set(prices.columns)
    missing = sorted(requested - available)
    if missing:
        st.warning("Dropped due to missing data: " + ", ".join(missing))

    st.write(
        f"Using {prices.shape[1]} tickers with data from {prices.index.min().date()} to {prices.index.max().date()}."
    )
    st.caption(f"Regime: {regime}")
    st.dataframe(prices.tail().round(2), use_container_width=True, height=180)

    returns = build_returns(prices)
    if returns.empty:
        st.error("Not enough return history after cleaning.")
        return

    st.subheader("2. Efficient Frontier")
    with st.spinner("Simulating portfolios..."):
        results_frame = simulate_random_portfolios(
            num_portfolios=num_portfolios,
            returns_df=returns,
            risk_free_annual=rf,
            ticker_list=list(prices.columns),
        )

    max_sharpe_port = results_frame.iloc[results_frame["sharpe"].idxmax()]
    min_vol_port = results_frame.iloc[results_frame["stdev"].idxmin()]

    test_weights = None
    test_metrics = None
    test_label = None
    if test_mode == "Equal-weight (1/N)":
        test_weights = np.ones(len(prices.columns)) / len(prices.columns)
        test_metrics = calc_portfolio_perf(test_weights, returns, rf)
        test_label = "Equal-weight (1/N)"
    elif test_mode == "Custom weights":
        test_weights, err = parse_custom_weights(custom_weights_str, len(prices.columns))
        if err:
            st.error(err)
        else:
            test_metrics = calc_portfolio_perf(test_weights, returns, rf)
            test_label = "Custom Portfolio"

    fig_frontier = plot_efficient_frontier(results_frame, max_sharpe_port, min_vol_port, test_metrics, test_label)
    st.pyplot(fig_frontier, use_container_width=True)

    st.subheader("3. Risk / Return Table")
    risk_table = make_asset_summary_table(prices)
    display = risk_table.copy()
    for c in ["AnnReturn", "AnnVol", "MaxDrawdown", "DownsideVol"]:
        if c in display.columns:
            display[c] = display[c].map(format_pct)
    for c in ["Sharpe", "Beta"]:
        if c in display.columns:
            display[c] = display[c].map(lambda x: format_num(x, 2))
    st.dataframe(display, use_container_width=True, height=280)

    st.subheader("4. Crisis Fingerprint Roles")
    cluster_df = build_crisis_role_table(prices)
    c1, c2 = st.columns(2)
    with c1:
        fig_buckets = plot_risk_buckets(cluster_df)
        if fig_buckets is not None:
            st.pyplot(fig_buckets, use_container_width=True)
    with c2:
        fig_roles = plot_crisis_roles(cluster_df)
        if fig_roles is not None:
            st.pyplot(fig_roles, use_container_width=True)

    display_cluster = pretty_crisis_table(cluster_df)
    st.dataframe(display_cluster, use_container_width=True, height=260)

    st.subheader("5. Key Portfolio Weights")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Max Sharpe Portfolio**")
        st.dataframe(format_portfolio_row(max_sharpe_port, list(prices.columns)), use_container_width=True, height=220)
    with col2:
        st.markdown("**Minimum Volatility Portfolio**")
        st.dataframe(format_portfolio_row(min_vol_port, list(prices.columns)), use_container_width=True, height=220)

    if test_weights is not None and test_metrics is not None:
        st.markdown("**User Test Portfolio**")
        row = pd.Series(
            [test_metrics.ann_return, test_metrics.ann_vol, test_metrics.sharpe] + list(test_weights),
            index=["ret", "stdev", "sharpe"] + list(prices.columns),
            name=test_label,
        )
        st.dataframe(format_portfolio_row(row, list(prices.columns)), use_container_width=True, height=220)