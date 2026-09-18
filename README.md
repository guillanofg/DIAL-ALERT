# DIAL ALERT

DIAL-ALERT is an end-to-end machine-learning capstone that estimates the risk of a later systolic blood-pressure reading below 90 mmHg during an eligible haemodialysis session. It uses only information available at the index time or from earlier sessions and keeps every patient's sessions within one data partition.

> **Academic prototype only.** DIAL-ALERT is not a diagnostic device and must not guide patient care without external validation, prospective silent-mode testing, human-factors evaluation, and institutional governance approval.

## Main result

The selected random-forest pipeline was evaluated once on 21,354 sessions from 170 patients who were excluded from model fitting and threshold selection.

| Measure | Locked test result |
| --- | ---: |
| Average precision | 0.395 |
| ROC AUC | 0.852 |
| Brier score | 0.062 |
| Sensitivity at threshold 0.143 | 66.1% |
| Specificity at threshold 0.143 | 86.1% |
| Precision at threshold 0.143 | 30.6% |
| Recall within the highest-risk 20% of sessions | 69.1% |
| Lift within the highest-risk 20% | 3.46 |

These are retrospective prediction results. They do not show that an alert prevents hypotension, improves outcomes, or saves money.

## Problem and task

The clinical operations question is whether information available early in a dialysis session can identify sessions that merit closer observation. The data-science task is supervised binary classification. The primary outcome is any later systolic blood-pressure measurement below 90 mmHg. Average precision is the primary technical metric because the event prevalence is 8.49%. Secondary measures cover discrimination, calibration, threshold performance, alert capacity, and fairness.

## Data

The project uses HEMOBP Version 3, a public dataset released on Figshare under CC BY 4.0 and described in *Scientific Data*.

- Dataset DOI: [10.6084/m9.figshare.6260654.v3](https://doi.org/10.6084/m9.figshare.6260654.v3)
- Data descriptor: [10.1038/s41597-019-0319-8](https://doi.org/10.1038/s41597-019-0319-8)
- Source files: `idp.csv`, `d1.csv`, and `vip.csv`
- Final analytic cohort: 106,758 sessions from 830 patients

Raw and processed data are intentionally excluded from Git because the largest source file exceeds GitHub's ordinary file limit. The download script retrieves the fixed Version 3 files and verifies the publisher-provided MD5 checksums.

## Repository contents

| Path | Purpose |
| --- | --- |
| `src/` | Data acquisition, cohort construction, EDA, training, auditing, prediction, and report scripts |
| `notebooks/` | Guided reproducible workflow and rapid result review |
| `data/` | Empty raw and processed directories with acquisition instructions |
| `models/` | Selected fitted predictor, threshold, and model manifest |
| `artifacts/` | Machine-readable metrics and publication-ready figures |
| `docs/` | Data dictionaries, preprocessing specification, and model card |
| `reports/` | Final report, component reports, and audience-specific presentations |
| `tests/` | Repository and inference smoke tests |
| `.github/workflows/` | Automated test workflow |

## Quick start

Use Python 3.12 from the repository root.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Download and verify the public data:

```bash
python src/download_data.py
```

Rebuild the analytic table and model results:

```bash
python src/build_session_dataset.py --raw-dir data/raw --output-dir data/processed
python src/train_evaluate.py \
  --data data/processed/hemobp_session_level.csv.gz \
  --config configs/model_config.json \
  --artifacts artifacts \
  --models models
python src/generate_eda.py
python src/generate_step4_assets.py
python src/audit_bias_fairness.py
```

Create the consolidated report after the figures and metrics exist:

```bash
python src/create_final_report.py
```

The notebook `notebooks/01_reproducible_workflow.ipynb` presents the same sequence with explanations. The `Makefile` provides equivalent shortcuts.

## Score new session records

The repository includes the selected predictor. Input CSV files must contain the 22 fields listed in `models/decision_threshold.json`.

```bash
python src/predict.py --input new_sessions.csv --output predictions.csv
```

The output adds `dial_alert_probability` and `dial_alert_flag`. A flag means that the estimated risk exceeds the validation-selected operating threshold; it is not a diagnosis or treatment recommendation.

## Validation design

- Training: 64,053 sessions from 496 patients
- Validation: 21,351 sessions from 164 patients
- Test: 21,354 sessions from 170 patients
- Patient overlap across partitions: zero
- Model search: three-fold grouped cross-validation on training patients
- Model selection: grouped-CV average precision, with validation Brier score as the prespecified tie-breaker
- Threshold selection: maximum F2 score on validation patients only
- Uncertainty: 500 bootstrap resamples of whole test patients

## Models compared

The analysis compares a prevalence baseline, logistic regression, embedded L1 feature selection, decision tree, PCA logistic regression, random forest, and histogram gradient boosting. Random forest was selected because it was within 0.01 of the best grouped-CV average precision and had better validation calibration than the boosted-tree candidate.

## Explainability and fairness

The audit combines permutation importance, aggregate approximate interventional SHAP values, synthetic SHAP and LIME local explanations, and dependence curves across synthetic reference profiles. No patient-level explanation table or observed-patient local example is published. Fairness metrics cover recorded sex and age; diabetes is treated as a clinical subgroup. Race, ethnicity, socioeconomic status, and gender identity are unavailable and cannot be audited.

Outcome-by-sex reweighting improved some recorded-sex disparity measures with essentially unchanged average precision. Sex-specific thresholds did not transfer well to the test set and were rejected. Full details and uncertainty intervals are in `reports/Franklin_Guillano_DIAL_ALERT_Final_Report.pdf` and `docs/model_card.md`.

## Reproducibility

- Configuration and random seeds are stored in `configs/model_config.json`.
- Model hashes and software versions are stored in `models/model_manifest.json`.
- Split assignments and all reported metrics have machine-readable artifacts.
- Tests validate repository contracts and run an end-to-end inference smoke test.
- Continuous integration executes the tests on each push and pull request.

Small numerical differences may occur across hardware or dependency builds. The pinned environment, patient-level split logic, and saved manifests allow those differences to be identified.

## License and attribution

Project code is released under the MIT License. HEMOBP is a separate work released under CC BY 4.0; its original authors and license must be credited when the data are used. The fitted model is derived from HEMOBP and is provided only for academic reproducibility.

## Author

Franklin B. Guillano

## Step 9: Use of Generative AI

See [the Step 9 documentation, code, and examples](step9_genai/README.md) and the [63-second demo video](step9_genai/demo/DIAL_ALERT_Step9_Demo.mp4). This demonstrates AI-assisted authoring with source-linked numeric validation. The code replays a saved draft; it does not make a live LLM call or change the predictive model.

