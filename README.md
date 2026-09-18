# DIAL ALERT

DIAL-ALERT is an end-to-end machine-learning capstone that estimates the risk of a later systolic blood-pressure (SBP) reading below 90 mmHg during an eligible haemodialysis session. It uses only information available at the index time or from earlier sessions and keeps every patient's sessions within one data partition.

> **Academic prototype only.** DIAL-ALERT is not a diagnostic device and must not guide patient care without external validation, prospective silent-mode testing, human-factors evaluation, and institutional governance approval.

## Main result

The selected random-forest pipeline was evaluated once on **21,354 sessions from 170 test patients** who were excluded from model fitting and threshold selection. The large session count should not be interpreted as 21,354 independent patients.

| Measure | Locked test result |
| --- | ---: |
| Average precision | 0.395 |
| ROC AUC | 0.852 |
| Brier score | 0.062 |
| Sensitivity at probability threshold 0.143 | 66.1% |
| Specificity at probability threshold 0.143 | 86.1% |
| Precision at probability threshold 0.143 | 30.6% |
| Recall within highest-risk 20% of sessions | 69.1% |
| Lift within highest-risk 20% | 3.46 |

Patient-bootstrap 95% confidence intervals are reported in `docs/model_card.md` and `artifacts/test_metric_confidence_intervals.csv`.

These are retrospective prediction results. They do not show that an alert prevents hypotension, improves outcomes, or saves money.

## Outcome and eligibility

The primary outcome is **any SBP <90 mmHg measured after the index observation**. The index is the earliest valid BP observation during active dialysis in minutes 0–30.

Eligibility additionally requires at least two distinct post-index measurement minutes and an observation at or beyond **dialysis minute 120**. This is a session-duration/follow-up rule: it does **not** require 120 minutes of follow-up after the prediction time. For example, an index at minute 20 can satisfy the rule if the session has an observation at minute 120 or later.

The final analytic cohort contains **106,758 sessions from 830 patients**, with primary-event prevalence **8.49%**.

## Two different alert strategies

The project reports two operational approaches and does not treat them as interchangeable:

1. **Fixed probability threshold:** flag a session when predicted risk is at least **0.142855878 (reported as 0.143)**. This threshold was selected on validation patients by maximum F2 score. On the locked test set it produced 66.1% sensitivity and 30.6% precision.
2. **Fixed review capacity:** rank sessions by predicted risk and review only the **highest-risk 20%**. On the locked test set this captured 69.1% of observed events, with 29.4% precision and 3.46-fold lift.

The first strategy fixes a probability cutoff; the second fixes workload. Their operating characteristics should therefore be interpreted separately.

## Model selection

Models compared were a prevalence baseline, logistic regression, embedded L1 feature selection, decision tree, PCA logistic regression, random forest, and histogram gradient boosting.

The prespecified selection rule was: **highest patient-grouped cross-validation average precision; when candidates were within 0.01, prefer the lower validation Brier score.** Random forest was selected under this rule. The saved finalist uses **no post-hoc calibration** (`calibration_method: none`). Claims that one finalist provides better probabilities than another should not be made until finalists are compared under the same calibration procedure.

## Future pilot targets — proposed, not demonstrated

The following are **future prospective pilot targets**, not results from the retrospective study:

- **Event detection:** aim to identify at least **65% of later SBP <90 events** while preserving acceptable calibration.
- **False-alert workload:** aim for **no more than 15 false alerts per 100 eligible sessions**, with staffing capacity reviewed before live display.
- **Clinician review time:** target a **median review time of 2 minutes or less per displayed alert** during a supervised workflow study.

These targets are provisional and should be pre-registered, reviewed with local clinicians, and revised if local workflow or safety requirements justify different limits.

## Data

The project uses HEMOBP Version 3, a public dataset released on Figshare under CC BY 4.0 and described in *Scientific Data*.

- Dataset DOI: https://doi.org/10.6084/m9.figshare.6260654.v3
- Data descriptor: https://doi.org/10.1038/s41597-019-0319-8
- Source files: `idp.csv`, `d1.csv`, and `vip.csv`

Raw and processed data are intentionally excluded from Git. The download script retrieves the fixed Version 3 files and verifies publisher-provided checksums.

## Repository contents

| Path | Purpose |
| --- | --- |
| `src/` | Data acquisition, cohort construction, EDA, training, auditing, prediction, and report scripts |
| `notebooks/` | Guided reproducible workflow |
| `data/` | Empty raw/processed directories with acquisition instructions |
| `models/` | Included fitted predictor, operating threshold, and model manifest |
| `artifacts/` | Included machine-readable metrics and publication figures |
| `docs/` | Data dictionaries, preprocessing specification, model card, and submission notes |
| `reports/` | Included reports and two presentation binaries |
| `step8_deployment/` | Local Flask inference package and deployment instructions |
| `step9_genai/` | Saved AI-draft replay, numeric validation, examples, and demo |
| `tests/` | Repository and inference smoke tests |

### Included versus regenerated artifacts

**Included:** `models/dial_alert_final_predictor.joblib`, `models/decision_threshold.json`, `models/model_manifest.json`, current metrics/figures under `artifacts/`, reports, and presentation binaries.

**Regenerated from data/code:** processed session data, model-search outputs, refreshed metrics/figures, and reports can be rebuilt by following the commands below.

**Presentation rebuild:** the current PPTX files are included. Rebuilding them from `src/create_step6_presentations.mjs` requires the JavaScript presentation-generation environment used by that script in addition to the Python requirements; this is not installed by `requirements.txt`.

## Reproduce the analysis

Use Python 3.12 from the repository root.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python src/download_data.py
python src/build_session_dataset.py --raw-dir data/raw --output-dir data/processed
python src/train_evaluate.py --data data/processed/hemobp_session_level.csv.gz --config configs/model_config.json --artifacts artifacts --models models
python src/generate_eda.py
python src/generate_step4_assets.py
python src/audit_bias_fairness.py
python src/create_final_report.py
pytest -q
```

A fresh-environment verification record should be saved in `docs/REPRODUCIBILITY_RECORD.md`. Do not mark it complete until the entire sequence, including a prediction smoke test, has been executed in a clean environment.

## Score new session records

The included predictor expects the 22 fields listed in `models/decision_threshold.json`.

```bash
python src/predict.py --input new_sessions.csv --output predictions.csv
```

The output adds `dial_alert_probability` and `dial_alert_flag`. A flag is a model output, not a diagnosis or treatment recommendation.

## Validation design

- Training: 64,053 sessions / 496 patients
- Validation: 21,351 sessions / 164 patients
- Test: 21,354 sessions / 170 patients
- Patient overlap across partitions: zero
- Model search: three-fold grouped cross-validation on training patients
- Threshold selection: maximum F2 on validation patients only
- Uncertainty: 500 bootstrap resamples of whole test patients

## Additional analyses — clearly secondary

Analyses that would strengthen the work, without repeatedly tuning against the existing test set, include: advance-warning time; a baseline-SBP + prior-hypotension clinical comparator; ablation of historical features including first-observed sessions; equally calibrated finalist comparison; sensitivity to extreme UF/fluid-excess values and short-session exclusions; and stronger presentation of patient-level uncertainty.

These should be labeled secondary/exploratory unless specified prospectively. External/temporal validation, fairness confirmation on fresh data, and staged prospective evaluation remain future work.

## Step 8: Deployment & MLOps

The repository now contains a local Flask inference package in `step8_deployment/`. It loads the included model and exposes health and prediction endpoints. This demonstrates local packaging only; it is **not clinical deployment**. A recorded Step 8 screencast is not currently included, so the optional step should not be described as fully demonstrated until that media is added.

## Step 9: Use of Generative AI

See `step9_genai/README.md` and `step9_genai/demo/DIAL_ALERT_Step9_Demo.mp4`. Step 9 demonstrates **replay of a saved AI-assisted draft with source-linked numeric validation**. It does **not** demonstrate live LLM generation, an LLM-backed clinical recommender, or a live model call.

## Limitations

The endpoint is BP-defined rather than a complete symptomatic IDH diagnosis. The dataset is retrospective and single-center and omits symptoms, interventions, medications, laboratory values, and many comorbidities. The locked test set contains only **170 independent patients**. The model has not been externally, temporally, or prospectively validated. Current fairness mitigation findings are exploratory and require confirmation on fresh data.

## License and attribution

Project code is released under the MIT License. HEMOBP is a separate work released under CC BY 4.0; its original authors and license must be credited when the data are used. The fitted model is derived from HEMOBP and is provided only for academic reproducibility.

## Author

Franklin B. Guillano
