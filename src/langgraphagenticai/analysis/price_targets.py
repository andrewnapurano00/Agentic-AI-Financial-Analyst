"""Dated target-window normalization and indicative target/quote price arithmetic."""
from math import isfinite
from datetime import datetime, timezone

WINDOWS=(("Last month","lastMonth","lastMonthAvgPriceTarget"),("Last quarter","lastQuarter","lastQuarterAvgPriceTarget"))


def finite(value):
    if value is None or isinstance(value,bool):return None
    try:
        result=float(value)
        return result if isfinite(result) else None
    except (TypeError,ValueError,OverflowError):return None


def currency(value):
    value=str(value or "").upper().strip()
    return value if len(value)==3 and value.isalpha() else None


def normalize_targets(payload,symbol):
    rows=[r for r in payload if isinstance(r,dict) and r.get("symbol")==symbol] if isinstance(payload,list) else []
    if not rows:
        raise ValueError("No price-target summary matches the selected stock.")
    fields=[field for _,count,avg in WINDOWS for field in (count,avg)]+["currency"]
    records=[{k:r.get(k) for k in fields} for r in rows]
    if any(r!=records[0] for r in records[1:]):
        raise ValueError("Conflicting price-target summaries were excluded.")
    row=rows[0]; result=[]
    for window,count_field,target_field in WINDOWS:
        count=finite(row.get(count_field));target=finite(row.get(target_field))
        count=int(count) if count is not None and count>=0 and count.is_integer() else None
        reason=""
        if count==0:
            target=None;reason="No ratings in this window."
        elif target is None or target<0 or (target==0 and not count):
            target=None;reason="Average price target unavailable."
        elif count is None:
            reason="Coverage count unavailable."
        result.append(dict(window=window,target=target,count=count,currency=currency(row.get("currency")),note=reason))
    return result


def compare_targets(summary,quote,now=None):
    now=now or datetime.now(timezone.utc)
    if summary.get("symbol")!=quote.get("symbol"):
        raise ValueError("Target and quote symbols do not match.")
    price=finite(quote.get("price"));price=price if price is not None and price>0 and not quote.get("error") else None
    warnings=[]
    stamp=quote.get("as_of")
    try:
        parsed=datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
        if parsed.tzinfo is None:raise ValueError("Unknown quote timezone")
        if parsed>now:
            price=None;warnings.append("Future quote timestamp excluded.")
        elif (now-parsed).total_seconds()>4*86400:
            warnings.append("The latest available quote is over four calendar days old; comparison may be stale.")
    except (TypeError,ValueError):
        warnings.append("Quote observation time is unavailable; current-price freshness is unverified.")
    quote_currency=currency(quote.get("currency"))
    rows=[]
    for target in summary.get("targets",[]):
        item=dict(target);target_currency=currency(item.get("currency"))
        compatible=not (quote_currency and target_currency and quote_currency!=target_currency)
        pct=None
        if not compatible:
            warnings.append("Target and quote currencies differ; upside comparison excluded.")
        elif price is not None and item.get("target") is not None:
            pct=(item["target"]/price-1)*100
            if not isfinite(pct):
                pct=None;warnings.append("Target/quote comparison is not a finite percentage.")
            if not quote_currency or not target_currency:
                warnings.append("Target/quote currency is not independently verified. Percentage comparison assumes matching currencies and price basis.")
        item.update(price=price,upside_pct=pct,comparable=compatible,
                    direction="Upside" if pct is not None and pct>0 else "Downside" if pct is not None and pct<0 else "At target" if pct==0 else "Unavailable")
        rows.append(item)
    return dict(price=price,currency=quote_currency,rows=rows,warnings=list(dict.fromkeys(warnings)))
