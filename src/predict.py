"""Score session-level DIAL-ALERT records with the saved Step 4 predictor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


def score_file(input_path: Path, model_path: Path, threshold_path: Path, output_path: Path) -> None:
    predictor = joblib.load(model_path)
    threshold_spec = json.loads(threshold_path.read_text(encoding="utf-8"))
    features = list(threshold_spec["features"])
    threshold = float(threshold_spec["threshold"])

    frame = pd.read_csv(input_path)
    missing = sorted(set(features) - set(frame.columns))
    if missing:
        raise ValueError(f"Input is missing required features: {missing}")

    model_input = frame[features].copy()
    # Training applies log1p to the raw count before the fitted pipeline.
    model_input["prior_session_count"] = np.log1p(
        model_input["prior_session_count"].clip(lower=0)
    )
    probability = predictor.predict_proba(model_input)[:, 1]
    output = frame.copy()
    output["dial_alert_probability"] = probability
    output["dial_alert_flag"] = (probability >= threshold).astype(int)
    output.to_csv(output_path, index=False)
    print(f"Wrote {len(output):,} predictions to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--model", type=Path, default=Path("models/dial_alert_final_predictor.joblib")
    )
    parser.add_argument(
        "--threshold", type=Path, default=Path("models/decision_threshold.json")
    )
    parser.add_argument("--output", type=Path, default=Path("predictions.csv"))
    args = parser.parse_args()
    score_file(args.input, args.model, args.threshold, args.output)


if __name__ == "__main__":
    main()
