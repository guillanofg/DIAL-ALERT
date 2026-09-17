from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.predict import score_file


ROOT = Path(__file__).resolve().parents[1]


def test_saved_model_scores_a_valid_input(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "age_years": 60,
                "dialysis_vintage_years": 5.0,
                "weightstart": 65.0,
                "dryweight": 63.0,
                "temperature": 36.5,
                "fluid_excess_kg": 2.0,
                "fluid_excess_pct": 3.17,
                "baseline_sbp": 130.0,
                "baseline_dbp": 70.0,
                "baseline_map": 90.0,
                "baseline_pulse_pressure": 60.0,
                "initial_uf_l_h": 0.7,
                "initial_uf_ml_kg_h": 10.77,
                "initial_blood_flow_ml_min": 250.0,
                "initial_dialysate_temp_c": 36.5,
                "initial_conductivity_ms_cm": 14.0,
                "prior_session_idh": 0.0,
                "prior_nadir_sbp": 100.0,
                "prior_idh_rate": 0.10,
                "prior_session_count": 10,
                "gender": "M",
                "DM": 1,
            }
        ]
    )
    input_path = tmp_path / "session.csv"
    output_path = tmp_path / "prediction.csv"
    frame.to_csv(input_path, index=False)

    score_file(
        input_path,
        ROOT / "models/dial_alert_final_predictor.joblib",
        ROOT / "models/decision_threshold.json",
        output_path,
    )

    result = pd.read_csv(output_path)
    assert result.shape[0] == 1
    assert result["dial_alert_probability"].between(0, 1).all()
    assert set(result["dial_alert_flag"]).issubset({0, 1})

