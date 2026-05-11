from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np
import pandas as pd

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception:  # pragma: no cover - optional runtime dependency
    colors = None
    landscape = None
    letter = None
    getSampleStyleSheet = None
    inch = 72
    PageBreak = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional runtime dependency
    OpenAI = None


ADD_ACTIONS = {"Strong Buy", "Buy", "Add", "Start / Rotate In"}
TRIM_ACTIONS = {"Trim"}
EXIT_ACTIONS = {"Sell", "Exit", "Avoid"}
HOLD_ACTIONS = {"Hold", "Watchlist"}


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def _safe_str(x: Any, default: str = "") -> str:
    if x is None:
        return default
    try:
        if pd.isna(x):
            return default
    except Exception:
        pass
    text = str(x).strip()
    return text if text else default


def _pct(x: Any) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x) * 100:.1f}%"
    except Exception:
        return "NA"


def _money(x: Any) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return f"${float(x):,.0f}"
    except Exception:
        return "NA"


def _score(x: Any) -> str:
    try:
        if pd.isna(x):
            return "NA"
        return f"{float(x):.2f}"
    except Exception:
        return "NA"


def _first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def build_sector_allocation_table(
    position_snapshot: pd.DataFrame | None,
    rebalance_table: pd.DataFrame | None,
    portfolio_value: float | None = None,
) -> pd.DataFrame:
    """Build before/after sector allocation from current holdings and target rebalance output."""
    current_rows = pd.DataFrame()
    if position_snapshot is not None and not position_snapshot.empty:
        current_rows = position_snapshot.copy()
        if "sector" not in current_rows.columns:
            current_rows["sector"] = "Unknown"
        if "current_weight" not in current_rows.columns:
            value_col = _first_existing(current_rows, ["market_value", "current_value"])
            if value_col:
                vals = pd.to_numeric(current_rows[value_col], errors="coerce").fillna(0.0)
                denom = float(vals.sum()) or 1.0
                current_rows["current_weight"] = vals / denom
            else:
                current_rows["current_weight"] = 0.0
        current_alloc = (
            current_rows.assign(current_weight=pd.to_numeric(current_rows["current_weight"], errors="coerce").fillna(0.0))
            .groupby("sector", dropna=False)["current_weight"]
            .sum()
        )
    else:
        current_alloc = pd.Series(dtype=float)

    target_rows = pd.DataFrame()
    if rebalance_table is not None and not rebalance_table.empty:
        target_rows = rebalance_table.copy()
        if "sector" not in target_rows.columns:
            target_rows["sector"] = "Unknown"
        if "target_weight" not in target_rows.columns:
            target_rows["target_weight"] = 0.0
        target_alloc = (
            target_rows.assign(target_weight=pd.to_numeric(target_rows["target_weight"], errors="coerce").fillna(0.0))
            .groupby("sector", dropna=False)["target_weight"]
            .sum()
        )
    else:
        target_alloc = pd.Series(dtype=float)

    sectors = sorted(set(current_alloc.index.astype(str)).union(set(target_alloc.index.astype(str))))
    rows = []
    for sector in sectors:
        current_w = float(current_alloc.get(sector, 0.0))
        target_w = float(target_alloc.get(sector, 0.0))
        rows.append(
            {
                "sector": sector or "Unknown",
                "current_weight": current_w,
                "target_weight": target_w,
                "delta_weight": target_w - current_w,
                "current_value": (portfolio_value or 0.0) * current_w,
                "target_value": (portfolio_value or 0.0) * target_w,
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("target_weight", ascending=False).reset_index(drop=True)


def build_target_weight_explanations(rebalance_table: pd.DataFrame | None) -> pd.DataFrame:
    """Explain why each target weight changed in plain English."""
    if rebalance_table is None or rebalance_table.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, row in rebalance_table.copy().iterrows():
        ticker = _safe_str(row.get("ticker"), "NA")
        action = _safe_str(row.get("final_action"), "Hold")
        rebalance_action = _safe_str(row.get("rebalance_action"), "Maintain")
        current_w = _safe_float(row.get("current_weight"), 0.0)
        target_w = _safe_float(row.get("target_weight"), 0.0)
        delta_w = target_w - current_w
        reason = _safe_str(row.get("rebalance_reason"), "portfolio construction")
        confidence = _safe_str(row.get("decision_confidence"), "medium")
        data_quality = _safe_str(row.get("data_quality_label"), "medium")
        consensus = _safe_str(row.get("consensus_state"), "mixed")
        sizing = _safe_str(row.get("suggested_sizing"), "normal")
        constraints = _safe_str(row.get("constraint_flags"), "")
        trade_value = _safe_float(row.get("trade_value"), 0.0)

        if abs(delta_w) < 0.0025:
            change_phrase = "kept near the current weight"
        elif delta_w > 0:
            change_phrase = f"increased by {_pct(delta_w)}"
        else:
            change_phrase = f"reduced by {_pct(abs(delta_w))}"

        if action in ADD_ACTIONS:
            driver = "the committee views this as a capital-use candidate"
        elif action in TRIM_ACTIONS:
            driver = "the committee wants to harvest capital while keeping some exposure"
        elif action in EXIT_ACTIONS:
            driver = "the committee is removing or avoiding the position"
        else:
            driver = "the committee is keeping the position inside its tolerance band"

        explanation = (
            f"{ticker} was {change_phrase} because {driver}. The target reflects {reason}, "
            f"{confidence} decision confidence, {data_quality} data quality, {consensus} consensus, "
            f"and {sizing} sizing."
        )
        if constraints:
            explanation += f" Constraint overlay: {constraints}."

        rows.append(
            {
                "ticker": ticker,
                "sector": row.get("sector", "Unknown"),
                "final_action": action,
                "rebalance_action": rebalance_action,
                "current_weight": current_w,
                "target_weight": target_w,
                "delta_weight": delta_w,
                "trade_value": trade_value,
                "decision_confidence": confidence,
                "data_quality_label": data_quality,
                "reason_code": reason,
                "constraints": constraints,
                "target_weight_explanation": explanation,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("delta_weight", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def build_stress_scenario_table(
    recommendation_table: pd.DataFrame | None,
    rebalance_table: pd.DataFrame | None,
    sector_allocation: pd.DataFrame | None,
) -> pd.DataFrame:
    """Deterministic stress-test read-through based on recommendation, sector, risk, and target deltas."""
    if recommendation_table is None or recommendation_table.empty:
        return pd.DataFrame()

    recs = recommendation_table.copy()
    reb = rebalance_table.copy() if rebalance_table is not None and not rebalance_table.empty else pd.DataFrame()
    if not reb.empty:
        merge_cols = [c for c in ["ticker", "target_weight", "delta_weight", "rebalance_action"] if c in reb.columns]
        recs = recs.merge(reb[merge_cols], on="ticker", how="left", suffixes=("", "_rebalance"))

    for col in ["current_weight", "target_weight", "delta_weight", "composite_score", "risk_fit_score", "technical_score", "valuation_score", "fundamental_score"]:
        if col in recs.columns:
            recs[col] = pd.to_numeric(recs[col], errors="coerce")

    sector_target = {}
    if sector_allocation is not None and not sector_allocation.empty and {"sector", "target_weight"}.issubset(sector_allocation.columns):
        sector_target = dict(zip(sector_allocation["sector"].astype(str), pd.to_numeric(sector_allocation["target_weight"], errors="coerce").fillna(0.0)))

    scenario_defs = [
        {
            "scenario": "Market selloff",
            "portfolio_read_through": "Risk-off tape: prioritize liquidity, risk fit, and names with stronger quality scores.",
            "positive_sectors": {"Consumer Defensive", "Healthcare", "Utilities"},
            "negative_sectors": {"Technology", "Communication Services", "Consumer Cyclical", "Real Estate"},
            "risk_weight": 0.45,
            "technical_weight": 0.25,
            "quality_weight": 0.30,
        },
        {
            "scenario": "Rate shock",
            "portfolio_read_through": "Higher-rate tape: penalize long-duration growth, leverage, and rate-sensitive sectors.",
            "positive_sectors": {"Financial Services", "Energy"},
            "negative_sectors": {"Real Estate", "Utilities", "Technology", "Consumer Cyclical"},
            "risk_weight": 0.40,
            "technical_weight": 0.20,
            "quality_weight": 0.40,
        },
        {
            "scenario": "Recession",
            "portfolio_read_through": "Growth slowdown: favor balance-sheet quality, defensive sectors, and lower-risk holdings.",
            "positive_sectors": {"Consumer Defensive", "Healthcare", "Utilities"},
            "negative_sectors": {"Consumer Cyclical", "Energy", "Industrials", "Financial Services"},
            "risk_weight": 0.50,
            "technical_weight": 0.15,
            "quality_weight": 0.35,
        },
        {
            "scenario": "AI-led rally",
            "portfolio_read_through": "Risk-on growth leadership: favor high-quality technology, communication services, and momentum winners.",
            "positive_sectors": {"Technology", "Communication Services"},
            "negative_sectors": {"Utilities", "Consumer Defensive", "Real Estate"},
            "risk_weight": 0.20,
            "technical_weight": 0.40,
            "quality_weight": 0.40,
        },
    ]

    rows: list[dict[str, Any]] = []
    for scenario in scenario_defs:
        scored = recs.copy()
        sector = scored.get("sector", pd.Series("Unknown", index=scored.index)).astype(str)
        sector_bonus = np.where(sector.isin(scenario["positive_sectors"]), 1.0, 0.0)
        sector_penalty = np.where(sector.isin(scenario["negative_sectors"]), -1.0, 0.0)
        risk = scored.get("risk_fit_score", pd.Series(5.0, index=scored.index)).fillna(5.0) / 10.0
        tech = scored.get("technical_score", pd.Series(5.0, index=scored.index)).fillna(5.0) / 10.0
        quality = scored.get("fundamental_score", pd.Series(5.0, index=scored.index)).fillna(5.0) / 10.0
        valuation = scored.get("valuation_score", pd.Series(5.0, index=scored.index)).fillna(5.0) / 10.0
        quality_blend = 0.65 * quality + 0.35 * valuation
        scenario_score = (
            scenario["risk_weight"] * risk
            + scenario["technical_weight"] * tech
            + scenario["quality_weight"] * quality_blend
            + 0.08 * sector_bonus
            + 0.08 * sector_penalty
        )
        scored["scenario_score"] = np.clip(scenario_score, 0.0, 1.0)
        scored["target_weight_filled"] = scored.get("target_weight", pd.Series(0.0, index=scored.index)).fillna(
            scored.get("current_weight", pd.Series(0.0, index=scored.index)).fillna(0.0)
        )
        scored["weighted_score"] = scored["scenario_score"] * scored["target_weight_filled"].clip(lower=0.0)
        portfolio_resilience = float(scored["weighted_score"].sum() / max(scored["target_weight_filled"].sum(), 1e-9))

        vulnerable = scored.sort_values("scenario_score", ascending=True).head(3)
        resilient = scored.sort_values("scenario_score", ascending=False).head(3)
        target_sectors = sorted(sector_target.items(), key=lambda kv: kv[1], reverse=True)[:3]

        if portfolio_resilience >= 0.68:
            stance = "Constructive"
        elif portfolio_resilience >= 0.52:
            stance = "Mixed"
        else:
            stance = "Vulnerable"

        rows.append(
            {
                "scenario": scenario["scenario"],
                "portfolio_resilience_score": portfolio_resilience,
                "stance": stance,
                "portfolio_read_through": scenario["portfolio_read_through"],
                "most_resilient_names": ", ".join(resilient["ticker"].astype(str).tolist()),
                "most_vulnerable_names": ", ".join(vulnerable["ticker"].astype(str).tolist()),
                "largest_target_sector_weights": ", ".join([f"{s}: {w:.1%}" for s, w in target_sectors]) if target_sectors else "NA",
                "suggested_response": _scenario_response(scenario["scenario"], stance),
            }
        )
    return pd.DataFrame(rows)


def _scenario_response(scenario: str, stance: str) -> str:
    if scenario == "Market selloff":
        return "Keep adds incremental, use trim candidates as funding, and avoid forcing new risk until technicals stabilize." if stance != "Constructive" else "Portfolio has acceptable resilience; still phase into additions rather than buying all at once."
    if scenario == "Rate shock":
        return "Watch rate-sensitive sector exposure and avoid expanding long-duration names unless valuation support is strong." if stance != "Constructive" else "Portfolio is reasonably balanced for a higher-rate tape."
    if scenario == "Recession":
        return "Shift capital toward higher-quality defensive holdings and reduce weak cyclicals first." if stance != "Constructive" else "Portfolio quality looks adequate; monitor earnings revisions and credit-sensitive names."
    if scenario == "AI-led rally":
        return "Avoid underweighting high-quality momentum leaders if risk controls allow." if stance != "Constructive" else "Portfolio is well positioned for growth leadership, but monitor concentration."
    return "Monitor scenario-specific risk."


def build_portfolio_committee_summary(
    portfolio_summary: dict[str, Any],
    recommendation_table: pd.DataFrame | None,
    rebalance_table: pd.DataFrame | None,
    sector_allocation: pd.DataFrame | None,
    stress_scenarios: pd.DataFrame | None,
    openai_api_key: str = "",
    model_name: str = "gpt-4o-mini",
) -> str:
    fallback = _deterministic_committee_summary(
        portfolio_summary, recommendation_table, rebalance_table, sector_allocation, stress_scenarios
    )
    if not openai_api_key or OpenAI is None:
        return fallback

    try:
        client = OpenAI(api_key=openai_api_key)
        payload = {
            "task": (
                "Write a concise investment committee summary for the top of a portfolio manager dashboard. "
                "Use clean plain text only. Use this exact structure: Executive View, Recommended Positioning, "
                "Biggest Adds, Biggest Funding Sources, Sector Shift, Stress-Test Read-Through, Bottom Line. "
                "Use hyphen bullets only. Do not invent data."
            ),
            "portfolio_summary": portfolio_summary,
            "recommendations": _records(recommendation_table, 20),
            "rebalance": _records(rebalance_table, 20),
            "sector_allocation": _records(sector_allocation, 20),
            "stress_scenarios": _records(stress_scenarios, 10),
            "fallback_summary": fallback,
        }
        response = client.responses.create(
            model=model_name,
            input=[
                {"role": "system", "content": "You are a portfolio strategist. Respond in clean plain text only."},
                {"role": "user", "content": str(payload)},
            ],
        )
        text = getattr(response, "output_text", "") or ""
        return text.strip() or fallback
    except Exception as exc:
        return fallback + f"\n\nAI summary fallback note: AI request failed: {exc}"


def _records(df: pd.DataFrame | None, limit: int) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return df.head(limit).replace({np.nan: None}).to_dict(orient="records")


def _deterministic_committee_summary(
    portfolio_summary: dict[str, Any],
    recommendation_table: pd.DataFrame | None,
    rebalance_table: pd.DataFrame | None,
    sector_allocation: pd.DataFrame | None,
    stress_scenarios: pd.DataFrame | None,
) -> str:
    recs = recommendation_table.copy() if recommendation_table is not None else pd.DataFrame()
    reb = rebalance_table.copy() if rebalance_table is not None else pd.DataFrame()
    adds = recs[recs.get("final_action", pd.Series(dtype=str)).astype(str).isin(ADD_ACTIONS)] if not recs.empty else pd.DataFrame()
    trims = recs[recs.get("final_action", pd.Series(dtype=str)).astype(str).isin(TRIM_ACTIONS | EXIT_ACTIONS)] if not recs.empty else pd.DataFrame()

    best_adds = ", ".join(adds.head(4)["ticker"].astype(str).tolist()) if not adds.empty and "ticker" in adds else "None"
    funding = ", ".join(trims.head(4)["ticker"].astype(str).tolist()) if not trims.empty and "ticker" in trims else "None"

    largest_uses = "None"
    largest_sources = "None"
    if not reb.empty and "delta_weight" in reb.columns:
        tmp = reb.copy()
        tmp["delta_weight"] = pd.to_numeric(tmp["delta_weight"], errors="coerce").fillna(0.0)
        if "ticker" in tmp:
            largest_uses = ", ".join(tmp[tmp["delta_weight"] > 0].sort_values("delta_weight", ascending=False).head(3)["ticker"].astype(str).tolist()) or "None"
            largest_sources = ", ".join(tmp[tmp["delta_weight"] < 0].sort_values("delta_weight", ascending=True).head(3)["ticker"].astype(str).tolist()) or "None"

    sector_shift = "No sector shift available."
    if sector_allocation is not None and not sector_allocation.empty and "delta_weight" in sector_allocation.columns:
        sec = sector_allocation.copy()
        sec["delta_weight"] = pd.to_numeric(sec["delta_weight"], errors="coerce").fillna(0.0)
        up = sec.sort_values("delta_weight", ascending=False).head(1)
        down = sec.sort_values("delta_weight", ascending=True).head(1)
        if not up.empty and not down.empty:
            sector_shift = f"Largest increase: {up.iloc[0]['sector']} ({_pct(up.iloc[0]['delta_weight'])}); largest reduction: {down.iloc[0]['sector']} ({_pct(down.iloc[0]['delta_weight'])})."

    stress_line = "Stress scenarios are not available."
    if stress_scenarios is not None and not stress_scenarios.empty:
        stress_line = "; ".join(
            f"{r['scenario']}: {r['stance']}" for _, r in stress_scenarios.head(4).iterrows()
        )

    portfolio_value = portfolio_summary.get("portfolio_value", 0.0) if isinstance(portfolio_summary, dict) else 0.0
    regime = portfolio_summary.get("regime", "Unknown") if isinstance(portfolio_summary, dict) else "Unknown"
    benchmark = portfolio_summary.get("benchmark", "SPY") if isinstance(portfolio_summary, dict) else "SPY"

    return (
        "Executive View\n"
        f"- Portfolio value analyzed: {_money(portfolio_value)} versus benchmark {benchmark}. Macro regime: {regime}.\n"
        f"- Add/start candidates: {best_adds}. Funding or risk-reduction candidates: {funding}.\n\n"
        "Recommended Positioning\n"
        f"- Largest capital uses: {largest_uses}.\n"
        f"- Largest funding sources: {largest_sources}.\n"
        f"- Sector shift: {sector_shift}\n\n"
        "Stress-Test Read-Through\n"
        f"- {stress_line}\n\n"
        "Bottom Line\n"
        "- Use the rebalance as a staged implementation plan, not a blind one-click trade list. Prioritize higher-conviction adds, fund them with weaker trims/exits, and respect the position and sector caps."
    )


def make_export_excel(
    portfolio_summary: dict[str, Any],
    committee_summary: str,
    recommendation_table: pd.DataFrame | None,
    rebalance_table: pd.DataFrame | None,
    sector_allocation: pd.DataFrame | None,
    target_explanations: pd.DataFrame | None,
    stress_scenarios: pd.DataFrame | None,
    decision_audit_table: pd.DataFrame | None = None,
) -> bytes:
    """Return an XLSX workbook as bytes for Streamlit download_button."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame([portfolio_summary or {}]).to_excel(writer, sheet_name="Portfolio Summary", index=False)
        pd.DataFrame({"committee_summary": [committee_summary or ""]}).to_excel(writer, sheet_name="Committee Summary", index=False)
        _safe_to_excel(recommendation_table, writer, "Recommendations")
        _safe_to_excel(rebalance_table, writer, "Rebalance")
        _safe_to_excel(sector_allocation, writer, "Sector Allocation")
        _safe_to_excel(target_explanations, writer, "Target Explanations")
        _safe_to_excel(stress_scenarios, writer, "Stress Scenarios")
        _safe_to_excel(decision_audit_table, writer, "Decision Audit")

        workbook = writer.book
        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            for col_cells in sheet.columns:
                max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in col_cells)
                sheet.column_dimensions[col_cells[0].column_letter].width = min(max(max_len + 2, 12), 45)
    return output.getvalue()


def _safe_to_excel(df: pd.DataFrame | None, writer: pd.ExcelWriter, sheet_name: str) -> None:
    if df is None or df.empty:
        pd.DataFrame({"message": ["No data available"]}).to_excel(writer, sheet_name=sheet_name[:31], index=False)
    else:
        df.replace({np.nan: None}).to_excel(writer, sheet_name=sheet_name[:31], index=False)


def make_export_pdf(
    portfolio_summary: dict[str, Any],
    committee_summary: str,
    recommendation_table: pd.DataFrame | None,
    rebalance_table: pd.DataFrame | None,
    sector_allocation: pd.DataFrame | None,
    stress_scenarios: pd.DataFrame | None,
) -> bytes:
    """Return a simple PDF report as bytes for Streamlit download_button."""
    if SimpleDocTemplate is None:
        raise RuntimeError("reportlab is not installed. Add reportlab to requirements.txt to enable PDF export.")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        rightMargin=0.35 * inch,
        leftMargin=0.35 * inch,
        topMargin=0.35 * inch,
        bottomMargin=0.35 * inch,
    )
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("AI Portfolio Manager Recommendation Report", styles["Title"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(f"Portfolio Value: {_money((portfolio_summary or {}).get('portfolio_value', 0.0))}", styles["Normal"]))
    story.append(Paragraph(f"Benchmark: {(portfolio_summary or {}).get('benchmark', 'SPY')} | Regime: {(portfolio_summary or {}).get('regime', 'Unknown')}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))
    for block in str(committee_summary or "No summary available.").split("\n"):
        story.append(Paragraph(block if block.strip() else " ", styles["Normal"]))
    story.append(PageBreak())

    _add_pdf_table(story, styles, "Top Recommendations", recommendation_table, ["ticker", "sector", "final_action", "decision_reason", "decision_confidence", "composite_score", "current_weight"])
    story.append(PageBreak())
    _add_pdf_table(story, styles, "Recommended Rebalance", rebalance_table, ["ticker", "sector", "final_action", "rebalance_action", "current_weight", "target_weight", "delta_weight", "trade_value"])
    story.append(PageBreak())
    _add_pdf_table(story, styles, "Sector Allocation", sector_allocation, ["sector", "current_weight", "target_weight", "delta_weight"])
    story.append(PageBreak())
    _add_pdf_table(story, styles, "Stress Scenarios", stress_scenarios, ["scenario", "stance", "portfolio_resilience_score", "most_resilient_names", "most_vulnerable_names", "suggested_response"])

    doc.build(story)
    return buf.getvalue()


def _add_pdf_table(story: list[Any], styles: Any, title: str, df: pd.DataFrame | None, preferred_cols: list[str]) -> None:
    story.append(Paragraph(title, styles["Heading1"]))
    story.append(Spacer(1, 0.12 * inch))
    if df is None or df.empty:
        story.append(Paragraph("No data available.", styles["Normal"]))
        return
    work = df.copy().head(25)
    cols = [c for c in preferred_cols if c in work.columns]
    if not cols:
        cols = list(work.columns[:8])
    display = work[cols].copy()
    for col in display.columns:
        if col in {"current_weight", "target_weight", "delta_weight", "data_quality_score", "portfolio_resilience_score"}:
            display[col] = pd.to_numeric(display[col], errors="coerce").map(_pct)
        elif col in {"trade_value", "current_value", "target_value", "market_value"}:
            display[col] = pd.to_numeric(display[col], errors="coerce").map(_money)
        elif "score" in col:
            display[col] = pd.to_numeric(display[col], errors="coerce").map(_score)
        else:
            display[col] = display[col].astype(str).str.slice(0, 80)
    data = [list(display.columns)] + display.astype(str).values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
