# Export content and safety cases

Use temporary synthetic data. Inspect generated artifacts without using real secrets or a user's private portfolio.

| Synthetic input | What to verify |
| --- | --- |
| Text containing <, >, &, quotes, and non-ASCII company names | Visible text survives PDF/HTML escaping and UTF-8 exports without becoming executable markup. |
| A company title beginning with =HYPERLINK(...) | Stored as text, not an executable spreadsheet formula. |
| Text beginning with +, -, @, or leading control/whitespace before = | Writer/text sanitization handles applicable formula-trigger cases. |
| Numeric -20.5, zero, and missing | Remain numeric negative, numeric zero, and blank/null respectively. |
| URL with javascript:, user-info credentials, or an invalid hostname | Unsafe destination is removed or rejected; descriptive text can remain. |
| HTTPS URL with ?apikey=synthetic-secret or &token=synthetic-secret | Exported destination and displayed text do not contain the credential value. |
| Nested api_key/password fields or provider error containing a bearer token | No credential appears in JSON, table, PDF text, or metadata. |
| NaN/infinity and embedded bytes | JSON remains standards-compliant; binary/session artifacts are excluded from evidence exports. |
| Unreviewed report or unknown evidence ID | Download preserves the unresolved status/limitation rather than suggesting completed review. |
| Long paragraphs, wide tables, and many evidence rows | PDF pages remain readable; tables do not lose currency/period/source context. |

## Inspect artifacts

For Excel, open with openpyxl and inspect cell value, data_type, number_format, and hyperlink target; a file that opens successfully can still contain injected formulas.

For CSV, use csv.reader to verify round-trip columns/text and check textual formula triggers. Do not break genuine numeric negatives to handle hostile text.

For JSON, use json.loads and inspect nested fields; never serialize the entire session as a shortcut.

For PDF, validate text and links with a PDF inspection tool already available in the environment, and visually inspect representative pages for layout changes. A %PDF header or byte scan alone does not prove content correctness or absence of secrets in compressed objects. If extraction tooling is unavailable, report that verification gap.

Generate exports directly from a saved packet in tests. Test the download action separately with a model-call counter so it cannot silently re-run research.
