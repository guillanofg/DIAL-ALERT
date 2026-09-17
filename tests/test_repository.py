from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_feature_contract_matches_model_configuration() -> None:
    config = load_json("configs/model_config.json")
    threshold = load_json("models/decision_threshold.json")
    expected = config["numeric_features"] + config["categorical_features"]
    assert threshold["features"] == expected
    assert 0 < threshold["threshold"] < 1


def test_locked_results_are_internally_consistent() -> None:
    result = load_json("artifacts/final_test_metrics.json")["test_metrics_calibrated"]
    total = result["tn"] + result["fp"] + result["fn"] + result["tp"]
    assert total == 21354
    assert result["tp"] + result["fn"] == 1814
    assert 0 <= result["average_precision"] <= 1
    assert 0 <= result["roc_auc"] <= 1
    assert 0 <= result["brier_score"] <= 1


def test_split_summary_has_patient_disjoint_partitions() -> None:
    summary = pd.read_csv(ROOT / "artifacts/split_summary.csv")
    assert set(summary["split"]) == {"training", "validation", "test"}
    assert int(summary["sessions"].sum()) == 106758
    assert int(summary["patients"].sum()) == 830


def test_required_publication_files_exist() -> None:
    required = [
        "README.md",
        "LICENSE",
        "CITATION.cff",
        "docs/data_dictionary.md",
        "docs/model_card.md",
        "reports/Franklin_Guillano_DIAL_ALERT_Final_Report.pdf",
        "reports/Franklin_Guillano_DIAL_ALERT_Technical_Presentation.pptx",
        "reports/Franklin_Guillano_DIAL_ALERT_Business_Presentation.pptx",
    ]
    missing = [path for path in required if not (ROOT / path).is_file()]
    assert not missing, f"Missing required publication files: {missing}"

