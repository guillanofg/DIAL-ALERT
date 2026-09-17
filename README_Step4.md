# DIAL ALERT Step 4 Model Implementation

This submission implements and compares supervised classifiers for predicting later blood-pressure-defined intradialytic hypotension from information available at the index time. The analytic cohort and preprocessing rules are inherited from Steps 2 and 3.

## Why supervised classification

The target is a prespecified binary outcome. Clustering, recommender systems, and deep learning do not answer the stated prediction question. Deep neural models were not added because the predictors are structured tabular variables, the cohort has only 830 independent patient groups, and clinical interpretability and calibration are more important than architectural complexity. Histogram gradient boosting supplies a reproducible boosted-tree benchmark without an external compiled dependency.

## Reproduce the analysis

1. Create an environment with Python 3.12 and install `requirements-step4.txt`.
2. Obtain the public HEMOBP source files and place `idp.csv`, `d1.csv`, and `vip.csv` in `data/raw`.
3. Run the following commands from the project root.

```bash
python src/build_session_dataset.py --raw-dir data/raw --output-dir data/processed
python src/train_evaluate.py --data data/processed/hemobp_session_level.csv.gz --config configs/model_config.json --artifacts artifacts --models models
python src/generate_step4_assets.py
```

The model script uses patient-disjoint training, validation, and test partitions. Hyperparameter searches use grouped cross-validation and optimize average precision. Calibration choice and the F2 operating threshold are selected using validation patients only. The test set is evaluated once after all choices are locked.

## Score new records

```bash
python src/predict.py --input new_sessions.csv --output predictions.csv
```

The input must contain all features listed in `models/decision_threshold.json`. The output includes `dial_alert_probability` and `dial_alert_flag`.

## Main artefacts

- `models/dial_alert_final_predictor.joblib` is the selected random-forest pipeline.
- `models/decision_threshold.json` records the operating threshold and feature order.
- `models/model_manifest.json` records file hashes, versions, and random seeds.
- `artifacts/model_comparison.csv` contains grouped cross-validation and validation metrics.
- `artifacts/final_test_metrics.json` contains the locked test-set assessment.
- `artifacts/test_metric_confidence_intervals.csv` contains patient-cluster bootstrap intervals.
- `artifacts/capacity_metrics.csv` translates ranking performance into alert workload.

## Intended use

This is an academic clinical decision-support prototype. It is not a diagnostic device and must not guide patient care without external and prospective validation, workflow testing, and governance approval.
