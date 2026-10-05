"""Locally defined indicators; periods count observed bars, not calendar days."""
from dataclasses import asdict, dataclass
import math

import pandas as pd


@dataclass(frozen=True)
class IndicatorSettings:
    selected: tuple[str, ...] = ("SMA", "RSI")
    sma: int = 20
    ema: int = 20
    rsi: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bollinger: int = 20
    bollinger_std: float = 2.0

    def __post_init__(self):
        if len(set(self.selected)) != len(self.selected) or set(self.selected) - {"SMA", "EMA", "RSI", "MACD", "Bollinger"}:
            raise ValueError("Select supported indicators once each.")
        for key in ("sma", "ema", "rsi", "macd_fast", "macd_slow", "macd_signal", "bollinger"):
            value = getattr(self, key)
            if isinstance(value, bool) or not isinstance(value, int) or not 2 <= value <= 500:
                raise ValueError("Indicator windows must be integers between 2 and 500 bars.")
        if self.macd_fast >= self.macd_slow or self.macd_slow + self.macd_signal > 500:
            raise ValueError("MACD fast must be below slow; slow plus signal must be at most 500 bars.")
        if not math.isfinite(self.bollinger_std) or not 0.5 <= self.bollinger_std <= 5:
            raise ValueError("Bollinger multiplier must be between 0.5 and 5.")

    def to_dict(self):
        return asdict(self)


def wilder_rsi(close, window):
    result = pd.Series(float("nan"), index=close.index, dtype=float)
    if len(close) <= window:
        return result
    change = close.diff()
    gains, losses = change.clip(lower=0), -change.clip(upper=0)
    gain, loss = gains.iloc[1:window + 1].mean(), losses.iloc[1:window + 1].mean()
    def value():
        return 50.0 if gain == loss == 0 else 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    result.iloc[window] = value()
    for i in range(window + 1, len(close)):
        gain = (gain * (window - 1) + gains.iloc[i]) / window
        loss = (loss * (window - 1) + losses.iloc[i]) / window
        result.iloc[i] = value()
    return result


def calculate_indicators(points, settings):
    """Compute over warmup plus visible bars; caller trims only after calculation."""
    frame = pd.DataFrame(points, columns=["Date", "Close"])
    if frame.empty:
        return frame
    if not all(math.isfinite(float(x)) and float(x) > 0 for x in frame.Close):
        raise ValueError("Indicator prices must be finite and positive.")
    close = frame.Close.astype(float)
    if "SMA" in settings.selected:
        frame["SMA"] = close.rolling(settings.sma, min_periods=settings.sma).mean()
    if "EMA" in settings.selected:
        frame["EMA"] = close.ewm(span=settings.ema, adjust=False, min_periods=settings.ema).mean()
    if "RSI" in settings.selected:
        frame["RSI"] = wilder_rsi(close, settings.rsi)
    if "MACD" in settings.selected:
        fast = close.ewm(span=settings.macd_fast, adjust=False, min_periods=settings.macd_fast).mean()
        slow = close.ewm(span=settings.macd_slow, adjust=False, min_periods=settings.macd_slow).mean()
        frame["MACD"] = fast - slow
        frame["MACD signal"] = frame.MACD.ewm(span=settings.macd_signal, adjust=False, min_periods=settings.macd_signal).mean()
        frame["MACD histogram"] = frame.MACD - frame["MACD signal"]
    if "Bollinger" in settings.selected:
        middle = close.rolling(settings.bollinger, min_periods=settings.bollinger).mean()
        spread = close.rolling(settings.bollinger, min_periods=settings.bollinger).std(ddof=0) * settings.bollinger_std
        frame["Bollinger mid"], frame["Bollinger upper"], frame["Bollinger lower"] = middle, middle + spread, middle - spread
    return frame


def finite_domain(values):
    values = [float(value) for value in values if pd.notna(value) and math.isfinite(float(value))]
    if not values:
        return [0.0, 1.0]
    low, high = min(values), max(values)
    pad = max((high - low) * .06, max(abs(low), abs(high)) * .005, .01)
    return [low - pad, high + pad]


def axis_style(period):
    if period == "1D":
        return {"format": "%H:%M", "tickCount": 5, "labelAngle": 0}
    if period == "5D":
        return {"format": "%b %d", "tickCount": 5, "labelAngle": 0}
    if period in {"1M", "3M"}:
        return {"format": "%b %d", "tickCount": 6, "labelAngle": 0}
    return {"format": "%b %Y" if period == "1Y" else "%Y", "tickCount": 6, "labelAngle": 0}
