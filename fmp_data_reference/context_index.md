# Context index for future Codex sessions

Purpose: reusable FMP endpoint/schema evidence for future sourcing, validation and authorized improvements. This collection itself does not authorize application changes.

1. Check [collection report](collection_report.md) and [coverage matrix](coverage_matrix.csv) for whether the required API/ticker actually succeeded, its UTC retrieval time/data dates, and restrictions.
2. Use [endpoint inventory](endpoint_inventory.csv) to match the workbook API ID to the original/current route and semantic caveats.
3. Search [field dictionary CSV](data_dictionary.csv) by API ID and nested path; use [observed schemas](schemas/) and the exact sample/raw paths from coverage. Definitions/joins/units may be inferred or unknown.
4. Read [sector classifications](sector_tickers.csv) before cross-sector comparisons. Do not confuse absent, zero, null and empty-string values.

## Common entry points

| Research area | Dictionary sections | Sample folders |
| --- | --- | --- |
| Security lookup and identifiers | [FMP-002](data_dictionary.md#fmp-002), [FMP-005](data_dictionary.md#fmp-005), [FMP-006](data_dictionary.md#fmp-006), [FMP-007](data_dictionary.md#fmp-007) | `samples/FMP-002/`–`FMP-007/` |
| Company/sector/currency context | [FMP-018](data_dictionary.md#fmp-018) | `samples/FMP-018/` |
| Quotes and share float | [FMP-039](data_dictionary.md#fmp-039), [FMP-045](data_dictionary.md#fmp-045) | `samples/FMP-039/`, `samples/FMP-045/` |
| Annual/quarterly statements | [Income](data_dictionary.md#fmp-061), [Balance sheet](data_dictionary.md#fmp-063), [Cash flow](data_dictionary.md#fmp-065) | `samples/FMP-061/`, `FMP-063/`, `FMP-065/` |
| As-reported statements | [FMP-067](data_dictionary.md#fmp-067)–[FMP-070](data_dictionary.md#fmp-070) | `samples/FMP-067/`–`FMP-070/` |
| Metrics, ratios, TTM and growth | [FMP-074](data_dictionary.md#fmp-074)–[FMP-084](data_dictionary.md#fmp-084) | `samples/FMP-074/`–`FMP-084/` |
| DCF and analyst data | [DCF](data_dictionary.md#fmp-085), [Estimates](data_dictionary.md#fmp-031), [Targets](data_dictionary.md#fmp-094) | Corresponding API-ID folders |
| News and transcripts | [Stock news](data_dictionary.md#fmp-102), [Transcript](data_dictionary.md#fmp-111), [Transcript dates](data_dictionary.md#fmp-112) | Corresponding API-ID folders |
| Filings, earnings, dividends, splits | [Filings](data_dictionary.md#fmp-118), [Earnings](data_dictionary.md#fmp-123), [Dividends](data_dictionary.md#fmp-127), [Splits](data_dictionary.md#fmp-129) | Corresponding API-ID folders |
| Price history and technical indicators | [Intraday](data_dictionary.md#fmp-135), [EOD](data_dictionary.md#fmp-136), [SMA](data_dictionary.md#fmp-137)–[Standard deviation](data_dictionary.md#fmp-145) | Corresponding API-ID folders |
| ETF/fund context | [ETF holdings](data_dictionary.md#fmp-148), [Info](data_dictionary.md#fmp-149), [Stock exposure](data_dictionary.md#fmp-152) | Corresponding API-ID folders |
| Ownership, insider, ESG and Congress | [Institutional](data_dictionary.md#fmp-184), [Insider](data_dictionary.md#fmp-192), [ESG](data_dictionary.md#fmp-157), [Senate](data_dictionary.md#fmp-160) | Corresponding API-ID folders |
| Macro and other assets | [Treasury](data_dictionary.md#fmp-208), [Economic](data_dictionary.md#fmp-209), [Commodities](data_dictionary.md#fmp-212), [Forex](data_dictionary.md#fmp-217), [Crypto](data_dictionary.md#fmp-222) | Corresponding API-ID folders |
| Bulk extraction | [FMP-238](data_dictionary.md#fmp-238)–[FMP-259](data_dictionary.md#fmp-259) | Raw shared response plus per-stock extractions where accessible |

Only use sample folders that exist and have successful coverage; missing/restricted endpoints still have inventory and schema entries. Full dictionary includes all 259 API IDs. [README refresh instructions](README.md#refresh-or-resume) explain bounded collection, transformations, authorization and limitations.

To inspect a precise field without loading the full dictionary:

```powershell
& 'C:/Users/andna/anaconda3/python.exe' fmp_data_reference/scripts/query_reference.py --api FMP-061 --field revenue --limit 5
```

The schemas include all historical collected JSON samples. Counts can include repeated cached projections; they are not independent statistical observations. WebSocket references [FMP-235](data_dictionary.md#fmp-235)–[FMP-237](data_dictionary.md#fmp-237) have bounded live entitlement-denial evidence and official protocol links in the inventory/report.
