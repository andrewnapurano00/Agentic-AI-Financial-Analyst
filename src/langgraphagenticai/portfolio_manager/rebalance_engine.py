from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


ACTION_BASE_SHIFT = {
    "Strong Buy": 0.45,
    "Buy": 0.30,
    "Add": 0.22,
    "Start / Rotate In": 0.18,
    "Hold": 0.00,
    "Watchlist": -0.03,
    "Trim": -0.28,
    "Sell": -0.65,
    "Exit": -1.00,
    "Avoid": -1.00,
}

CONFIDENCE_MULTIPLIER = {
    "low": 0.75,
    "medium": 1.00,
    "high": 1.18,
    "very high": 1.30,
}

CONSENSUS_MULTIPLIER = {
    "conflicted": 0.80,
    "mixed": 0.95,
    "constructive": 1.05,
    "constructive but debated": 1.00,
    "aligned": 1.12,
    "aligned bullish": 1.12,
    "strong": 1.18,
    "risk constrained": 0.82,
    "cautious / mixed": 0.82,
    "defensive / bearish": 0.70,
}

SIZING_MULTIPLIER = {
    "starter": 0.85,
    "small": 0.92,
    "small / defensive": 0.82,
    "normal": 1.00,
    "medium": 1.08,
    "large": 1.18,
    "overweight": 1.25,
}

ACTION_PRIORITY = {
    "Strong Buy": 6,
    "Buy": 5,
    "Add": 4,
    "Start / Rotate In": 4,
    "Hold": 3,
    "Watchlist": 2,
    "Trim": 1,
    "Sell": 0,
    "Exit": 0,
    "Avoid": 0,
}

ENTRY_ACTIONS = {"Strong Buy", "Buy", "Add", "Start / Rotate In"}
EXIT_ACTIONS = {"Avoid", "Exit", "Sell"}
REDUCE_ACTIONS = {"Trim"}
KEEP_ACTIONS = ENTRY_ACTIONS | {"Hold"}
REDISTRIBUTABLE_ACTIONS = KEEP_ACTIONS


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def _clean_text(x: Any, default: str = "") -> str:
    if x is None:
        return default
    s = str(x).strip()
    return s if s else default


def _risk_penalty(risk_fit_score: float) -> float:
    if risk_fit_score <= 0:
        return 0.90
    if risk_fit_score < 2.5:
        return 0.72
    if risk_fit_score < 4.0:
        return 0.84
    if risk_fit_score < 5.5:
        return 0.94
    if risk_fit_score < 7.0:
        return 1.00
    return 1.05


def _starter_weight(
    confidence: str,
    consensus_state: str,
    suggested_sizing: str,
    starter_min_weight: float,
) -> float:
    base = starter_min_weight
    base *= CONFIDENCE_MULTIPLIER.get(confidence.lower(), 1.00)
    base *= CONSENSUS_MULTIPLIER.get(consensus_state.lower(), 1.00)
    base *= SIZING_MULTIPLIER.get(suggested_sizing.lower(), 1.00)
    return max(starter_min_weight, base)


def _make_position_cap(
    action: str,
    confidence: str,
    consensus: str,
    max_position_weight: float,
) -> float:
    position_cap = max_position_weight
    if (
        action in {"Strong Buy", "Buy", "Add"}
        and confidence in {"high", "very high"}
        and consensus in {"aligned", "aligned bullish", "strong"}
    ):
        position_cap = min(max_position_weight + 0.03, 0.25)
    return position_cap


def _conviction_score(row: pd.Series) -> float:
    action = _clean_text(row.get("final_action"), "Hold")
    confidence = _clean_text(row.get("decision_confidence"), "medium").lower()
    consensus = _clean_text(row.get("consensus_state"), "mixed").lower()
    sizing = _clean_text(row.get("suggested_sizing"), "normal").lower()
    composite = _safe_float(row.get("composite_score"), 0.0)
    peer_reliability = _safe_float(row.get("peer_reliability"), 0.6)
    data_quality_score = _safe_float(row.get("data_quality_score"), 0.65)
    risk_score = _safe_float(row.get("risk_fit_score"), 0.0)

    action_component = ACTION_PRIORITY.get(action, 3) / 6.0
    confidence_component = {
        "low": 0.35,
        "medium": 0.55,
        "high": 0.78,
        "very high": 0.92,
    }.get(confidence, 0.55)
    consensus_component = {
        "conflicted": 0.25,
        "mixed": 0.45,
        "constructive": 0.60,
        "constructive but debated": 0.55,
        "aligned": 0.80,
        "aligned bullish": 0.84,
        "strong": 0.92,
        "risk constrained": 0.35,
        "cautious / mixed": 0.32,
        "defensive / bearish": 0.20,
    }.get(consensus, 0.45)
    sizing_component = {
        "starter": 0.35,
        "small": 0.45,
        "small / defensive": 0.32,
        "normal": 0.60,
        "medium": 0.72,
        "large": 0.84,
        "overweight": 0.95,
    }.get(sizing, 0.60)
    composite_component = np.clip(composite / 10.0, 0.0, 1.0)
    risk_component = np.clip(_risk_penalty(risk_score), 0.65, 1.10) / 1.10

    conviction = (
        0.28 * action_component
        + 0.18 * confidence_component
        + 0.16 * consensus_component
        + 0.12 * sizing_component
        + 0.18 * composite_component
        + 0.08 * risk_component
    )
    conviction *= 0.88 + 0.08 * np.clip(peer_reliability, 0.0, 1.0) + 0.04 * np.clip(data_quality_score, 0.0, 1.0)
    return float(np.clip(conviction, 0.0, 1.0))


def _target_band(conviction: float, starter_min_weight: float, max_position_weight: float) -> tuple[str, float]:
    starter = max(starter_min_weight, min(0.035, max_position_weight * 0.35))
    standard = min(max_position_weight * 0.65, max_position_weight)
    full = max_position_weight

    if conviction >= 0.82:
        return "full", full
    if conviction >= 0.68:
        return "standard", max(standard, starter)
    if conviction >= 0.52:
        return "starter", starter
    return "watch", 0.0


def _build_constraints(row: pd.Series, target: float, position_cap: float, max_position_weight: float) -> str:
    flags: list[str] = []
    current_weight = _safe_float(row.get("current_weight"), 0.0)
    risk_fit = _safe_float(row.get("risk_fit_score"), 0.0)
    if target >= position_cap - 1e-6 and position_cap < 0.25:
        flags.append("position cap")
    if current_weight > max_position_weight * 0.95:
        flags.append("existing concentration")
    if risk_fit > 0 and risk_fit < 4.0:
        flags.append("risk limited")
    if _clean_text(row.get("consensus_state"), "mixed").lower() in {"conflicted", "risk constrained"}:
        flags.append("consensus caution")
    return " | ".join(flags)


def _initial_target_for_row(
    row: pd.Series,
    max_position_weight: float,
    starter_min_weight: float,
) -> dict[str, Any]:
    action = _clean_text(row.get("final_action"), "Hold")
    confidence = _clean_text(row.get("decision_confidence"), "medium").lower()
    consensus = _clean_text(row.get("consensus_state"), "mixed").lower()
    sizing = _clean_text(row.get("suggested_sizing"), "normal").lower()

    current_weight = _safe_float(row.get("current_weight"), 0.0)
    shares = _safe_float(row.get("shares"), 0.0)
    last_price = _safe_float(row.get("last_price"), 0.0)
    risk_mult = _risk_penalty(_safe_float(row.get("risk_fit_score"), 0.0))
    data_quality_score = _safe_float(row.get("data_quality_score"), 0.65)
    data_quality_label = _clean_text(row.get("data_quality_label"), "medium").lower()
    conviction = _conviction_score(row)
    band, band_weight = _target_band(conviction, starter_min_weight, max_position_weight)

    raw_agent_target = row.get("agentic_target_weight", row.get("ai_target_weight", row.get("recommended_target_weight", np.nan)))
    agentic_target = _safe_float(raw_agent_target, np.nan)
    uses_agentic_target = not pd.isna(agentic_target)

    confidence_mult = CONFIDENCE_MULTIPLIER.get(confidence, 1.0)
    consensus_mult = CONSENSUS_MULTIPLIER.get(consensus, 1.0)
    sizing_mult = SIZING_MULTIPLIER.get(sizing, 1.0)
    position_cap = _make_position_cap(action, confidence, consensus, max_position_weight)

    if data_quality_score <= 0.45:
        position_cap = min(position_cap, max(starter_min_weight, max_position_weight * 0.45))
    elif data_quality_score < 0.60:
        position_cap = min(position_cap, max(starter_min_weight, max_position_weight * 0.70))

    if current_weight > max_position_weight * 0.90:
        concentration_penalty = 0.85
    elif current_weight > max_position_weight * 0.75:
        concentration_penalty = 0.93
    else:
        concentration_penalty = 1.0

    multiplier = confidence_mult * consensus_mult * sizing_mult * risk_mult * concentration_penalty
    base_shift = ACTION_BASE_SHIFT.get(action, 0.0)
    owned = current_weight > 0

    if uses_agentic_target:
        # In v4 the LLM portfolio committee owns the target weight.
        # The max position setting is a cap, not a target. We do not convert
        # Add/Hold/Trim labels into default equal weights here.
        target = float(np.clip(agentic_target, 0.0, position_cap))
        rationale = _clean_text(row.get("agentic_target_weight_rationale"), "agentic committee target weight")
        funding_role = _clean_text(row.get("allocation_role"), "agentic allocation")
        if action in EXIT_ACTIONS:
            target = min(target, current_weight * 0.15 if current_weight > 0 else 0.0)
            funding_role = "funding source"
    elif action in EXIT_ACTIONS:
        target = 0.0
        rationale = "deallocate"
        funding_role = "funding source"
    elif action in REDUCE_ACTIONS:
        trim_floor = max(0.0, min(current_weight * 0.70, band_weight))
        trim_ceiling = current_weight * (0.72 if conviction < 0.55 else 0.85)
        target = min(trim_ceiling, current_weight)
        target = max(trim_floor, target)
        rationale = "trim to conviction band"
        funding_role = "funding source"
    elif not owned and action in ENTRY_ACTIONS:
        entry_floor = _starter_weight(confidence, consensus, sizing, starter_min_weight) * risk_mult
        entry_target = max(entry_floor, band_weight)
        if action == "Start / Rotate In":
            entry_target = min(entry_target, max(entry_floor, starter_min_weight * 1.35))
        target = entry_target
        rationale = f"new {band} position"
        funding_role = "capital use"
    else:
        shifted = current_weight * (1.0 + float(np.clip(base_shift * multiplier, -1.0, 0.80)))
        if action == "Hold":
            lower_band = current_weight * 0.97
            upper_band = min(current_weight * 1.04, position_cap)
            target = min(max(shifted, lower_band), upper_band)
            if current_weight > position_cap:
                target = min(target, position_cap)
            rationale = "hold within band"
            funding_role = "neutral"
        else:
            base_target = max(current_weight, band_weight)
            target = max(base_target, shifted)
            if action == "Add" and conviction < 0.60:
                target = min(target, max(current_weight, starter_min_weight * 1.5))
            rationale = f"build toward {band} weight"
            funding_role = "capital use"

    target = float(np.clip(target, 0.0, position_cap))
    constraint_flags = _build_constraints(row, target, position_cap, max_position_weight)

    return {
        "ticker": row.get("ticker"),
        "sector": row.get("sector", "Unknown"),
        "shares": shares,
        "last_price": last_price,
        "current_weight": current_weight,
        "final_action": action,
        "decision_confidence": confidence,
        "consensus_state": consensus,
        "suggested_sizing": sizing,
        "risk_fit_score": _safe_float(row.get("risk_fit_score"), 0.0),
        "data_quality_score": data_quality_score,
        "data_quality_label": data_quality_label,
        "composite_score": _safe_float(row.get("composite_score"), 0.0),
        "peer_reliability": _safe_float(row.get("peer_reliability"), 0.0),
        "position_cap": position_cap,
        "conviction_score": conviction,
        "target_band": band,
        "target_weight_raw": target,
        "uses_agentic_target": bool(uses_agentic_target),
        "rebalance_reason": rationale,
        "funding_role": funding_role,
        "constraint_flags": constraint_flags,
    }


def _allocate_budget(out: pd.DataFrame, target_total_weight: float) -> pd.DataFrame:
    if out.empty:
        return out

    result = out.copy()
    result["target_weight"] = result["target_weight_raw"].clip(lower=0.0)

    agentic_mode = bool(result.get("uses_agentic_target", pd.Series(False, index=result.index)).fillna(False).any())

    # Agentic allocation mode: LLM target weights are the source of truth.
    # We only scale down if the committee allocated more than the investable budget.
    # We do NOT scale up to fill unused cash, because that recreates deterministic
    # equal-weight/max-weight behavior and overrides the agents' conviction sizing.
    if agentic_mode:
        total_target = float(result["target_weight"].sum())
        if total_target > target_total_weight + 1e-12 and total_target > 0:
            result["target_weight"] = result["target_weight"] * (target_total_weight / total_target)
            flags = result["constraint_flags"].astype(str).replace("", np.nan).fillna("")
            result["constraint_flags"] = flags.map(lambda x: (x + " | scaled to cash budget").strip(" |"))
        result["target_weight"] = result[["target_weight", "position_cap"]].min(axis=1).clip(lower=0.0)
        return result

    current_total = float(result["current_weight"].sum())
    external_cash = max(0.0, target_total_weight - current_total)

    decreases = (result["current_weight"] - result["target_weight"]).clip(lower=0.0)
    increases = (result["target_weight"] - result["current_weight"]).clip(lower=0.0)

    funded_by_trims = float(decreases.sum())
    growth_need = float(increases.sum())
    total_budget = funded_by_trims + external_cash

    if growth_need > total_budget + 1e-12:
        grow_mask = increases > 0
        grow_room = increases[grow_mask]
        grow_priority = (
            result.loc[grow_mask, "conviction_score"].clip(lower=0.05)
            * result.loc[grow_mask, "final_action"].map(ACTION_PRIORITY).fillna(1).clip(lower=1)
        )
        weighted_need = grow_room * grow_priority.values
        weighted_need_sum = float(weighted_need.sum())
        scaled_growth = grow_room * (total_budget / weighted_need_sum) * grow_priority.values if weighted_need_sum > 0 else grow_room * 0.0
        result.loc[grow_mask, "target_weight"] = result.loc[grow_mask, "current_weight"] + scaled_growth.values
    elif total_budget > growth_need + 1e-12:
        surplus = total_budget - growth_need
        eligible = (
            result["final_action"].isin(ENTRY_ACTIONS)
            & (result["target_weight"] < result["position_cap"])
        )
        if eligible.any() and surplus > 1e-12:
            room = (result.loc[eligible, "position_cap"] - result.loc[eligible, "target_weight"]).clip(lower=0.0)
            weights = room * result.loc[eligible, "conviction_score"].clip(lower=0.05)
            weight_sum = float(weights.sum())
            if weight_sum > 0:
                addl = np.minimum(room.values, surplus * (weights / weight_sum).values)
                result.loc[eligible, "target_weight"] += addl

    result["target_weight"] = result[["target_weight", "position_cap"]].min(axis=1).clip(lower=0.0)
    return result

def _apply_sector_cap(df: pd.DataFrame, max_sector_weight: float) -> pd.DataFrame:
    if df.empty or "sector" not in df.columns:
        return df

    out = df.copy()
    out["target_weight"] = out["target_weight"].clip(lower=0.0)
    max_sector_weight = max(0.0, max_sector_weight)
    agentic_mode = bool(out.get("uses_agentic_target", pd.Series(False, index=out.index)).fillna(False).any())

    for _ in range(10):
        sector_totals = out.groupby("sector", dropna=False)["target_weight"].sum()
        breaches = sector_totals[sector_totals > max_sector_weight + 1e-12]
        if breaches.empty:
            break

        freed_total = 0.0
        for sector_name, sector_total in breaches.items():
            mask = out["sector"] == sector_name
            if not mask.any() or sector_total <= 0:
                continue
            scale = max_sector_weight / sector_total
            reduced = out.loc[mask, "target_weight"] * scale
            freed_total += float(out.loc[mask, "target_weight"].sum() - reduced.sum())
            out.loc[mask, "target_weight"] = reduced.values
            flags = out.loc[mask, "constraint_flags"].astype(str).replace("", np.nan).fillna("")
            out.loc[mask, "constraint_flags"] = flags.map(lambda x: (x + " | sector cap").strip(" |"))

        # In agentic allocation mode, sector-cap reductions become cash. Do not
        # auto-redistribute them, because that would override the committee's sizing.
        if agentic_mode or freed_total <= 1e-12:
            break

        eligible = (
            out["target_weight"] < out["position_cap"]
        ) & out["final_action"].isin(REDISTRIBUTABLE_ACTIONS)
        if not eligible.any():
            break

        room = (out.loc[eligible, "position_cap"] - out.loc[eligible, "target_weight"]).clip(lower=0.0)
        weights = room * out.loc[eligible, "conviction_score"].clip(lower=0.05)
        weight_sum = float(weights.sum())
        if weight_sum <= 0:
            break
        add_back = np.minimum(room.values, freed_total * (weights / weight_sum).values)
        out.loc[eligible, "target_weight"] += add_back

    return out

def _normalize_to_total(out: pd.DataFrame, target_total_weight: float) -> pd.DataFrame:
    if out.empty:
        return out
    result = out.copy()
    total = float(result["target_weight"].sum())
    if total <= 0:
        return result

    if total > target_total_weight + 1e-12:
        scale = target_total_weight / total
        result["target_weight"] = result["target_weight"] * scale
        result["target_weight"] = result[["target_weight", "position_cap"]].min(axis=1).clip(lower=0.0)
        return result

    shortage = target_total_weight - total
    if shortage <= 1e-12:
        return result

    eligible = (
        (result["target_weight"] < result["position_cap"])
        & result["final_action"].isin(ENTRY_ACTIONS | {"Hold"})
        & ~result["final_action"].isin(REDUCE_ACTIONS | EXIT_ACTIONS)
    )
    if not eligible.any():
        return result

    room = (result.loc[eligible, "position_cap"] - result.loc[eligible, "target_weight"]).clip(lower=0.0)
    weights = room * result.loc[eligible, "conviction_score"].clip(lower=0.05)
    weight_sum = float(weights.sum())
    if weight_sum <= 0:
        return result

    addl = np.minimum(room.values, shortage * (weights / weight_sum).values)
    result.loc[eligible, "target_weight"] += addl
    return result


def _suppress_small_trades(out: pd.DataFrame, min_trade_weight_change: float) -> pd.DataFrame:
    if out.empty:
        return out
    result = out.copy()
    small_mask = (
        (result["current_weight"] > 0)
        & (~result["final_action"].isin(EXIT_ACTIONS))
        & ((result["target_weight"] - result["current_weight"]).abs() < min_trade_weight_change)
    )
    result.loc[small_mask, "target_weight"] = result.loc[small_mask, "current_weight"]
    flags = result.loc[small_mask, "constraint_flags"].astype(str).replace("", np.nan).fillna("")
    result.loc[small_mask, "constraint_flags"] = flags.map(lambda x: (x + " | turnover threshold").strip(" |"))
    return result


def _normalize_agentic_targets_to_budget(out: pd.DataFrame, target_total_weight: float, max_sector_weight: float) -> pd.DataFrame:
    """Make agentic targets arithmetically usable while preserving LLM ranking.

    The LLM determines relative conviction and raw target weights. This function only
    performs portfolio math: scale down if over budget, allocate residual by conviction
    where there is cap room, and leave the remainder as CASH when caps make 100% impossible.
    """
    if out.empty:
        return out
    result = out.copy()
    result["target_weight"] = pd.to_numeric(result["target_weight"], errors="coerce").fillna(0.0).clip(lower=0.0)
    result["position_cap"] = pd.to_numeric(result["position_cap"], errors="coerce").fillna(0.0).clip(lower=0.0)

    # If over the security budget, scale down proportionally, then reapply caps.
    total = float(result["target_weight"].sum())
    if total > target_total_weight + 1e-12 and total > 0:
        result["target_weight"] *= target_total_weight / total
        result["target_weight"] = result[["target_weight", "position_cap"]].min(axis=1).clip(lower=0.0)
        flags = result["constraint_flags"].astype(str).replace("", np.nan).fillna("")
        result["constraint_flags"] = flags.map(lambda x: (x + " | scaled to budget").strip(" |"))

    # If under budget, distribute only to names the committee did not mark as funding/exit.
    # This is conviction weighted, not equal weighted, and respects security/sector caps.
    for _ in range(25):
        total = float(result["target_weight"].sum())
        shortage = target_total_weight - total
        if shortage <= 1e-8:
            break
        eligible = ~result["final_action"].isin(EXIT_ACTIONS | REDUCE_ACTIONS)
        eligible &= result["target_weight"] < result["position_cap"] - 1e-9
        if not eligible.any():
            break

        rooms = (result.loc[eligible, "position_cap"] - result.loc[eligible, "target_weight"]).clip(lower=0.0)
        # Sector remaining room.
        sector_room = pd.Series(index=result.loc[eligible].index, dtype=float)
        sector_totals = result.groupby("sector", dropna=False)["target_weight"].sum().to_dict()
        for idx, row in result.loc[eligible].iterrows():
            remaining = max(0.0, max_sector_weight - float(sector_totals.get(row.get("sector"), 0.0)))
            sector_room.loc[idx] = min(float(rooms.loc[idx]), remaining)
        rooms = sector_room.clip(lower=0.0)
        eligible_idx = rooms[rooms > 1e-9].index
        if len(eligible_idx) == 0:
            break

        priorities = (
            result.loc[eligible_idx, "conviction_score"].clip(lower=0.05)
            * result.loc[eligible_idx, "final_action"].map(ACTION_PRIORITY).fillna(3).clip(lower=1)
        )
        weights = rooms.loc[eligible_idx] * priorities
        wsum = float(weights.sum())
        if wsum <= 0:
            break
        add = np.minimum(rooms.loc[eligible_idx].values, shortage * (weights / wsum).values)
        if float(np.sum(add)) <= 1e-10:
            break
        result.loc[eligible_idx, "target_weight"] += add
        flags = result.loc[eligible_idx, "constraint_flags"].astype(str).replace("", np.nan).fillna("")
        result.loc[eligible_idx, "constraint_flags"] = flags.map(lambda x: (x + " | residual allocated by agent conviction").strip(" |"))

    return result


def _append_cash_row_if_needed(out: pd.DataFrame, target_total_weight: float, portfolio_value: float) -> pd.DataFrame:
    if out.empty:
        return out
    invested = float(pd.to_numeric(out["target_weight"], errors="coerce").fillna(0.0).sum())
    residual_cash = max(0.0, 1.0 - invested)
    # Always include cash when meaningful so total portfolio weights visibly add to 100%.
    if residual_cash <= 1e-5:
        return out
    cash_row = {col: None for col in out.columns}
    cash_row.update({
        "ticker": "CASH",
        "sector": "Cash / Unallocated",
        "final_action": "Hold",
        "rebalance_action": "Hold cash",
        "decision_confidence": "high",
        "consensus_state": "constraint-aware",
        "suggested_sizing": "cash buffer",
        "target_band": "cash",
        "uses_agentic_target": True,
        "funding_role": "cash / dry powder",
        "rebalance_reason": "Residual cash after agent targets, position caps, sector caps, and requested cash buffer.",
        "constraint_flags": "cash row added so target weights sum to 100%",
        "conviction_score": 0.0,
        "current_weight": max(0.0, 1.0 - float(pd.to_numeric(out["current_weight"], errors="coerce").fillna(0.0).sum())),
        "target_weight": residual_cash,
        "delta_weight": residual_cash - max(0.0, 1.0 - float(pd.to_numeric(out["current_weight"], errors="coerce").fillna(0.0).sum())),
        "current_value": max(0.0, 1.0 - float(pd.to_numeric(out["current_weight"], errors="coerce").fillna(0.0).sum())) * portfolio_value,
        "target_value": residual_cash * portfolio_value,
        "trade_value": (residual_cash - max(0.0, 1.0 - float(pd.to_numeric(out["current_weight"], errors="coerce").fillna(0.0).sum()))) * portfolio_value,
        "current_shares": 0,
        "target_shares": 0,
        "share_change": 0,
        "risk_fit_score": 0.0,
        "data_quality_score": 1.0,
        "data_quality_label": "high",
        "trade_priority": 7,
    })
    return pd.concat([out, pd.DataFrame([cash_row])], ignore_index=True)


def compute_recommended_rebalance(
    recommendation_table: pd.DataFrame,
    portfolio_value: float | None = None,
    cash_buffer: float = 0.00,
    max_position_weight: float = 0.18,
    max_sector_weight: float = 0.55,
    starter_min_weight: float = 0.025,
    min_trade_weight_change: float = 0.0025,
) -> pd.DataFrame:
    """
    Builds target portfolio weights from the recommendation matrix.

    Expected columns in recommendation_table:
    - ticker, sector, shares, last_price, current_weight, final_action

    Optional but used if present:
    - decision_confidence, consensus_state, suggested_sizing, risk_fit_score,
      composite_score, peer_reliability
    """

    if recommendation_table is None or recommendation_table.empty:
        return pd.DataFrame()

    work = recommendation_table.copy()

    for col in ["shares", "last_price", "current_weight", "risk_fit_score", "data_quality_score", "composite_score", "peer_reliability"]:
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
        else:
            work[col] = 0.0

    if portfolio_value is None or portfolio_value <= 0:
        derived_value = (work["shares"] * work["last_price"]).sum()
        portfolio_value = float(derived_value) if derived_value > 0 else 1.0

    target_total_weight = min(max(0.0, 1.0 - float(cash_buffer)), 1.0)

    current_total = float(work["current_weight"].sum())
    if current_total > 1.20:
        work["current_weight"] = work["current_weight"] / 100.0
        current_total = float(work["current_weight"].sum())
    if current_total <= 0:
        work["current_weight"] = 0.0

    if "sector" not in work.columns:
        work["sector"] = "Unknown"
    if "data_quality_label" not in work.columns:
        work["data_quality_label"] = "medium"

    raw_targets = [
        _initial_target_for_row(
            row=row,
            max_position_weight=max_position_weight,
            starter_min_weight=starter_min_weight,
        )
        for _, row in work.iterrows()
    ]
    out = pd.DataFrame(raw_targets)

    if out.empty:
        return out

    out = _allocate_budget(out, target_total_weight=target_total_weight)
    out = _apply_sector_cap(out, max_sector_weight=max_sector_weight)
    out = _suppress_small_trades(out, min_trade_weight_change=min_trade_weight_change)

    agentic_mode = bool(out.get("uses_agentic_target", pd.Series(False, index=out.index)).fillna(False).any())
    if agentic_mode:
        out = _normalize_agentic_targets_to_budget(out, target_total_weight=target_total_weight, max_sector_weight=max_sector_weight)
        out = _apply_sector_cap(out, max_sector_weight=max_sector_weight)
    else:
        out = _normalize_to_total(out, target_total_weight=target_total_weight)

    out["delta_weight"] = out["target_weight"] - out["current_weight"]
    out["current_value"] = out["current_weight"] * portfolio_value
    out["target_value"] = out["target_weight"] * portfolio_value
    out["trade_value"] = out["target_value"] - out["current_value"]

    out["current_shares"] = pd.to_numeric(out["shares"], errors="coerce").fillna(0.0)
    out["target_shares"] = np.where(
        out["last_price"] > 0,
        np.round(out["target_value"] / out["last_price"]).astype(int),
        0,
    )
    out["share_change"] = out["target_shares"] - out["current_shares"]

    def classify_trade(delta_weight: float, action: str, current_weight: float) -> str:
        if action in EXIT_ACTIONS and current_weight > 0:
            return "Exit"
        if abs(delta_weight) < min_trade_weight_change:
            return "Hold"
        if current_weight <= 0 and delta_weight >= min_trade_weight_change:
            return "Open position"
        if delta_weight >= 0.05:
            return "Increase meaningfully"
        if delta_weight >= min_trade_weight_change:
            return "Increase slightly"
        if delta_weight <= -0.05:
            return "Trim meaningfully"
        if delta_weight <= -min_trade_weight_change:
            return "Trim slightly"
        return "Hold"

    out["rebalance_action"] = [
        classify_trade(dw, act, cw)
        for dw, act, cw in zip(out["delta_weight"], out["final_action"], out["current_weight"])
    ]

    out["trade_priority"] = np.select(
        [
            out["rebalance_action"].eq("Exit"),
            out["rebalance_action"].eq("Trim meaningfully"),
            out["rebalance_action"].eq("Open position"),
            out["rebalance_action"].eq("Increase meaningfully"),
            out["rebalance_action"].eq("Trim slightly"),
            out["rebalance_action"].eq("Increase slightly"),
        ],
        [0, 1, 2, 3, 4, 5],
        default=6,
    )

    keep_cols = [
        "ticker",
        "sector",
        "final_action",
        "rebalance_action",
        "decision_confidence",
        "consensus_state",
        "suggested_sizing",
        "target_band",
        "uses_agentic_target",
        "funding_role",
        "rebalance_reason",
        "constraint_flags",
        "conviction_score",
        "current_weight",
        "target_weight",
        "delta_weight",
        "current_value",
        "target_value",
        "trade_value",
        "current_shares",
        "target_shares",
        "share_change",
        "risk_fit_score",
        "data_quality_score",
        "data_quality_label",
        "trade_priority",
    ]

    out = out[keep_cols].copy()
    out = _append_cash_row_if_needed(out, target_total_weight=target_total_weight, portfolio_value=portfolio_value)
    out = out.sort_values(["trade_priority", "delta_weight"], ascending=[True, False]).reset_index(drop=True)

    return out



