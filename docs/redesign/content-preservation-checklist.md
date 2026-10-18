# Mandatory Content Preservation and Release Checklist

This file is part of the implementation contract. Preservation of existing content is a release requirement, not a design preference.

## What this package does and does not establish
The redesign has not been implemented. This package requires proof of preservation; it does not certify a finished app. The accompanying source-ui-inventory.csv is a static extraction from the supplied ZIP. Its rows are source candidates, not verified active UI content. It includes helper/conditional paths and can omit custom renderers or dynamic content. Agents must reconcile it against active source paths and runtime screens before coding.

## Before application edits
- Trace all eight routes, nested modes, result tabs and relevant helper renderers.
- Reconcile every source candidate: active, duplicate presentation, unreachable, or conditional. Explain exclusions; do not delete rows to improve completion statistics.
- Expand custom components and dynamic sections into preservation rows. Include full report text, all table columns, chart/range/technical controls, provider/date/unit evidence, warnings, settings, exports and state behavior.
- Record original and proposed locations and exact verification method for every active item.
- Independently review requirements understanding and the complete baseline inventory. No application edits until this review passes.

## Implementation restrictions
- Reorganize existing content; never replace full content with a summary alone.
- Preserve every existing metric, table, report, chart, filter, technical indicator/control, news item presentation, scenario, evidence/audit section and export.
- Preserve input options/defaults, units, scoring/formulas, universes, missing/zero handling and financial thresholds.
- Preserve saved history, follow-ups, thread/run/ticker identity, retry/finalize semantics, fingerprints and explicit paid actions.
- Details may move to named tabs/disclosures, but must remain reachable and retain their meaning. Material missing-data, mismatch, failure and eligibility notices remain visible near affected outputs.
- Existing information may not be removed simply because it is absent from a mockup. Mockups are representative layouts with illustrative data.
- New features have separate acceptance criteria; they do not count as replacements for existing features.

## Required release evidence
1. Content parity: compare the same baseline and redesigned fixture inputs. Verify all fields, table columns/rows, full narratives, sources and limitations, including conditional states.
2. Control parity: exercise each control and compare behavior, not just its visual label.
3. Export parity: verify all existing formats and payload content/schema. Do not shorten exports as part of visual redesign.
4. State parity: verify navigation, remounts, empty filters, saved result mismatches and partial failures preserve appropriate work and identity.
5. Call parity: ordinary navigation, filtering, chart changes and disclosure access must not add paid model calls.
6. Visual parity: compare approved composition across required widths without hiding content through clipping or unreadable text.
7. Independent reviewer signs each verified preservation row and the release report.

## Release rule
Required result: 100% of the reconciled active content/control/export inventory verified; zero unexplained omissions; zero unresolved preservation failures. Counts refer to the expanded reviewed inventory, not merely the raw source CSV. Pre-existing failures are recorded separately and must not be used to silently remove functionality.

If a required item cannot be preserved, stop dependent release work, identify the exact item and reason, and obtain the user's explicit decision before reducing scope. Do not mark the redesign complete while preservation remains unresolved.

## Completion report template
- Baseline app revision and test fixture versions:
- Reviewed active inventory total:
- Verified preservation total:
- Omitted or changed items with explicit user authorization:
- Outstanding preservation failures:
- Functional, state, export and call-parity results:
- Visual review links:
- Independent reviewer and sign-off date:
- Release decision: PASS / FAIL (with reasons)
