# Included and regenerated artifacts

| Item | Distribution and rebuild |
| --- | --- |
| Selected random forest | Included: `models/dial_alert_final_predictor.joblib`; no post-hoc calibration |
| Threshold and 22-feature contract | Included: `models/decision_threshold.json`; supply the raw prior-session count, transformed with log1p during scoring |
| Candidate models and mitigation models | Not bundled. Rebuild with training and fairness scripts; the original model manifest records development outputs, including absent candidates |
| Raw HEMOBP tables | Not bundled. Download Version 3 with `src/download_data.py` and verify checksums |
| Session table, partition assignments, detailed audit intermediates | Not bundled. Regenerate locally; do not publish patient-level files |
| Metrics and figures | Included aggregate reference results. They are original study outputs, not the outcome of the 18 September clean-environment attempt |
| Reports and two decks | Included revised binaries. Report edits can be applied with `src/revise_submission_documents.py`; PPTX edits with `src/revise_submission_presentations.py` |
| Step 8 | Flask app, synthetic request, HTTP execution record and animated demo; no cloud or clinical deployment |
| Step 9 | Saved-draft replay with numeric checks and media; no demonstrated live LLM generation |

## Python and native dependencies

Core analysis: Python 3.12 and `requirements.txt`. Step 8 additionally needs `step8_deployment/requirements-step8.txt`. Editing the supplied slides needs `python-pptx==1.0.2`. PDF export and raster review need LibreOffice, Poppler and appropriate fonts. Animated demo generation needs Pillow. These authoring dependencies are separate from model inference.

## Presentation source dependencies

`src/create_step6_presentations.mjs` requires Node.js, the `@oai/artifact-tool` package, and the helper module `container_tools/artifact_tool_utils.mjs` plus the package/layout validators and metadata tools it invokes. It also needs Nimbus Sans and Nimbus Mono PS fonts and the included project figures. This specialized JavaScript authoring environment is **not bundled or installed by requirements.txt**; a standard npm/Python install is not asserted to recreate it.

The script requires absolute `SKILL_DIR` (helper bundle), `WORKSPACE_DIR` (repository), `TMP_DIR`, `OUTPUT_DIR`, and `RUNTIME_PYTHON` paths. Run it with `--finalize` in that compatible environment, then run `python src/revise_submission_presentations.py` to apply the final wording and readable summary slides. Without that JavaScript environment, the included PPTX files remain editable in presentation software or with the supplied Python revision script. Rendering and visual review are still required after edits.

## Full analysis order

Use a separate checkout/output location so a verification run does not overwrite the locked reference results. Install core requirements and run:

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

Step 2 also has a JavaScript workbook generator requiring its own authoring package; the included data dictionary workbook can be inspected without rebuilding it. Follow the report generators' data prerequisites and sanitize regenerated artifacts before publication. The complete above sequence remains unverified in a fresh environment because source acquisition failed; see the execution record.
