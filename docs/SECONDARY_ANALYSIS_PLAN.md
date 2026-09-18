# Secondary analyses and future validation

Status: planned, not executed in this submission revision. Original model, feature configuration, split and operating threshold remain locked. No new claims of model superiority or fairness improvement arise from these plans.

| Requested analysis | Prespecified approach and outputs |
| --- | --- |
| Advance-warning time | First valid post-index SBP <90 minute minus index minute; report median, IQR, range, and fractions above 15, 30 and 60 minutes, separately for all events and alerts at the locked threshold. Bootstrap patients. Reading intervals limit event-onset precision; no-event sessions have no event lead time |
| Small clinical comparator | Logistic regression with baseline SBP and prior-session hypotension; fit imputation and coefficients on training patients. Use the same patient folds and validation decision rules. Report AP, ROC AUC, Brier and workload with patient-bootstrap paired differences |
| Historical features | Compare the full feature set with all prior-session variables removed. Train both on the same development patients. Separately report first-observed and subsequent sessions; define missing history without looking forward |
| Equal finalist calibration | Use identical patient-disjoint calibration and decision subsets for RF and histogram boosting; compare none, sigmoid and isotonic for both. Choose method on development patients only. Report an exploratory comparison without replacing the locked model based on test results |
| Extremes and exclusions | Confirm UF units and source distributions; set plausibility rules before looking at test outcomes. Report missing, extreme and excluded counts. Compare unchanged predictions by extreme-value strata and preplanned alternative development-only cleaning. Describe shorter sessions separately; truncated monitoring must not be assumed event-free |
| Uncertainty | Emphasize 170 test patients. Use patient-cluster intervals and paired bootstrap differences; retain effective patient and event counts alongside session counts. Avoid treating repeated sessions as independent |

The existing test set has already been inspected. New analyses on it must be called exploratory, evaluated once under a written analysis plan, and followed by confirmation on new patients. Do not run an iterative test-set search for favorable results.

## Future validation

1. Lock the model and policy before external-center or later-period validation. Check cohort compatibility, availability of historical features, missingness and short-session coverage.
2. Confirm fairness mitigation on fresh data; measure uncertainty and clinical utility jointly. Current mitigation is exploratory and is not the deployed predictor.
3. Run silent predictions first. Check prospective eligibility, actual advance warning, latency, calibration, event detection and alert workload without influencing care.
4. If prespecified gates pass, assess supervised clinician review, override and actions, safety, patient outcomes and the full implementation cost. Clinical or financial benefit requires a suitable comparative evaluation; it is not inferred from retrospective recall or a 90-day feasibility pilot.

Proposed pilot targets: event detection at least 65%, no more than 15 false alerts per 100 eligible sessions, and median review time at most 2 minutes per displayed alert. These are provisional targets, not achieved clinical results or established safety standards.
