# Reproduction guide

## Core Python workflow

Use a separate checkout and Python 3.12. Training regenerates local models and result artifacts; do not replace a locked published model merely because a verification run differs.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m unittest discover -s step9_genai/tests -v
python src/predict.py --input examples/synthetic_session.csv --output predictions.csv
python src/download_data.py
python src/build_session_dataset.py --raw-dir data/raw --output-dir data/processed
python src/train_evaluate.py --data data/processed/hemobp_session_level.csv.gz --config configs/model_config.json --artifacts artifacts --models models
python src/generate_eda.py
python src/generate_step4_assets.py
python src/audit_bias_fairness.py
python src/generate_step2_assets.py
python src/create_step2_report.py
python src/create_eda_report.py
python src/create_model_report.py
python src/create_bias_fairness_report.py
python src/create_final_report.py
```

The example is entirely synthetic and is not a patient record. For Windows, activate with `.venv\Scripts\activate`. Generation of the Step 2 spreadsheet and Step 6 decks needs the additional JavaScript environment below. DOCX-to-PDF conversion also needs LibreOffice and appropriate fonts. Python-only model training and inference do not require the presentation runtime.

The public source totals approximately 274 MB. RAM use exceeds source-file size because pandas holds multiple intermediate tables. Runtime depends on hardware; no universal runtime is promised. The fixed Figshare Version 3 publisher checksums must pass. If acquisition returns HTTP 403, resolve access through the publisher; do not substitute unverified files or claim a completed reproduction. Consult `docs/reproducibility_record.md` for this release's actual checks.

## Published versus regenerated

| Included in Git | Regenerated locally |
|---|---|
| Selected fitted predictor and decision threshold | Candidate fitted models and experimental mitigation models |
| Configuration and historical model manifest | Raw HEMOBP files and processed session table |
| Aggregate metrics and plots | Patient-level partition assignments |
| Reports, presentations and notebook | Detailed audit intermediates excluded by .gitignore |

The historical manifest lists training-run outputs; `release_included` identifies which are distributed. Source-data hash values describe the original run. Compressed-file bytes can vary even when table values agree; compare cohort counts, partitions and numeric results in addition to hashes. Never publish raw records or patient-level split assignments.

## Presentation and spreadsheet authoring dependencies

`src/create_step6_presentations.mjs` uses Node.js ES modules, `@oai/artifact-tool`, Nimbus Sans and Nimbus Mono PS fonts, and externally supplied presentation helper/validator files under `SKILL_DIR`. These are not installed by requirements.txt and are not bundled in this repository. The original managed authoring runtime is required for that builder. Set absolute `WORKSPACE_DIR`, `TMP_DIR`, `OUTPUT_DIR`, `SKILL_DIR`, `RUNTIME_PYTHON`, `RUNTIME_NODE`, `RUNTIME_NODE_MODULES`, and `RUNTIME_BIN_DIR` paths. Run draft export first and `--finalize` after inspection. Final output must be in a new directory because the finalizer does not overwrite files.

The Step 2 workbook builder also relies on its documented JavaScript artifact runtime. The distributed XLSX and PPTX files can be opened and edited independently of these builders. Full presentation regeneration is therefore environment-dependent; core Python model reproducibility is a separate claim.

## Verification record

Record the source commit, Python and package versions, commands, exit codes, hashes of the model and threshold, test results and any differences in regenerated metrics. Keep records aggregate-only. The existing test suite checks inference and repository contracts; it does not demonstrate clinical effectiveness or reproduce training by itself.
