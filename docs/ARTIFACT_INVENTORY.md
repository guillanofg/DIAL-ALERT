# Included and regenerated artifacts

Updated: 23 September 2026.

## Artifact inventory

| Item | Distribution and rebuild |
| --- | --- |
| Selected random forest | Included: models/dial_alert_final_predictor.joblib. No post-hoc calibration was retained. |
| Threshold and feature contract | Included: models/decision_threshold.json. Supply the raw prior-session count; scoring applies the log1p transformation. |
| Candidate and mitigation models | Not bundled. Regenerate using the training and fairness scripts. The original model manifest also records development outputs that are not included. |
| Raw HEMOBP tables | Not bundled. Download Version 3 using src/download_data.py and verify checksums. |
| Session table, split assignments, and patient-level audit intermediates | Not bundled. Regenerate locally and exclude patient-level files from publication. |
| Metrics and figures | Included aggregate results represent the locked reference analysis. Numerical comparisons with the fresh reproduction are documented separately. |
| Reports and two decks | Included revised binaries. Report and presentation generation scripts must retain the corrections made to the final deliverables. |
| Step 8 | Local Flask app, synthetic request, HTTP execution record, and animated demo. This demonstrates local inference, not clinical or cloud deployment. |
| Step 9 earlier demonstration | step9_genai contains saved-draft replay, numeric checks, examples, and media. This earlier demonstration does not establish live generation. |
| Step 9 live demonstration | step9_assistant contains the local Ollama project assistant, examples, review evidence, and edited live-demo video. Observed answer-quality limitations remain; citation and numeric checks do not establish semantic correctness. |

## Reproducibility status

The execution record documents successful end-to-end reproduction on 20 September 2026 using Python 3.12 on macOS.

HEMOBP Version 3 files were downloaded and checksum-verified. The analytical dataset was rebuilt, models were retrained and evaluated, analysis outputs were regenerated, and the automated test suite completed with 15 passed, 0 failed, and 0 skipped.

The reproduced results were numerically consistent with the locked reference rather than byte-for-byte identical. See REPRODUCIBILITY_RECORD.md for the numerical comparison and execution details.

The failed acquisition attempt on 18 September 2026 is retained as historical context. It is not the current reproduction status.

This evidence establishes the documented analysis run. It does not establish that every optional document, workbook, presentation, and demo builder was independently reproduced in a fresh environment.

## Python and native dependencies

Core analysis uses Python 3.12 and requirements.txt. Step 8 has additional instructions in step8_deployment/requirements-step8.txt.

Editing the supplied presentations with the Python revision script requires python-pptx==1.0.2. PDF export and raster review require LibreOffice, Poppler, and appropriate fonts. Animated demo generation requires Pillow.

These authoring dependencies are separate from model inference. Step 9 live generation additionally requires the local setup described in step9_assistant/README.md.

## Presentation source dependencies

src/create_step6_presentations.mjs requires Node.js, @oai/artifact-tool, and container_tools/artifact_tool_utils.mjs, together with the validators and metadata tools invoked by that helper environment.

It also requires Nimbus Sans and Nimbus Mono PS fonts and the project figures. This specialized JavaScript authoring environment is not bundled or installed by requirements.txt.

The builder requires absolute SKILL_DIR, WORKSPACE_DIR, TMP_DIR, OUTPUT_DIR, and RUNTIME_PYTHON paths. Run it with --finalize in a compatible environment, then apply the current presentation revision script.

Without that environment, the included PPTX files remain editable in presentation software. Render and visually inspect both decks after changes.

## Full analysis order

Run from the repository root in a separate checkout so that regeneration does not overwrite the locked reference outputs.

Install requirements.txt, then execute:

```bash
python src/download_data.py
python src/build_session_dataset.py --raw-dir data/raw --output-dir data/processed
python src/generate_step2_assets.py
python src/train_evaluate.py --data data/processed/hemobp_session_level.csv.gz --config configs/model_config.json --artifacts artifacts --models models
python src/generate_eda.py
python src/generate_step4_assets.py
python src/audit_bias_fairness.py
python src/create_step2_report.py
python src/create_eda_report.py
python src/create_model_report.py
python src/create_bias_fairness_report.py
python src/create_final_report.py
python src/revise_submission_documents.py
python -m pytest -q
```

This is the analysis and report-generation order. Consult REPRODUCIBILITY_RECORD.md for the commands and outputs documented in the successful reproduction.

Step 2 also includes a JavaScript workbook generator with separate authoring dependencies. The supplied workbook can be inspected without rebuilding it.

The Python report commands produce DOCX files. Export updated documents to PDF separately and visually inspect them before publication.

## Publication checks

Keep raw data, processed patient-level records, credentials, and private files out of Git.

Check regenerated reports and decks against the locked reference metrics, current Step 9 evidence, corrected references, and documented eligibility and alert policies.

Documentation corrections do not require model retraining.