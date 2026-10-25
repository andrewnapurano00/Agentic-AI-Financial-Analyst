# Equity Report committee and PDF repair - 2026-10-24

The user-reported failure exposed unconstrained ticker strings in CrewAI structured output. The precise rejected response was not retained; this repair does not claim a live reproduction. Structured output now exposes a request-specific enum for best buy, runner-up and specialist preferences, with whitespace/case normalization. Existing verdict consistency and independent universe validation remain; unknown symbols are rejected rather than substituted. No extra retries or model calls were introduced.

The active PDF wrapper delegates saved narrative export to `analysis/equity_report_pdf.py`. It preserves full executive summary and AI research note, and includes committee verdict, confidence, conclusion, debate, specialist dissent, catalysts, risks, invalidation and limitations. It paginates instead of truncating. Compact comparison metrics remain an appendix. Text is escaped, common credentials and configured keys are redacted, and no active links are created.

The saved committee fingerprint is checked before both rendering and exporting. A mismatched/absent decision is explicitly unavailable in the PDF. Downloads and ordinary reruns use saved data, without provider/model calls. A failed explicit debate does not overwrite an existing decision. README describes the THESIS-to-EXPORTS workflow. Existing working-tree changes are preserved; no publication or deployment.


## Executive presentation revision

At the user's request, the PDF now uses portrait Letter pages with the Deep Research font family, navy research header, restrained blue headings, readable paragraph spacing, formatted emphasis/bullets and page footers. Long content flows naturally without forced committee page breaks. The active wrapper no longer constructs or exports compact comparison metrics; the PDF is a narrative summary and saved committee opinion. Metrics remain available in the unchanged app/Excel/CSV exports. Saved text is not regenerated or shortened; summary and decision provenance remain dated, and no additional AI/provider work occurs.
