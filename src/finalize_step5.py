"""Validate DIAL-ALERT Step 5 deliverables and write a checksum manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import joblib
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"
MANIFEST = ARTIFACTS / "step5_submission_manifest.json"


REQUIRED = [
    ROOT / "README_Step5.md",
    ROOT / "requirements-step5.txt",
    ROOT / "src" / "audit_bias_fairness.py",
    ROOT / "src" / "create_bias_fairness_report.py",
    ROOT / "src" / "create_eda_report.py",
    ROOT / "src" / "build_session_dataset.py",
    ROOT / "src" / "train_evaluate.py",
    ROOT / "src" / "predict.py",
    ROOT / "src" / "finalize_step5.py",
    ROOT / "configs" / "model_config.json",
    ARTIFACTS / "split_metadata.json",
    ARTIFACTS / "model_comparison.csv",
    ARTIFACTS / "final_test_metrics.json",
    ARTIFACTS / "step5_disparities.csv",
    ARTIFACTS / "step5_disparity_intervals.csv",
    ARTIFACTS / "step5_patient_weighted_disparities.csv",
    ARTIFACTS / "step5_attribute_availability.csv",
    ARTIFACTS / "step5_counterfactual_sex_audit.json",
    ARTIFACTS / "step5_sex_specific_thresholds.json",
    ARTIFACTS / "step5_mitigation_comparison.csv",
    ARTIFACTS / "step5_shap_global_importance.csv",
    ARTIFACTS / "step5_shap_local_synthetic.csv",
    ARTIFACTS / "step5_lime_local_synthetic.csv",
    ARTIFACTS / "step5_lime_local_metadata.json",
    ARTIFACTS / "step5_robustness_audit.csv",
    ARTIFACTS / "step5_ethical_risk_register.csv",
    ARTIFACTS / "step5_audit_summary.json",
    ARTIFACTS / "step5_fairness_overview.png",
    ARTIFACTS / "step5_disparity_summary.png",
    ARTIFACTS / "step5_mitigation_tradeoff.png",
    ARTIFACTS / "step5_shap_summary.png",
    ARTIFACTS / "step5_shap_local_synthetic.png",
    ARTIFACTS / "step5_lime_local_synthetic.png",
    ARTIFACTS / "step5_pdp_ice.png",
    MODELS / "decision_threshold.json",
    MODELS / "model_manifest.json",
    MODELS / "dial_alert_final_predictor.joblib",
    REPORTS / "Franklin_Guillano_DIAL_ALERT_Bias_and_Fairness_Analysis.docx",
    REPORTS / "Franklin_Guillano_DIAL_ALERT_Bias_and_Fairness_Analysis.pdf",
]

LOCAL_VALIDATION_INPUTS = [
    ROOT / "data" / "processed" / "hemobp_session_level.csv.gz",
    ARTIFACTS / "split_assignments.csv.gz",
    ARTIFACTS / "step5_group_metrics.csv",
    ARTIFACTS / "step5_group_metric_intervals.csv",
    ARTIFACTS / "step5_intersectional_metrics.csv",
    ARTIFACTS / "step5_original_model_sex_metrics.csv",
    ARTIFACTS / "step5_patient_weighted_group_metrics.csv",
    ARTIFACTS / "step5_sex_outcome_reweighting_sex_metrics.csv",
    ARTIFACTS / "step5_sex_specific_thresholds_sex_metrics.csv",
    ARTIFACTS / "step5_synthetic_case.json",
    MODELS / "dial_alert_step5_sex_reweighted.joblib",
]

PACKAGE_MEMBERS = REQUIRED
PACKAGE = REPORTS / "Franklin_Guillano_DIAL_ALERT_Step5_Ethical_AI_and_Bias_Audit.zip"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate() -> None:
    missing = [
        str(path.relative_to(ROOT))
        for path in REQUIRED + LOCAL_VALIDATION_INPUTS
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError("Missing Step 5 deliverables: " + ", ".join(missing))

    groups = pd.read_csv(ARTIFACTS / "step5_group_metrics.csv")
    disparities = pd.read_csv(ARTIFACTS / "step5_disparities.csv")
    mitigation = pd.read_csv(ARTIFACTS / "step5_mitigation_comparison.csv")
    required_attributes = {"Recorded sex", "Age group", "Diabetes status"}
    if not required_attributes.issubset(set(groups["attribute"])):
        raise ValueError("Subgroup metric table does not contain all planned audits")
    if not required_attributes.issubset(set(disparities["attribute"])):
        raise ValueError("Disparity table does not contain all planned audits")
    expected_strategies = {
        "Original model",
        "Sex outcome reweighting",
        "Sex specific thresholds",
    }
    if set(mitigation["strategy"]) != expected_strategies:
        raise ValueError("Mitigation comparison is incomplete")

    for path in REQUIRED:
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        if path.suffix == ".png" and path.stat().st_size < 10_000:
            raise ValueError(f"Chart appears incomplete: {path.relative_to(ROOT)}")

    final_model = joblib.load(MODELS / "dial_alert_final_predictor.joblib")
    reweighted_model = joblib.load(MODELS / "dial_alert_step5_sex_reweighted.joblib")
    if not hasattr(final_model, "predict_proba") or not hasattr(reweighted_model, "predict_proba"):
        raise TypeError("A saved model does not expose predict_proba")


def write_manifest() -> None:
    entries = []
    for path in REQUIRED:
        entries.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    MANIFEST.write_text(
        json.dumps(
            {
                "project": "DIAL-ALERT",
                "step": 5,
                "title": "Ethical AI and Bias Auditing",
                "file_count": len(entries),
                "files": entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def build_package() -> None:
    members = PACKAGE_MEMBERS + [MANIFEST]
    with zipfile.ZipFile(PACKAGE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in members:
            archive.write(path, path.relative_to(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="Validate files and models")
    parser.add_argument("--package", action="store_true", help="Create the submission ZIP")
    args = parser.parse_args()

    if not args.verify and not args.package:
        args.verify = True
        args.package = True
    validate()
    write_manifest()
    if args.package:
        build_package()
    print(json.dumps({"verified": True, "manifest": str(MANIFEST), "package": str(PACKAGE)}))


if __name__ == "__main__":
    main()
