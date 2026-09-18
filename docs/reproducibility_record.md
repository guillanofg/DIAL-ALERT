# Reproducibility execution record

Source snapshot: `e1330231bba9ff4ff85bf051c1baa322f3e55951`, with submission-documentation revisions applied. The fitted predictor and operating threshold remain byte-for-byte unchanged.

A new isolated Python 3.12.14 virtual environment installed requirements.txt successfully using uv. It did not inherit system site packages. No raw patient data were used in the synthetic inference check.

| Command or stage | Actual outcome |
|---|---|
| `uv venv --python 3.12 <fresh-environment>` | Passed |
| `uv pip install --python <fresh-environment>/bin/python -r requirements.txt` | Passed |
| `python -m pytest -q` | 11 tests passed |
| `python -m unittest discover -s step9_genai/tests -v` | 12 tests passed |
| `python src/predict.py --input examples/synthetic_session.csv --output predictions.csv` | Passed; probability 0.06264385529386092, flag 0 |
| `python src/download_data.py` | Failed with HTTP 403 while acquiring d1.csv |
| Raw-data cohort build, training and downstream audit reproduction | Not run because verified source files were unavailable |

The publisher metadata request succeeded far enough to begin d1.csv acquisition. No unverified substitute data were used. An acquisition failure is not evidence that the model is incorrect, but it prevents a full reproduction claim. The missing raw-data stages remain to be run where publisher access is available, using the documented checksums and instructions.

The passing tests establish repository contracts and synthetic inference behavior, not clinical safety, statistical validity, or fresh model training. Exact package versions and model/threshold SHA-256 values are recorded in `artifacts/reproduction_verification.json`.

Document and slide revisions use existing aggregate artifacts. No performance estimates were newly calculated from patient records or substituted for the locked results.
