"""Compact report disclosure; detailed immutable contracts remain in audit JSON."""
from .research_metrics import project_sector_row


def report_basis_notes(result):
    rows = [project_sector_row(row) for row in result.get("comparison", [])]
    if not any(row.get("Metric contracts") for row in rows):
        return []
    notes = ["TTM flows sum four consecutive validated fiscal quarters, assuming standalone flows on standardized routes when duration metadata is absent; balance sheets are point-in-time snapshots. ROE/ROA use matched beginning and ending balances. Forward growth compares FY+2 with FY+1 annual estimates, not trailing results.",
             "Source dates, currencies, formulas and original inputs remain in Sources & Evidence and the audit JSON. Unsupported metrics remain unavailable; calculation checks do not certify AI prose."]
    failed = {}
    for item in result.get("evidence", []):
        if item.get("status") in {"missing", "error"} and item.get("symbol"):
            failed.setdefault(str(item["symbol"]), set()).add(str(item.get("category", "dataset")))
    for symbol, categories in failed.items():
        notes.append(symbol + " - unavailable datasets: " + ", ".join(sorted(categories)) + ". Successful evidence is retained; review Sources & Evidence before relying on incomplete coverage.")
    for row in rows:
        symbol = str(row.get("Ticker", ""))
        metadata = ["Statement " + str(row.get("Statement date") or "date unavailable") + " / " + str(row.get("Statement currency") or "currency unavailable"),
                    "quote " + str(row.get("Quote as of") or row.get("Price date") or "date unavailable") + " / " + str(row.get("Quote currency") or "currency unavailable")]
        if row.get("Quote currency assumption"):
            metadata.append(str(row["Quote currency assumption"]))
        sources = [item for item in result.get("evidence", []) if item.get("symbol") == symbol and item.get("status") == "ok"]
        providers = sorted({str(item["provider"]) for item in sources if item.get("provider")})
        retrieved = sorted({str(item["retrieved_at"]) for item in sources if item.get("retrieved_at")})
        if providers:
            metadata.append("Sources: " + ", ".join(providers))
        if retrieved:
            metadata.append("retrieved " + retrieved[0] + (" to " + retrieved[-1] if len(retrieved) > 1 else ""))
        notes.append(symbol + " - " + "; ".join(metadata) + ".")
        contracts = row.get("Metric contracts", {})
        # Only decision-relevant sector priorities; do not list unrelated specialist fields.
        frameworks = [f for f in result.get("sector_frameworks", []) if f.get("symbol") == row.get("Ticker")]
        priorities = list(dict.fromkeys(k for f in frameworks for k in f.get("must_have", [])))
        missing = [k for k in priorities if row.get(k) is None and contracts.get(k, {}).get("applicability") not in {"not_applicable", "inapplicable"}]
        if missing:
            notes.append(str(row.get("Ticker", "")) + " - unavailable priority metrics: " + ", ".join(missing) + ". These gaps limit sector comparisons; values have not been estimated.")
    return notes
