from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

from langgraphagenticai.portfolio_manager.evidence_builder import safe_float, clean_text


def _normalize_weights(weights: pd.Series, target_sum: float) -> pd.Series:
    w = pd.to_numeric(weights, errors="coerce").fillna(0.0).clip(lower=0.0)
    total = float(w.sum())
    if target_sum <= 0:
        return w * 0.0
    if total <= 0:
        return pd.Series([target_sum / len(w)] * len(w), index=w.index) if len(w) else w
    return w / total * target_sum


def _apply_position_caps(weights: pd.Series, max_position_weight: float, target_sum: float, iterations: int = 20) -> pd.Series:
    if weights.empty:
        return weights
    w = _normalize_weights(weights, target_sum)
    cap = max_position_weight if max_position_weight and max_position_weight > 0 else 1.0
    for _ in range(iterations):
        over = w > cap + 1e-9
        if not over.any():
            break
        excess = float((w[over] - cap).sum())
        w[over] = cap
        room = (~over) & (w < cap - 1e-9)
        room_total = float(w[room].sum())
        if excess <= 1e-12 or not room.any() or room_total <= 0:
            break
        w.loc[room] = w.loc[room] + (w.loc[room] / room_total * excess)
    return _normalize_weights(w.clip(upper=cap), min(target_sum, cap * len(w)))


def _apply_sector_caps(df: pd.DataFrame, weights: pd.Series, max_sector_weight: float, target_sum: float, iterations: int = 20) -> pd.Series:
    if weights.empty or "sector" not in df.columns or not max_sector_weight or max_sector_weight <= 0:
        return _normalize_weights(weights, target_sum)
    w = _normalize_weights(weights, target_sum)
    sectors = df["sector"].fillna("Unclassified").astype(str)
    sector_cap = max_sector_weight
    for _ in range(iterations):
        sector_totals = w.groupby(sectors).sum()
        over_sectors = sector_totals[sector_totals > sector_cap + 1e-9]
        if over_sectors.empty:
            break
        excess_total = 0.0
        frozen = pd.Series(False, index=w.index)
        for sector, total in over_sectors.items():
            mask = sectors == sector
            if total > 0:
                scaled = w[mask] / total * sector_cap
                excess_total += float(w[mask].sum() - scaled.sum())
                w.loc[mask] = scaled
                frozen.loc[mask] = True
        room = ~frozen
        room_sector_totals = w.groupby(sectors).sum()
        room = room & sectors.map(lambda s: room_sector_totals.get(s, 0.0) < sector_cap - 1e-9)
        room_total = float(w[room].sum())
        if excess_total <= 1e-12 or not room.any() or room_total <= 0:
            break
        w.loc[room] = w.loc[room] + (w.loc[room] / room_total * excess_total)
    return _normalize_weights(w, min(target_sum, sector_cap * max(1, sectors.nunique())))


def validate_agentic_weights(
    recommendation_table: pd.DataFrame,
    portfolio_value: float | None,
    max_position_weight: float,
    max_sector_weight: float,
    cash_buffer: float,
    min_trade_weight_change: float = 0.0025,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Validate AI target weights, cap constraints, normalize totals, and calculate trades.

    This function intentionally does not make investment decisions. It only repairs math and
    makes constraint adjustments transparent.
    """
    if recommendation_table is None or recommendation_table.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, {"status": "empty"}

    df = recommendation_table.copy().reset_index(drop=True)
    for col in ["current_weight", "target_weight_proposed", "market_value", "shares", "last_price"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    if "sector" not in df.columns:
        df["sector"] = "Unclassified"
    df["sector"] = df["sector"].fillna("Unclassified").astype(str)

    investable_weight = max(0.0, min(1.0, 1.0 - float(cash_buffer or 0.0)))
    position_capacity = max_position_weight * len(df) if max_position_weight and max_position_weight > 0 else investable_weight
    sector_count = max(1, df["sector"].nunique())
    sector_capacity = max_sector_weight * sector_count if max_sector_weight and max_sector_weight > 0 and max_sector_weight < 1 else investable_weight
    feasible_invested_weight = max(0.0, min(investable_weight, position_capacity, sector_capacity))
    residual_cash_weight = max(0.0, 1.0 - feasible_invested_weight)
    proposed = df["target_weight_proposed"].clip(lower=0.0)
    if float(proposed.sum()) <= 0:
        proposed = df["current_weight"].clip(lower=0.0)
    proposed_norm = _normalize_weights(proposed, feasible_invested_weight)
    capped_pos = _apply_position_caps(proposed_norm, max_position_weight=max_position_weight, target_sum=feasible_invested_weight)
    capped_sector = _apply_sector_caps(df, capped_pos, max_sector_weight=max_sector_weight, target_sum=float(capped_pos.sum()))
    final_weights = _apply_position_caps(capped_sector, max_position_weight=max_position_weight, target_sum=float(capped_sector.sum()))

    if float(final_weights.sum()) > 0:
        final_weights = final_weights / float(final_weights.sum()) * feasible_invested_weight

    df["target_weight_raw_ai"] = proposed
    df["target_weight"] = final_weights
    df["delta_weight"] = df["target_weight"] - df["current_weight"]

    value = safe_float(portfolio_value, 0.0) or float(df["market_value"].sum())
    df["current_value"] = df["market_value"]
    df["target_value"] = df["target_weight"] * value if value > 0 else 0.0
    df["trade_value"] = df["target_value"] - df["current_value"]
    df["current_shares"] = df["shares"]
    df["target_shares"] = np.where(df["last_price"] > 0, df["target_value"] / df["last_price"], np.nan)
    df["share_change"] = df["target_shares"] - df["current_shares"]

    def classify(row: pd.Series) -> str:
        dw = safe_float(row.get("delta_weight"), 0.0) or 0.0
        action = clean_text(row.get("final_action"), "Hold")
        if abs(dw) < min_trade_weight_change:
            return "Hold / no trade"
        if action == "Sell" or row.get("target_weight", 0.0) <= 0.0001:
            return "Sell / exit"
        if dw > 0:
            return "Add / buy"
        return "Trim / sell"

    df["rebalance_action"] = df.apply(classify, axis=1)
    df["trade_direction"] = np.where(df["trade_value"] > 0, "Buy", np.where(df["trade_value"] < 0, "Sell", "No trade"))
    df["trade_priority"] = np.where(abs(df["delta_weight"]) >= 0.03, "High", np.where(abs(df["delta_weight"]) >= 0.01, "Medium", "Low"))

    flags = []
    for _, row in df.iterrows():
        row_flags = []
        if safe_float(row.get("target_weight_raw_ai"), 0.0) > max_position_weight + 1e-9:
            row_flags.append("AI target capped by max position")
        sector_total = float(df.loc[df["sector"] == row["sector"], "target_weight"].sum())
        if sector_total >= max_sector_weight - 1e-6 and max_sector_weight < 1:
            row_flags.append("sector cap active")
        if abs((safe_float(row.get("target_weight_raw_ai"), 0.0) or 0.0) - (safe_float(row.get("target_weight"), 0.0) or 0.0)) > 0.005:
            row_flags.append("validator adjusted AI weight")
        flags.append("; ".join(row_flags))
    df["constraint_flags"] = flags
    df["rebalance_reason"] = df.apply(
        lambda r: f"{r.get('final_action', 'Hold')}: {r.get('committee_reason', '')}"[:700], axis=1
    )

    rec_cols = [
        "ticker", "company_name", "asset_type", "sector", "industry", "final_action", "committee_conviction",
        "current_weight", "target_weight", "delta_weight", "trade_value", "share_change", "committee_reason",
        "key_risks", "monitoring_triggers", "composite_score", "fundamental_score", "valuation_score",
        "forward_score", "technical_score", "risk_score", "target_weight_raw_ai", "constraint_flags",
    ]
    recommendation_out = df[[c for c in rec_cols if c in df.columns]].copy()

    rebalance_cols = [
        "ticker", "final_action", "rebalance_action", "trade_direction", "current_weight", "target_weight",
        "delta_weight", "current_value", "target_value", "trade_value", "current_shares", "target_shares",
        "share_change", "last_price", "trade_priority", "constraint_flags", "rebalance_reason",
    ]
    rebalance_out = df[[c for c in rebalance_cols if c in df.columns]].copy()

    sector_current = df.groupby("sector", as_index=False)["current_weight"].sum().rename(columns={"current_weight": "current_weight"})
    sector_target = df.groupby("sector", as_index=False)["target_weight"].sum().rename(columns={"target_weight": "target_weight"})
    sector_table = sector_current.merge(sector_target, on="sector", how="outer").fillna(0.0)
    sector_table["delta_weight"] = sector_table["target_weight"] - sector_table["current_weight"]
    sector_table["current_value"] = sector_table["current_weight"] * value if value > 0 else 0.0
    sector_table["target_value"] = sector_table["target_weight"] * value if value > 0 else 0.0
    if residual_cash_weight > 0.0001:
        cash_rec = {col: None for col in recommendation_out.columns}
        cash_rec.update({
            "ticker": "CASH", "company_name": "Residual cash / dry powder", "asset_type": "Cash",
            "sector": "Cash", "industry": "Cash", "final_action": "Hold", "committee_conviction": "Medium",
            "current_weight": max(0.0, 1.0 - float(df["current_weight"].sum())),
            "target_weight": residual_cash_weight,
            "delta_weight": residual_cash_weight - max(0.0, 1.0 - float(df["current_weight"].sum())),
            "trade_value": 0.0, "share_change": 0.0,
            "committee_reason": "Cash balance created by explicit cash buffer or infeasible max position/sector caps.",
            "key_risks": "Cash drag if markets rally.",
            "monitoring_triggers": "Deploy if new ideas pass committee review or caps are relaxed.",
            "target_weight_raw_ai": residual_cash_weight,
            "constraint_flags": "residual cash from constraint validation",
        })
        recommendation_out = pd.concat([recommendation_out, pd.DataFrame([cash_rec])], ignore_index=True)

        cash_rb = {col: None for col in rebalance_out.columns}
        cash_rb.update({
            "ticker": "CASH", "final_action": "Hold", "rebalance_action": "Hold cash", "trade_direction": "No trade",
            "current_weight": max(0.0, 1.0 - float(df["current_weight"].sum())),
            "target_weight": residual_cash_weight,
            "delta_weight": residual_cash_weight - max(0.0, 1.0 - float(df["current_weight"].sum())),
            "current_value": 0.0, "target_value": residual_cash_weight * value if value > 0 else 0.0,
            "trade_value": 0.0, "current_shares": 0.0, "target_shares": 0.0, "share_change": 0.0,
            "last_price": 1.0, "trade_priority": "Low", "constraint_flags": "residual cash from constraint validation",
            "rebalance_reason": "Residual cash from cash target or infeasible concentration caps.",
        })
        rebalance_out = pd.concat([rebalance_out, pd.DataFrame([cash_rb])], ignore_index=True)
        cash_sector = {
            "sector": "Cash", "current_weight": max(0.0, 1.0 - float(df["current_weight"].sum())),
            "target_weight": residual_cash_weight,
        }
        cash_sector["delta_weight"] = cash_sector["target_weight"] - cash_sector["current_weight"]
        cash_sector["current_value"] = cash_sector["current_weight"] * value if value > 0 else 0.0
        cash_sector["target_value"] = cash_sector["target_weight"] * value if value > 0 else 0.0
        sector_table = pd.concat([sector_table, pd.DataFrame([cash_sector])], ignore_index=True)

    sector_table = sector_table.sort_values("target_weight", ascending=False).reset_index(drop=True)

    diagnostics = {
        "status": "validated",
        "target_weight_sum": float(recommendation_out["target_weight"].fillna(0).sum()) if "target_weight" in recommendation_out.columns else float(df["target_weight"].sum()),
        "cash_buffer": float(cash_buffer or 0.0),
        "residual_cash_weight": residual_cash_weight,
        "investable_weight": investable_weight,
        "feasible_invested_weight": feasible_invested_weight,
        "max_position_weight": max_position_weight,
        "max_sector_weight": max_sector_weight,
        "validator_adjusted_names": int(df["constraint_flags"].astype(str).str.contains("validator adjusted", regex=False).sum()),
        "positions_over_cap_after_validation": int((df["target_weight"] > max_position_weight + 1e-6).sum()),
        "sectors_over_cap_after_validation": int(((sector_table["sector"].astype(str).str.lower() != "cash") & (sector_table["target_weight"] > max_sector_weight + 1e-6)).sum()) if max_sector_weight < 1 else 0,
    }
    return recommendation_out, rebalance_out, sector_table, diagnostics
