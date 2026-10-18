"""Common BVPS requires dated common equity and outstanding common shares."""
from datetime import date
import math


def common_book_value(balance, reported=(), *, today=None):
    from .model import number
    today = today or date.today()
    common = number(balance.get("commonStockEquity"))
    if common is None:
        total, preferred = number(balance.get("totalStockholdersEquity")), number(balance.get("preferredStock"))
        if total is not None and preferred is not None and preferred >= 0:
            common = total - preferred
    shares = number(balance.get("commonStockSharesOutstanding"))
    support, note = None, ""
    if shares is None:
        matches = []
        for index, row in enumerate(reported):
            if not isinstance(row, dict):
                continue
            if row.get("symbol") != balance.get("symbol") or row.get("period") != "FY" or row.get("reportedCurrency") != balance.get("reportedCurrency"):
                continue
            year = balance.get("fiscalYear") or balance.get("calendarYear")
            if year and row.get("fiscalYear") and str(year) != str(row["fiscalYear"]):
                continue
            try:
                if date.fromisoformat(row["date"]) > today:
                    continue
                gap = abs((date.fromisoformat(row["date"]) - date.fromisoformat(balance["date"])).days)
            except (KeyError, ValueError, TypeError):
                continue
            if gap:
                # FMP recorded as-reported dates can precede normalized FY end
                # by one day. Require the same FY and independently matching equity.
                equity = number(row.get("stockholdersequity"))
                total = number(balance.get("totalStockholdersEquity"))
                if gap != 1 or not row.get("fiscalYear") or str(row["fiscalYear"]) != str(balance.get("fiscalYear") or balance.get("calendarYear")) or equity is None or total is None or not math.isclose(equity, total, rel_tol=1e-9, abs_tol=.01):
                    continue
            for field in ("acceptedDate", "filingDate"):
                if row.get(field) and str(row[field])[:10] > today.isoformat():
                    break
            else:
                value = number(row.get("commonstocksharesoutstanding"))
                issued, treasury = number(row.get("commonstocksharesissued")), number(row.get("treasurystockcommonshares"))
                if value is not None and issued is not None and treasury is not None and not math.isclose(value, issued-treasury, rel_tol=1e-9, abs_tol=.01):
                    continue
                if value is None:
                    if issued is not None and treasury is not None and issued > 0 and treasury >= 0:
                        value = issued - treasury
                if value is not None and value > 0:
                    matches.append((index, value, gap))
        if len(matches) == 1:
            support, shares, gap = matches[0]
            note = "As-reported FY common shares" + ("; one-day date offset reconciled by fiscal year and total equity" if gap else "")
    value = common / shares if common is not None and shares is not None and shares > 0 else None
    return {"value": value, "shares": shares, "common_equity": common, "reported_index": support, "note": note}
