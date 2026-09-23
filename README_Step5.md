# DIAL-ALERT Step 5: Ethical AI and Bias Auditing

This package audits the locked Step 4 DIAL-ALERT random-forest model for explainability, robustness, subgroup performance, and mitigation tradeoffs. DIAL-ALERT predicts whether a later systolic blood-pressure reading during a haemodialysis session will fall below 90 mmHg.

The work is an academic clinical decision-support prototype. It is not a medical device, does not establish clinical benefit or causal fairness, and must not be used to determine treatment.

## Main deliverables

- `reports/Franklin_Guillano_DIAL_ALERT_Bias_and_Fairness_Analysis.pdf`
- `reports/Franklin_Guillano_DIAL_ALERT_Bias_and_Fairness_Analysis.docx`
- `src/audit_bias_fairness.py`
- `src/create_bias_fairness_report.py`
- `artifacts/step5_*`
- `models/dial_alert_step5_sex_reweighted.joblib`

## Locked evaluation design

- Test population: 21,354 sessions from 170 patients
- Patient overlap across training, validation, and test: zero
- Operating threshold: 0.1428558780, selected on validation patients in Step 4
- Uncertainty: 500 bootstrap resamples of whole patients
- Overall test results: average precision 0.395, ROC AUC 0.852, Brier score 0.062, sensitivity 66.1%, specificity 86.1%, and precision 30.6%

The test set remains separate from model fitting, calibration selection, and threshold selection. Mitigation thresholds are estimated from validation patients only.

## Audit coverage

### Explainability

- Global permutation evidence from Step 4
- Aggregate Monte Carlo interventional SHAP importance
- One explicitly labelled synthetic high-risk SHAP scenario
- LIME-style weighted local surrogate for the same synthetic scenario, with an explicit fidelity diagnostic
- Dependence and conditional-effect plots across synthetic reference profiles

The explanation methods describe the fitted model. They do not establish causality or safe treatment targets.

### Fairness

The source data support audits for recorded sex and age. Diabetes is examined as a clinically relevant subgroup, not as a protected-attribute or socioeconomic proxy. Race, ethnicity, socioeconomic status, and gender identity are unavailable and are explicitly reported as unauditable.

Reported metrics include demographic parity difference, disparate impact ratio, equal opportunity difference, false-positive-rate difference, equalized odds difference, predictive parity difference, and Brier-score difference. Results are supplemented with sex-by-age intersections and a patient-equal-weight sensitivity analysis.

### Mitigation

Two experiments are evaluated:

1. Sex-and-outcome reweighting during model fitting improved the recorded-sex disparate impact ratio from 0.705 to 0.764 and reduced the equalized odds gap from 0.076 to 0.058, while average precision changed from 0.395 to 0.394.
2. Validation-tuned sex-specific thresholds worsened held-out fairness and precision, so they are rejected.

The 0.80 disparate-impact ratio is used only as a descriptive screening heuristic. It is not treated as a legal, statistical, regulatory, or clinical fairness certificate.

## Reproduction

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-step5.txt
python src/audit_bias_fairness.py
python src/create_bias_fairness_report.py
python src/finalize_step5.py --verify
```

Default input paths are:

- `data/processed/hemobp_session_level.csv.gz`
- `artifacts/split_assignments.csv.gz`
- `configs/model_config.json`
- `models/dial_alert_final_predictor.joblib`
- `models/decision_threshold.json`

The analysis uses fixed random seeds stored in the model configuration and writes deterministic filenames. Small numerical differences may occur across platform or dependency versions.

## Data source

The processed data derive from the public HEMOBP dataset described by Lin CJ, Chen YY, Pan CF, Wu VC, and Wu CJ, “Dataset supporting blood pressure prediction for the management of chronic hemodialysis,” *Scientific Data* 6, 313 (2019), https://doi.org/10.1038/s41597-019-0319-8.

## Most important limitations

- Only 170 independent patients are in the test partition despite the large session count.
- Repeated sessions can overrepresent frequent attenders; patient-equal weighting materially changes some estimates.
- Patient-bootstrap intervals are wide, and small intersections are unstable.
- The event definition is an auditable blood-pressure threshold, not a complete clinical diagnosis of intradialytic hypotension.
- Race, ethnicity, socioeconomic status, gender identity, symptoms, interventions, and site variation are unavailable.
- SHAP is approximated by Monte Carlo feature-order permutations; only aggregate global output and explicitly synthetic local examples are published. The LIME-style surrogate has only moderate local fidelity.
- External temporal, geographic, and prospective silent-mode validation are required before any operational use.

## Governance position

DIAL-ALERT should remain decision support with accountable clinician override. Deployment requires external validation, broader protected-attribute collection with consent and governance, human-factors testing, capacity-aware alerting, subgroup calibration and error monitoring, privacy controls, documented incident response, and a rollback rule.

## Availability of the reweighted model

The reweighted model is a development and fairness-analysis output. It is not bundled in this repository and must be regenerated using the training and fairness-analysis scripts. See docs/ARTIFACT_INVENTORY.md for the execution order.

The bundled final predictor is models/dial_alert_final_predictor.joblib. Listing the reweighted model as a deliverable does not mean its model file is included.