"""Compact deterministic technical evidence and complete input identity."""
import hashlib
import json
import math


def technical_packet(chart, frame, settings, model):
    if frame.empty:
        raise ValueError("Usable prices are required for technical analysis.")
    last = frame.iloc[-1]
    evidence = [{"id": "T001", "metric": "Observed close", "value": float(last.Close), "unit": chart.get("unit", "Unknown")},
                {"id": "T002", "metric": "Selected-range price change", "value": (float(last.Close) / float(frame.iloc[0].Close) - 1) * 100 if len(frame) >= 2 else None,
                 "unit": "%", "basis": "Observed endpoints; not total return"}]
    for column in frame.columns:
        if column in {"Date", "Close"}:
            continue
        value = float(last[column])
        evidence.append({"id": f"T{len(evidence)+1:03d}", "metric": column,
                         "value": value if math.isfinite(value) else None,
                         "unit": "0–100 oscillator" if column == "RSI" else chart.get("unit", "Unknown")})
    # Fingerprint every observation used, including indicator warmup, not API credentials.
    identity = {"symbol": chart.get("symbol", "^GSPC"), "range": chart.get("period", "1D"),
                "as_of": chart.get("as_of", str(last.Date)), "provider": chart.get("provider", "Unknown"),
                "source": chart.get("source", "Unknown"), "price_basis": chart.get("price_basis", "Unknown"),
                "timezone": chart.get("timezone", "Unknown"), "currency": chart.get("currency", "Unknown"),
                "interval": chart.get("interval", "Unknown"), "window_unit": "Observed bars",
                "unit": chart.get("unit", "Unknown"), "partial": bool(chart.get("partial")), "stale": bool(chart.get("stale")),
                "settings": settings.to_dict(), "model": model,
                "observations": [(str(stamp), float(value)) for stamp, value in chart.get("calculation_points", chart["points"])]}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    return {**{key: value for key, value in identity.items() if key != "observations"},
            "fingerprint": fingerprint, "retrieved_at": chart.get("retrieved_at", "Unknown"),
            "visible_bars": len(frame), "calculation_bars": len(identity["observations"]),
            "history_start": chart.get("history_start", str(frame.iloc[0].Date)), "evidence": evidence,
            "limitations": ["Indicators use observed bars, not calendar days; EMA is seeded by the first available close.",
                            "Bollinger uses population standard deviation; RSI uses Wilder smoothing.",
                            "Timezone/adjustment may be unknown; missing bars are not imputed. Price performance is not total return."] + chart.get("warnings", [])}


def technical_summary(packet):
    metrics = {item["metric"]: item["value"] for item in packet["evidence"]}
    close = metrics["Observed close"]
    change = metrics["Selected-range price change"]
    lines = [f"Observed price change: {change:+.2f}% over {packet['visible_bars']} displayed bars." if change is not None else "Price change unavailable: only one observed bar."]
    for name in ("SMA", "EMA"):
        value = metrics.get(name)
        if value is not None:
            lines.append(f"Close is {'above' if close > value else 'below' if close < value else 'at'} {name} ({value:,.2f}).")
    rsi = metrics.get("RSI")
    if rsi is not None:
        state = "above 70" if rsi >= 70 else "below 30" if rsi <= 30 else "between 30 and 70"
        lines.append(f"Wilder RSI: {rsi:.1f}, {state}; thresholds are descriptive signals.")
    if metrics.get("MACD histogram") is not None:
        value = metrics["MACD histogram"]
        lines.append(f"MACD histogram: {value:+.3f}; MACD is {'above' if value > 0 else 'below' if value < 0 else 'at'} its signal.")
    if metrics.get("Bollinger upper") is not None:
        state = "above the upper band" if close > metrics["Bollinger upper"] else "below the lower band" if close < metrics["Bollinger lower"] else "inside the bands"
        lines.append(f"Close is {state}.")
    missing = [item["metric"] for item in packet["evidence"] if item["value"] is None]
    if missing:
        lines.append("Insufficient observed bars for: " + ", ".join(missing) + ".")
    return lines
