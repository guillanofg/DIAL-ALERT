# Fresh-environment reproducibility record

Date: 18 September 2026. Baseline repository commit: `a313a5fc7b510af5921ba049c2edbf586b3e0d72`. This record covers the submission revision based on that commit; the final revision commit contains this record and the accompanying checks.

**Result: partial verification only. Full data-to-training reproduction is blocked.** The source acquisition command returned HTTP 403, so cohort reconstruction, model search, retraining, fairness reruns and numerical comparison with the original test results were not executed. No original test results were replaced or retuned.

## Environment and commands

A new isolated virtual environment used Python **3.12.14**. Installation from `requirements.txt` and `step8_deployment/requirements-step8.txt` succeeded. Exact installed packages are in [environment-freeze.txt](verification/environment-freeze.txt).

| Step | Command or check | Observed result |
| --- | --- | --- |
| Environment | `python -m venv` then pip install from the two requirements files | Completed in a new environment |
| Acquire Version 3 | `python src/download_data.py` | Exit 1: `Data acquisition failed: HTTP Error 403: Forbidden` |
| Build cohort through retraining | Published data-dependent sequence | Not run: prerequisite data unavailable |
| Original README test invocation | `pytest -q` | Initially failed collection: repository root was not on the import path |
| Test-path correction | Explicit pytest `pythonpath = ["."]` | Corrected; CI now uses `python -m pytest` |
| Repository, inference and replay tests | `python -m pytest -q tests step9_genai/tests` | **27 passed**; [execution output](verification/tests.txt) |
| Saved predictor CLI | `python src/predict.py --input <synthetic CSV> --output <prediction CSV>` | One prediction written; probability **0.07625256348399012**, flag **0** |
| Real localhost HTTP | `python src/record_step8_demo.py` | Health OK; same synthetic probability and false flag; [responses](../step8_deployment/demo/http_execution.json) |
| Preprocessing agreement | Raw prior-session counts 0, 10 and 250 | API and CLI probabilities agree within 1e-12 after the app fix |
| Step 9 replay | `python step9_genai/src/replay_summary.py` | Completed; [output](verification/step9-replay.txt). No live LLM call |
| Document review | Revised reports exported to PDF and page images | Rendered pages reviewed; PDF companions refreshed |
| Presentation review | Both revised PPTX files rendered | 16 technical and 11 business slides reviewed; crowded business fairness chart replaced |

The app originally omitted the `log1p` transform of the raw prior-session count. It now applies the same transform as training and the CLI. A stale Step 9 README checksum was also corrected after reviewing its unchanged replay-only scope. These fixes do not alter the fitted model.

The fitted predictor retains SHA-256 `efb0f4d44b6569838259728d164b22e87e43bd73f058882a8491aba82639aa75`. The original model, threshold and model-selection configuration remain locked.

## What remains necessary

Run [the complete sequence](ARTIFACT_INVENTORY.md#full-analysis-order) from an environment that can retrieve the publisher's fixed Version 3 data. Preserve the original metrics in a separate checkout. Verify publisher file sizes/checksums, rebuild the cohort, train with the locked configuration, generate artifacts, run tests and compare prediction outputs. Record command exits, elapsed time, package versions and numerical tolerances. Do not infer full reproducibility from successful loading of an existing model.

Reference values to compare: 106,758 sessions / 830 patients; 21,354 test sessions / 170 patients; AP 0.3947805460; ROC AUC 0.8524597016; Brier 0.0621152148; threshold 0.1428558780. These are original study results, not newly reproduced estimates. Compressed intermediate-file hashes may differ with timestamps; use content and numerical comparisons as well as provenance checks.
## Successful end-to-end reproduction — 20 September 2026

A fresh end-to-end reproduction was successfully completed using Python 3.12 on macOS.

The HEMOBP Version 3 source data were downloaded from Figshare using the repository acquisition script. The source files d1.csv, idp.csv, and vip.csv were checksum-verified. An initial SSL certificate verification problem was resolved using the certifi certificate bundle, and two vip.csv download attempts timed out before a subsequent attempt completed successfully.

The session-level analytical dataset was rebuilt from the raw source data. The reproduced dataset contained 106,758 eligible sessions from 830 unique patients, including 9,067 primary IDH events (prevalence approximately 8.49%).

The complete analysis sequence was then executed successfully, including dataset construction, Step 2 audit generation, model training and evaluation, exploratory data analysis, Step 4 report graphics, bias/fairness analysis, and final report generation.

The patient-level split was reproduced with 64,053 training sessions from 496 patients, 21,351 validation sessions from 164 patients, and 21,354 test sessions from 170 patients.

The repository automated test suite was executed after installing the Flask dependency. Final result: 15 passed, 0 failed, 0 skipped.

Flask==3.1.3 was subsequently added to requirements.txt so that future fresh-environment installations include the dependency required by the inference/application tests.

Status: End-to-end data-to-training reproduction successfully completed and verified on 20 September 2026.
