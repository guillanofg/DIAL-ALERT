"""Finalize integrity metadata and the compact Step 4 submission bundle."""

from __future__ import annotations

import hashlib
import json
import platform
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
MODELS = ROOT / "models"
ARTIFACTS = ROOT / "artifacts"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_files() -> list[Path]:
    return [
        MODELS / "candidate_logistic_regression.joblib",
        MODELS / "candidate_l1_feature_selection.joblib",
        MODELS / "candidate_decision_tree.joblib",
        MODELS / "candidate_pca_logistic_regression.joblib",
        MODELS / "candidate_histogram_gradient_boosting.joblib",
        # The selected random forest is stored once under its deployment name.
        MODELS / "dial_alert_final_predictor.joblib",
        MODELS / "decision_threshold.json",
    ]


def write_model_manifest() -> Path:
    previous = json.loads((MODELS / "model_manifest.json").read_text(encoding="utf-8"))
    config = ROOT / "configs/model_config.json"
    data = ROOT / "data/processed/hemobp_session_level.csv.gz"
    final = json.loads((ARTIFACTS / "final_test_metrics.json").read_text(encoding="utf-8"))
    files = model_files()
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Step 4 model files: {missing}")
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "package_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "data_file": str(data.relative_to(ROOT)),
        "data_sha256": sha256_file(data),
        "config_file": str(config.relative_to(ROOT)),
        "config_sha256": sha256_file(config),
        "random_state": previous["random_state"],
        "n_jobs": previous["n_jobs"],
        "grouped_cv_folds": previous["grouped_cv_folds"],
        "split_seed": previous["split_seed"],
        "selected_model": final["selected_model"],
        "selected_calibration": final["calibration_method"],
        "model_files": [
            {
                "file": str(path.relative_to(ROOT)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
    }
    output = MODELS / "model_manifest.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output


def build_bundle(manifest_path: Path) -> Path:
    output = REPORTS / "Franklin_Guillano_DIAL_ALERT_Step4_Reproducible_Code_and_Models.zip"
    files = [
        ROOT / "README_Step4.md",
        ROOT / "requirements-step4.txt",
        ROOT / "src/build_session_dataset.py",
        ROOT / "src/train_evaluate.py",
        ROOT / "src/generate_step4_assets.py",
        ROOT / "src/predict.py",
        ROOT / "configs/model_config.json",
        manifest_path,
        *model_files(),
        ARTIFACTS / "split_summary.csv",
        ARTIFACTS / "split_metadata.json",
        ARTIFACTS / "model_comparison.csv",
        ARTIFACTS / "cv_search_top_results.csv",
        ARTIFACTS / "calibration_method_comparison.csv",
        ARTIFACTS / "final_test_metrics.json",
        ARTIFACTS / "test_metric_confidence_intervals.csv",
        ARTIFACTS / "capacity_metrics.csv",
        ARTIFACTS / "permutation_importance.csv",
    ]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing bundle files: {missing}")

    content_manifest = []
    for path in files:
        content_manifest.append(
            {
                "file": str(path.relative_to(ROOT)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    generated_manifest = ARTIFACTS / "step4_submission_manifest.json"
    generated_manifest.write_text(
        json.dumps({"files": content_manifest}, indent=2), encoding="utf-8"
    )
    files.append(generated_manifest)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, arcname=str(path.relative_to(ROOT)))
    return output


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    manifest = write_model_manifest()
    bundle = build_bundle(manifest)
    print(manifest)
    print(bundle)


if __name__ == "__main__":
    main()
