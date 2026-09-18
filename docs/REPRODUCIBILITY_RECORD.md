# Fresh-environment reproducibility record

## Purpose

This file records whether the published instructions have been executed end-to-end in a clean environment. It must not be marked complete based only on the original development environment.

## Required verification sequence

1. Create a new Python 3.12 virtual environment.
2. Install `requirements.txt`.
3. Run `python src/download_data.py` and confirm checksum verification.
4. Run `src/build_session_dataset.py`.
5. Run `src/train_evaluate.py` with the published config.
6. Regenerate EDA, Step 4, fairness, and final-report artifacts.
7. Run `pytest -q`.
8. Run `src/predict.py` on a valid 22-feature sample and confirm probability + flag output.
9. Compare key cohort counts and locked metrics with the published reference values.

## Reference values

- Final cohort: 106,758 sessions / 830 patients
- Event prevalence: 8.49%
- Test: 21,354 sessions / 170 patients
- Selected model: Random forest
- Test average precision: 0.395
- Test ROC AUC: 0.852
- Test Brier score: 0.062
- Probability threshold: 0.142855878 (0.143 reported)

## Status

**PENDING CLEAN-ENVIRONMENT EXECUTION.**

The repository documentation has been corrected to make the reproduction sequence explicit, but this record is intentionally not presented as a successful fresh-environment run until the full sequence is actually executed and its console log is saved here or as an attached text artifact.

## Execution log

Date: pending  
Environment: pending  
Git commit: pending  
Result: pending
