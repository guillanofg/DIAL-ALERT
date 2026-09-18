# DIAL-ALERT — Optional Step 8: Local Deployment & MLOps

This folder packages the **existing saved random-forest predictor** as a local Flask service. It is an academic deployment demonstration, not a clinical device.

## What is implemented

- Local Flask app with `/health` and `/predict` endpoints.
- Loads `models/dial_alert_final_predictor.joblib` and the 22-feature contract in `models/decision_threshold.json`.
- Returns probability plus the validation-selected threshold flag.
- Uses no API key and sends no data to an external service.
- Versioning/rollback uses the Git commit plus `models/model_manifest.json`.

## Install and run

From the repository root:

```bash
python -m venv .venv-step8
source .venv-step8/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r step8_deployment/requirements-step8.txt
python step8_deployment/app.py
```

Then open `http://127.0.0.1:8000/health`.

## Prediction request

POST JSON to `http://127.0.0.1:8000/predict` with all 22 model features. A template is provided in `sample_request.json`.

Example:

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  --data @step8_deployment/sample_request.json
```

## Monitoring plan

For any future silent-mode evaluation, log only governed, minimum-necessary operational fields. Monitor input completeness, score distribution, alert volume, latency, calibration, sensitivity, false-alert workload, subgroup performance, and model/data drift. Do not publish patient-level logs.

## Versioning and rollback

Record the Git commit, model SHA/hash from `models/model_manifest.json`, environment versions, and deployment date. If validation fails, data schema changes, drift is material, subgroup safety concerns emerge, or alert workload exceeds the pre-registered limit, disable the service and revert to the previously validated model/commit.

## Evidence status

The **app and instructions are included**. A recorded Step 8 GIF/screencast is **not currently included**, so this optional step should not be described as fully demonstrated until a real run is recorded and added. No cloud deployment is claimed.
