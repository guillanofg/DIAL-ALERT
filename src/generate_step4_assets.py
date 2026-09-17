"""Generate publication-ready graphics for the DIAL-ALERT Step 4 report."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibrationDisplay


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
BLUE = "#0B5C8E"
TEAL = "#2A9D8F"
ORANGE = "#E07A35"
RED = "#C84630"
GRAY = "#6B7280"


def save_model_comparison() -> None:
    comparison = pd.read_csv(ARTIFACTS / "model_comparison.csv")
    comparison = comparison.sort_values("cv_average_precision_mean", ascending=True)
    labels = comparison["model"].str.replace("Histogram gradient boosting", "Hist gradient boosting")

    fig, axes = plt.subplots(1, 2, figsize=(14.5, 6.3))
    axes[0].barh(
        labels,
        comparison["cv_average_precision_mean"],
        xerr=comparison["cv_average_precision_sd"],
        color=BLUE,
        alpha=0.92,
        capsize=3,
    )
    axes[0].axvline(
        comparison.loc[comparison.model.eq("Dummy prevalence baseline"), "cv_average_precision_mean"].iloc[0],
        color=RED,
        linestyle="--",
        linewidth=1.8,
        label="Prevalence baseline",
    )
    axes[0].set(
        title="Grouped cross-validation",
        xlabel="Average precision",
        ylabel="",
        xlim=(0, max(0.52, comparison.cv_average_precision_mean.max() + 0.08)),
    )
    axes[0].legend(frameon=False, loc="lower right")

    validation = comparison.sort_values("validation_brier_score", ascending=False)
    validation_labels = validation["model"].str.replace(
        "Histogram gradient boosting", "Hist gradient boosting"
    )
    colors = [TEAL if name == "Random forest" else ORANGE for name in validation.model]
    axes[1].barh(validation_labels, validation["validation_brier_score"], color=colors)
    axes[1].set(
        title="Validation probability error",
        xlabel="Brier score lower is better",
        ylabel="",
        xlim=(0, max(0.17, validation.validation_brier_score.max() * 1.12)),
    )
    fig.suptitle("Model selection balances ranking and calibration", y=1.02, fontsize=18)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "step4_model_comparison.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def save_test_intervals() -> None:
    intervals = pd.read_csv(ARTIFACTS / "test_metric_confidence_intervals.csv")
    display = {
        "roc_auc": "ROC AUC",
        "average_precision": "Average precision",
        "sensitivity": "Sensitivity",
        "specificity": "Specificity",
        "precision": "Precision",
        "f1": "F1 score",
        "recall_at_capacity": "Recall at 20% capacity",
        "precision_at_capacity": "Precision at 20% capacity",
    }
    plot = intervals[intervals.metric.isin(display)].copy()
    plot["label"] = plot.metric.map(display)
    plot = plot.sort_values("estimate")
    lower = plot.estimate - plot.ci_lower_95
    upper = plot.ci_upper_95 - plot.estimate

    fig, ax = plt.subplots(figsize=(9.4, 6.2))
    y = np.arange(len(plot))
    ax.errorbar(
        plot.estimate,
        y,
        xerr=np.vstack([lower, upper]),
        fmt="o",
        markersize=7,
        color=BLUE,
        ecolor=TEAL,
        elinewidth=2.2,
        capsize=4,
    )
    ax.set_yticks(y, plot.label)
    ax.set(
        title="Final test performance with patient-cluster intervals",
        xlabel="Metric value with 95% confidence interval",
        xlim=(0, 1),
    )
    ax.grid(axis="y", visible=False)
    for i, value in enumerate(plot.estimate):
        ax.text(min(value + 0.025, 0.94), i, f"{value:.3f}", va="center", fontsize=10)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "test_performance_intervals.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def save_model_workflow() -> None:
    final = json.loads((ARTIFACTS / "final_test_metrics.json").read_text(encoding="utf-8"))
    threshold = float(final["operating_threshold"])
    nodes = [
        ("Eligible session", "22 index-time predictors"),
        ("Preprocessing", "Median imputation and one-hot encoding"),
        ("Random forest", "250 trees and tuned leaf size"),
        ("Risk probability", "Estimated later BP-defined IDH risk"),
        ("Alert rule", f"Threshold {threshold:.3f} or capacity ranking"),
    ]
    fig, ax = plt.subplots(figsize=(15.2, 3.7))
    ax.set_xlim(0, 15.2)
    ax.set_ylim(0, 3.7)
    ax.axis("off")
    box_width = 2.45
    positions = [0.25, 3.25, 6.25, 9.25, 12.25]
    fills = ["#EAF3F8", "#EAF3F8", "#DFF3EE", "#EAF3F8", "#FBE9DD"]
    for i, ((title, subtitle), x, fill) in enumerate(zip(nodes, positions, fills)):
        box = FancyBboxPatch(
            (x, 0.75),
            box_width,
            2.05,
            boxstyle="round,pad=0.04,rounding_size=0.08",
            linewidth=1.4,
            edgecolor=BLUE if i != 4 else ORANGE,
            facecolor=fill,
        )
        ax.add_patch(box)
        ax.text(x + box_width / 2, 2.12, title, ha="center", va="center", fontsize=12, weight="bold")
        ax.text(x + box_width / 2, 1.42, subtitle, ha="center", va="center", fontsize=9.5, wrap=True)
        if i < len(nodes) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + box_width + 0.08, 1.78),
                    (positions[i + 1] - 0.08, 1.78),
                    arrowstyle="-|>",
                    mutation_scale=15,
                    linewidth=1.5,
                    color=GRAY,
                )
            )
    ax.set_title("DIAL ALERT inference workflow", fontsize=17, pad=8)
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "step4_model_workflow.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def save_compact_calibration_plot() -> None:
    config = json.loads((ROOT / "configs/model_config.json").read_text(encoding="utf-8"))
    features = list(config["numeric_features"]) + list(config["categorical_features"])
    data = pd.read_csv(ROOT / "data/processed/hemobp_session_level.csv.gz")
    assignments = pd.read_csv(ARTIFACTS / "split_assignments.csv.gz")
    if len(data) != len(assignments):
        raise ValueError("Split assignment length does not match the processed dataset")
    if not data["pid"].astype(str).equals(assignments["pid"].astype(str)):
        raise ValueError("Split assignments are not aligned with the processed dataset")
    test_mask = assignments["split"].eq("test").to_numpy()
    test = data.loc[test_mask].copy()
    test["prior_session_count"] = np.log1p(test["prior_session_count"].clip(lower=0))
    predictor = joblib.load(ROOT / "models/dial_alert_final_predictor.joblib")
    probability = predictor.predict_proba(test[features])[:, 1]

    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    CalibrationDisplay.from_predictions(
        test[config["primary_outcome"]].astype(int).to_numpy(),
        probability,
        n_bins=10,
        name="Random forest",
        ax=ax,
    )
    ax.set(
        title="Test set calibration",
        xlabel="Mean predicted risk",
        ylabel="Observed event rate",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "step4_calibration_plot.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    save_model_comparison()
    save_test_intervals()
    save_model_workflow()
    save_compact_calibration_plot()
    print("Generated Step 4 report graphics")


if __name__ == "__main__":
    main()
