# Submission-readiness status

Revision date: 18 September 2026. Seven of the eight priority areas have implementation/documentation evidence; full fresh-environment reproduction remains blocked. The remaining research is explicitly separated from completed submission edits.

| Priority | Result |
| --- | --- |
| 1 Consistency | Updated report wording and report sources; corrected older EDA boosting/AP-importance numbers; synchronized presentation counts and reference metrics |
| 2 Minute-120 eligibility | Explicit dialysis-time anchor in code comment, README, model card, report text and dedicated slide |
| 3 Measurable targets | Proposed future targets: at least 65% detection, at most 15 false alerts per 100 sessions, median review at most 2 minutes; no prospective success claimed |
| 4 Alert strategies | Separate threshold and capacity results, including different review and false-alert workloads |
| 5 Fresh reproduction | **Blocked at data acquisition, HTTP 403**. New-environment install, included-model prediction, local HTTP execution and 27 tests passed; these do not establish training reproducibility |
| 6 Documentation | Exact inventory, absent candidates/intermediates, authoring dependencies and rebuild order documented |
| 7 Visual review | Rendered both decks; technical 16 slides, business 11. Simplified crowded fairness chart, clarified labels and added focused evidence slides. Reports rendered and PDFs refreshed |
| 8 Optional steps | Fixed Flask inference preprocessing, tested agreement with CLI, added real HTTP evidence and labeled animated playback. Step 9 remains explicitly saved-draft replay without live generation |

## Additional work

Items 9–13 remain planned secondary analyses: warning time, small clinical comparator, history ablation, equally calibrated finalists, and extreme-value/short-session sensitivity. Item 14 is strengthened by prominent patient-cluster intervals and the 170-patient test denominator. See `SECONDARY_ANALYSIS_PLAN.md`.

Items 15–17 remain future external/temporal validation, fairness confirmation on fresh data, and staged prospective evaluation. No new dataset was supplied, no model was retuned against the existing test set, and no new clinical or financial benefit is claimed.
