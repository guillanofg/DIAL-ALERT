"""Local academic inference service for DIAL-ALERT Step 8."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "dial_alert_final_predictor.joblib"
CONTRACT_PATH = ROOT / "models" / "decision_threshold.json"

with CONTRACT_PATH.open("r", encoding="utf-8") as handle:
    CONTRACT = json.load(handle)

FEATURES = CONTRACT["features"]
THRESHOLD = float(CONTRACT["threshold"])
MODEL = joblib.load(MODEL_PATH)

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(
        status="ok",
        model="DIAL-ALERT random forest",
        feature_count=len(FEATURES),
        threshold=THRESHOLD,
        clinical_use=False,
    )


@app.post("/predict")
def predict():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Expected one JSON object."), 400

    missing = [name for name in FEATURES if name not in payload]
    extra = [name for name in payload if name not in FEATURES]
    if missing or extra:
        return jsonify(error="Feature contract mismatch.", missing=missing, extra=extra), 400

    frame = pd.DataFrame([{name: payload[name] for name in FEATURES}])
    probability = float(MODEL.predict_proba(frame)[:, 1][0])
    return jsonify(
        dial_alert_probability=probability,
        dial_alert_flag=bool(probability >= THRESHOLD),
        operating_threshold=THRESHOLD,
        interpretation="Academic model output only; not a diagnosis or treatment recommendation.",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
