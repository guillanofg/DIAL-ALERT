# DIAL ALERT Model Card

## Model summary

DIAL-ALERT is a random-forest probability model for a later blood-pressure-defined intradialytic hypotension event in an eligible haemodialysis session. It uses 22 variables available at the index time or derived only from earlier sessions.

## Intended use

The model supports academic study of early-session risk ranking, alert-capacity planning, explainability, and subgroup auditing. It may be used to reproduce the capstone results or to test a prospective silent-mode workflow after institutional approval.

The model must not be used as a diagnostic device, an autonomous treatment rule, a reason to withhold dialysis, or a substitute for clinician assessment.

## Data

The fitted model uses the public HEMOBP Version 3 dataset. The final cohort contains 106,758 sessions from 830 patients and a primary event prevalence of 8.49%. The public source is retrospective and single-center.

## Evaluation

All sessions from one patient remain in a single partition. Hyperparameters were selected with patient-grouped cross-validation on training patients. Calibration and the operating threshold were chosen with validation patients. Test patients were evaluated once after the choices were locked.

| Test measure | Estimate | Patient-bootstrap 95% interval |
| --- | ---: | ---: |
| Average precision | 0.395 | 0.306 to 0.478 |
| ROC AUC | 0.852 | 0.821 to 0.876 |
| Brier score | 0.062 | 0.049 to 0.077 |
| Sensitivity | 0.661 | 0.550 to 0.745 |
| Specificity | 0.861 | 0.806 to 0.903 |
| Precision | 0.306 | 0.260 to 0.353 |

At a fixed 20% alert capacity, the model captured 69.1% of observed events, with 29.4% precision and 3.46-fold lift over prevalence.

## Explainability

Global permutation importance, aggregate approximate interventional SHAP values, synthetic SHAP and LIME local explanations, and synthetic-profile dependence plots describe the fitted model. Patient-level explanation tables and observed-patient local examples are not published. These methods show model associations and must not be interpreted as causal treatment effects.

## Fairness

The available data permit audits for recorded sex and age. Diabetes is evaluated as a clinical subgroup. Race, ethnicity, socioeconomic status, and gender identity are absent. Point estimates and patient-bootstrap intervals are reported because repeated sessions and small groups can make apparent disparities unstable.

Outcome-by-sex reweighting modestly improved recorded-sex disparity measures without a material change in average precision. A sex-specific threshold strategy performed worse on new patients and was rejected. Any future deployment requires subgroup calibration and error monitoring with broader, appropriately governed attribute collection.

## Limitations

- The endpoint is a later SBP below 90 mmHg, not a complete symptomatic diagnosis.
- The data omit symptoms, interventions, medications, laboratory values, and many comorbidities.
- The study is retrospective and single-center.
- The test set contains 170 independent patients despite 21,354 sessions.
- Repeated visits give frequent attenders more session-level weight.
- The model has not been externally, temporally, or prospectively validated.
- Clinical benefit, workflow effect, and cost savings have not been demonstrated.

## Governance requirements

Before clinical use, the model requires external validation, prospective silent-mode testing, human-factors evaluation, capacity-aware threshold selection, privacy review, documented clinician override, incident response, drift monitoring, and a rollback rule.
