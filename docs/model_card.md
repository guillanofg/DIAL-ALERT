# DIAL ALERT Model Card

## Model summary

DIAL-ALERT is a random-forest probability model for a later blood-pressure-defined intradialytic hypotension event in an eligible haemodialysis session. It uses 22 variables available at the index time or derived only from earlier sessions.

## Outcome and eligibility

The primary endpoint is **any later SBP <90 mmHg after the index observation**. The index is the earliest valid BP observation during active dialysis in minutes 0–30.

Eligibility requires baseline SBP >=90 mmHg, at least two distinct later measurement minutes, and **last observed dialysis minute >=120**. The 120-minute rule is anchored to dialysis elapsed time, not to prediction time; it does not require 120 minutes after the index observation.

## Intended use

The model supports academic study of early-session risk ranking, alert-capacity planning, explainability, and subgroup auditing. It must not be used as a diagnostic device, autonomous treatment rule, reason to withhold dialysis, or substitute for clinician assessment.

## Data and independence

The fitted model uses public HEMOBP Version 3 data. The final cohort contains 106,758 sessions from 830 patients and a primary event prevalence of 8.49%. The study is retrospective and single-center.

The locked test set contains **21,354 sessions but only 170 independent test patients**. All sessions from one patient remain in one partition.

## Evaluation

| Test measure | Estimate | Patient-bootstrap 95% interval |
| --- | ---: | ---: |
| Average precision | 0.395 | 0.306 to 0.478 |
| ROC AUC | 0.852 | 0.821 to 0.876 |
| Brier score | 0.062 | 0.049 to 0.077 |
| Sensitivity at threshold 0.143 | 0.661 | 0.550 to 0.745 |
| Specificity at threshold 0.143 | 0.861 | 0.806 to 0.903 |
| Precision at threshold 0.143 | 0.306 | 0.260 to 0.353 |

## Alert strategies

Two distinct strategies are reported.

**Probability-threshold strategy:** validation-selected threshold 0.142855878 (reported as 0.143), selected by maximum F2. Test sensitivity was 66.1% and precision 30.6%.

**Capacity strategy:** review the highest-risk 20% of sessions, regardless of the absolute probability cutoff. On test data this captured 69.1% of events, with 29.4% precision and 3.46-fold lift.

These strategies answer different operational questions and should not be presented as the same alert rule.

## Model selection and calibration

Hyperparameters were selected with patient-grouped cross-validation on training patients. The prespecified model-selection rule was highest grouped-CV average precision; candidates within 0.01 were compared using validation Brier score. Random forest was selected under that rule.

The saved finalist has **no post-hoc calibration**. Any comparison claiming that random forest or gradient boosting provides better probabilities should first apply the same calibration procedure to both finalists.

## Proposed future pilot targets

These are **prospective pilot targets, not demonstrated outcomes**:

- detect at least 65% of later SBP <90 events;
- keep false alerts at or below 15 per 100 eligible sessions;
- median clinician review time <=2 minutes per displayed alert.

Targets should be pre-registered and reviewed locally before prospective testing.

## Explainability

Global permutation importance, aggregate approximate interventional SHAP values, synthetic SHAP and LIME local explanations, and synthetic-profile dependence plots describe the fitted model. These methods show model associations and must not be interpreted as causal treatment effects.

## Fairness

Available data permit audits for recorded sex and age; diabetes is evaluated as a clinical subgroup. Race, ethnicity, socioeconomic status, and gender identity are absent. Current mitigation results are exploratory. Outcome-by-sex reweighting improved some point estimates, while sex-specific thresholds did not transfer well to the test set and were rejected. Fairness improvements require confirmation on fresh data.

## Limitations

- BP-defined endpoint, not a complete symptomatic diagnosis.
- Symptoms, interventions, medications, laboratory values, and many comorbidities are unavailable.
- Retrospective, single-center data.
- Only 170 independent patients in the locked test set despite 21,354 sessions.
- Repeated visits give frequent attenders more session-level weight.
- No external, temporal, or prospective validation.
- Clinical benefit, workflow effect, and cost savings have not been demonstrated.
- Advance-warning time has not yet been reported.
- Historical-feature contribution, simple clinical comparator performance, and extreme-value/exclusion sensitivity remain secondary analyses.

## Governance requirements

Before clinical use: external or temporal validation, prospective silent-mode testing, human-factors evaluation, capacity-aware operating-point selection, privacy review, clinician override, incident response, drift monitoring, subgroup monitoring, and rollback rules.
