"""Curated research universe v1: inclusion is a starting list, not current eligibility."""
UNIVERSE_VERSION = "us-liquid-curated-20261019-v1"
# No leveraged, inverse, crypto, options-income or single-stock funds.
STOCKS = {
    "MSFT": ("Technology", ["AI", "growth"]), "NVDA": ("Technology", ["AI", "growth"]),
    "AAPL": ("Technology", ["quality"]), "AVGO": ("Technology", ["AI", "income"]),
    "GOOGL": ("Communication Services", ["AI", "growth"]), "META": ("Communication Services", ["AI", "growth"]),
    "AMZN": ("Consumer Cyclical", ["AI", "growth"]), "HD": ("Consumer Cyclical", ["quality"]),
    "JPM": ("Financial Services", ["quality", "income"]), "BRK-B": ("Financial Services", ["quality"]),
    "JNJ": ("Healthcare", ["income"]), "UNH": ("Healthcare", ["quality"]),
    "PG": ("Consumer Defensive", ["income"]), "KO": ("Consumer Defensive", ["income"]),
    "CAT": ("Industrials", ["infrastructure"]), "GE": ("Industrials", ["growth"]),
    "XOM": ("Energy", ["income"]), "NEE": ("Utilities", ["income", "clean energy"]),
    "LIN": ("Basic Materials", ["quality"]), "PLD": ("Real Estate", ["income"]),
}
ETFS = {
    "SPY": ("ETF broad equity", ["quality"]), "VTI": ("ETF broad equity", ["quality"]),
    "QQQ": ("ETF growth", ["AI", "growth"]), "VUG": ("ETF growth", ["growth"]),
    "SCHD": ("ETF dividend", ["income"]), "VIG": ("ETF dividend", ["income", "quality"]),
    "IWM": ("ETF small cap", ["growth"]), "IJR": ("ETF small cap", ["quality"]),
    "XLK": ("ETF Technology", ["AI"]), "XLV": ("ETF Healthcare", ["quality"]),
    "XLF": ("ETF Financials", ["quality"]), "XLI": ("ETF Industrials", ["infrastructure"]),
    "IEF": ("ETF Treasuries", ["defensive"]), "SHY": ("ETF Treasuries", ["defensive"]),
    "AGG": ("ETF bonds", ["defensive", "income"]), "GLD": ("ETF gold", ["diversifier"]),
}
UNIVERSE = {**STOCKS, **ETFS}
OVERLAP_GROUPS = [{"SPY", "VTI"}, {"QQQ", "VUG", "XLK"}, {"SCHD", "VIG"}, {"IWM", "IJR"}, {"IEF", "SHY", "AGG"}]
SECTORS = sorted({v[0] for v in STOCKS.values()})
THEMES = sorted({t for _, tags in UNIVERSE.values() for t in tags})


def eligible_names(mandate):
    return tuple(s for s in sorted(UNIVERSE) if s not in mandate.forbidden
                 and (mandate.assets == "both" or (s in ETFS) == (mandate.assets == "etfs")))
