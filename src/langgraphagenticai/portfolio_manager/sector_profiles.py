from __future__ import annotations

DEFAULT_PROFILE = {
    "weights": {
        "fundamental": 0.32,
        "valuation": 0.20,
        "technical": 0.17,
        "catalyst": 0.09,
        "earnings": 0.12,
        "risk_fit": 0.10,
    },
    "thresholds": {
        "min_market_cap": 1_000_000_000,
        "max_position": 0.18,
    },
}

SECTOR_PROFILES = {
    "Technology": {
        "weights": {"fundamental": 0.31, "valuation": 0.18, "technical": 0.19, "catalyst": 0.09, "earnings": 0.13, "risk_fit": 0.10},
    },
    "Financial Services": {
        "weights": {"fundamental": 0.36, "valuation": 0.18, "technical": 0.13, "catalyst": 0.08, "earnings": 0.13, "risk_fit": 0.12},
    },
    "Financial": {
        "weights": {"fundamental": 0.36, "valuation": 0.18, "technical": 0.13, "catalyst": 0.08, "earnings": 0.13, "risk_fit": 0.12},
    },
    "Real Estate": {
        "weights": {"fundamental": 0.33, "valuation": 0.22, "technical": 0.13, "catalyst": 0.08, "earnings": 0.12, "risk_fit": 0.12},
    },
    "Energy": {
        "weights": {"fundamental": 0.29, "valuation": 0.20, "technical": 0.17, "catalyst": 0.12, "earnings": 0.12, "risk_fit": 0.10},
    },
    "Healthcare": {
        "weights": {"fundamental": 0.34, "valuation": 0.18, "technical": 0.13, "catalyst": 0.10, "earnings": 0.11, "risk_fit": 0.14},
    },
    "Consumer Defensive": {
        "weights": {"fundamental": 0.34, "valuation": 0.18, "technical": 0.13, "catalyst": 0.08, "earnings": 0.11, "risk_fit": 0.16},
    },
}


def get_sector_profile(sector: str | None) -> dict:
    sector = str(sector or "").strip()
    specific = SECTOR_PROFILES.get(sector, {})
    merged = {
        "weights": {**DEFAULT_PROFILE["weights"], **specific.get("weights", {})},
        "thresholds": {**DEFAULT_PROFILE["thresholds"], **specific.get("thresholds", {})},
    }
    return merged
