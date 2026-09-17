"""Run the DIAL-ALERT Step 5 explainability, fairness, and mitigation audit.

The script preserves the locked Step 4 patient split and operating threshold.
All subgroup results are evaluated on the untouched patient-disjoint test set.
Mitigation thresholds are estimated from validation patients only.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.base import clone
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    roc_auc_score,
    roc_curve,
)


BLUE = "#146C94"
TEAL = "#2A9D8F"
ORANGE = "#E07A5F"
GOLD = "#E9C46A"
RED = "#C84630"
GRAY = "#6B7280"
PALE_BLUE = "#DCEAF4"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else np.nan


def expected_calibration_error(y: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    frame = pd.DataFrame({"y": y, "p": probability})
    try:
        frame["bin"] = pd.qcut(frame.p, q=bins, duplicates="drop")
    except ValueError:
        return np.nan
    grouped = frame.groupby("bin", observed=True)
    total = len(frame)
    return float(
        sum(len(group) / total * abs(group.y.mean() - group.p.mean()) for _, group in grouped)
    )


def metric_row(
    y: np.ndarray,
    probability: np.ndarray,
    pred: np.ndarray,
    weights: np.ndarray | None = None,
) -> dict:
    y = np.asarray(y, dtype=int)
    probability = np.asarray(probability, dtype=float)
    pred = np.asarray(pred, dtype=int)
    if weights is None:
        weights = np.ones(len(y), dtype=float)
    weights = np.asarray(weights, dtype=float)

    negative = y == 0
    positive = y == 1
    predicted_positive = pred == 1
    tp = weights[positive & predicted_positive].sum()
    fn = weights[positive & ~predicted_positive].sum()
    fp = weights[negative & predicted_positive].sum()
    tn = weights[negative & ~predicted_positive].sum()

    prevalence = np.average(y, weights=weights)
    selection_rate = np.average(pred, weights=weights)
    sensitivity = safe_divide(tp, tp + fn)
    false_positive_rate = safe_divide(fp, fp + tn)
    specificity = safe_divide(tn, tn + fp)
    precision = safe_divide(tp, tp + fp)
    result = {
        "prevalence": float(prevalence),
        "selection_rate": float(selection_rate),
        "sensitivity": sensitivity,
        "false_positive_rate": false_positive_rate,
        "specificity": specificity,
        "precision": precision,
        "f1": safe_divide(2 * precision * sensitivity, precision + sensitivity),
        "brier_score": float(np.average((probability - y) ** 2, weights=weights)),
    }
    if weights is not None and np.allclose(weights, 1):
        result["average_precision"] = (
            float(average_precision_score(y, probability)) if len(np.unique(y)) > 1 else np.nan
        )
        result["roc_auc"] = float(roc_auc_score(y, probability)) if len(np.unique(y)) > 1 else np.nan
        result["calibration_error"] = expected_calibration_error(y, probability)
    else:
        result["average_precision"] = np.nan
        result["roc_auc"] = np.nan
        result["calibration_error"] = np.nan
    return result


def group_metric_table(
    frame: pd.DataFrame,
    attribute: str,
    group_column: str,
    probability_column: str = "probability",
    prediction_column: str = "prediction",
    weight_column: str | None = None,
) -> pd.DataFrame:
    rows: list[dict] = []
    groups = frame[group_column].astype("string").fillna("Missing")
    for level in sorted(groups.unique()):
        mask = (groups == level).to_numpy()
        subset = frame.loc[mask]
        weights = subset[weight_column].to_numpy() if weight_column else None
        metrics = metric_row(
            subset["outcome"].to_numpy(),
            subset[probability_column].to_numpy(),
            subset[prediction_column].to_numpy(),
            weights,
        )
        rows.append(
            {
                "attribute": attribute,
                "group": str(level),
                "sessions": int(len(subset)),
                "patients": int(subset.pid.nunique()),
                "events": int(subset.outcome.sum()),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def disparity_row(table: pd.DataFrame, attribute: str) -> dict:
    selection_max = table.selection_rate.max()
    return {
        "attribute": attribute,
        "demographic_parity_difference": float(table.selection_rate.max() - table.selection_rate.min()),
        "disparate_impact_ratio": float(table.selection_rate.min() / selection_max)
        if selection_max > 0
        else np.nan,
        "equal_opportunity_difference": float(table.sensitivity.max() - table.sensitivity.min()),
        "false_positive_rate_difference": float(
            table.false_positive_rate.max() - table.false_positive_rate.min()
        ),
        "equalized_odds_difference": float(
            max(
                table.sensitivity.max() - table.sensitivity.min(),
                table.false_positive_rate.max() - table.false_positive_rate.min(),
            )
        ),
        "predictive_parity_difference": float(table.precision.max() - table.precision.min()),
        "brier_score_difference": float(table.brier_score.max() - table.brier_score.min()),
    }


def patient_bootstrap(
    frame: pd.DataFrame,
    audits: list[tuple[str, str]],
    iterations: int,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(random_state)
    patients = frame.pid.unique()
    index_by_patient = {
        pid: group.index.to_numpy() for pid, group in frame.groupby("pid", sort=False)
    }
    group_records: list[dict] = []
    disparity_records: list[dict] = []
    for iteration in range(iterations):
        sampled = rng.choice(patients, size=len(patients), replace=True)
        indices = np.concatenate([index_by_patient[pid] for pid in sampled])
        boot = frame.loc[indices]
        for attribute, column in audits:
            table = group_metric_table(boot, attribute, column)
            for row in table.to_dict("records"):
                group_records.append(
                    {
                        "iteration": iteration,
                        "attribute": attribute,
                        "group": row["group"],
                        "selection_rate": row["selection_rate"],
                        "sensitivity": row["sensitivity"],
                        "false_positive_rate": row["false_positive_rate"],
                        "precision": row["precision"],
                        "brier_score": row["brier_score"],
                    }
                )
            disparity_records.append({"iteration": iteration, **disparity_row(table, attribute)})

    group_boot = pd.DataFrame(group_records)
    disparity_boot = pd.DataFrame(disparity_records)
    group_intervals: list[dict] = []
    for (attribute, group), subset in group_boot.groupby(["attribute", "group"]):
        for metric in [
            "selection_rate",
            "sensitivity",
            "false_positive_rate",
            "precision",
            "brier_score",
        ]:
            values = subset[metric].dropna()
            group_intervals.append(
                {
                    "attribute": attribute,
                    "group": group,
                    "metric": metric,
                    "lower_95": float(values.quantile(0.025)),
                    "upper_95": float(values.quantile(0.975)),
                }
            )

    disparity_intervals: list[dict] = []
    for attribute, subset in disparity_boot.groupby("attribute"):
        for metric in [
            "demographic_parity_difference",
            "disparate_impact_ratio",
            "equal_opportunity_difference",
            "false_positive_rate_difference",
            "equalized_odds_difference",
            "predictive_parity_difference",
            "brier_score_difference",
        ]:
            values = subset[metric].dropna()
            disparity_intervals.append(
                {
                    "attribute": attribute,
                    "metric": metric,
                    "lower_95": float(values.quantile(0.025)),
                    "upper_95": float(values.quantile(0.975)),
                }
            )
    return pd.DataFrame(group_intervals), pd.DataFrame(disparity_intervals)


def choose_threshold_for_sensitivity(y: np.ndarray, probability: np.ndarray, target: float) -> float:
    false_positive_rate, sensitivity, thresholds = roc_curve(y, probability)
    distance = np.abs(sensitivity - target)
    best = np.flatnonzero(distance == distance.min())
    if len(best) > 1:
        best = best[np.argmin(false_positive_rate[best]) : np.argmin(false_positive_rate[best]) + 1]
    threshold = thresholds[int(best[0])]
    if not np.isfinite(threshold):
        threshold = 1.0
    return float(np.clip(threshold, 0.0, 1.0))


def overall_metrics(y: np.ndarray, probability: np.ndarray, pred: np.ndarray) -> dict:
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "average_precision": float(average_precision_score(y, probability)),
        "roc_auc": float(roc_auc_score(y, probability)),
        "brier_score": float(brier_score_loss(y, probability)),
        "selection_rate": float(pred.mean()),
        "sensitivity": safe_divide(tp, tp + fn),
        "specificity": safe_divide(tn, tn + fp),
        "precision": safe_divide(tp, tp + fp),
        "f1": float(f1_score(y, pred)),
    }


def approximate_interventional_shap(
    model,
    background: pd.DataFrame,
    explain: pd.DataFrame,
    outcomes: np.ndarray | None,
    permutations: int,
    random_state: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_state)
    features = list(explain.columns)
    records: list[dict] = []
    background = background.reset_index(drop=True)

    for case_number, (_, case) in enumerate(explain.reset_index(drop=True).iterrows(), start=1):
        rows: list[list] = []
        orders: list[np.ndarray] = []
        baseline_positions: list[int] = []
        for _ in range(permutations):
            donor = background.iloc[int(rng.integers(0, len(background)))].copy()
            order = rng.permutation(len(features))
            orders.append(order)
            baseline_positions.append(len(rows))
            rows.append(donor.tolist())
            current = donor.copy()
            for feature_index in order:
                current.iloc[feature_index] = case.iloc[feature_index]
                rows.append(current.tolist())

        synthetic = pd.DataFrame(rows, columns=features)
        predictions = model.predict_proba(synthetic)[:, 1]
        contribution = np.zeros(len(features), dtype=float)
        baseline_predictions: list[float] = []
        cursor = 0
        for order in orders:
            path = predictions[cursor : cursor + len(features) + 1]
            baseline_predictions.append(float(path[0]))
            for step, feature_index in enumerate(order):
                contribution[feature_index] += path[step + 1] - path[step]
            cursor += len(features) + 1
        contribution /= permutations
        prediction = float(model.predict_proba(case.to_frame().T)[:, 1][0])
        baseline = float(np.mean(baseline_predictions))
        case_id = f"case_{case_number:03d}"
        for feature, value, shap_value in zip(features, case.tolist(), contribution):
            records.append(
                {
                    "case_id": case_id,
                    "outcome": (
                        int(outcomes[case_number - 1]) if outcomes is not None else None
                    ),
                    "prediction": prediction,
                    "baseline_prediction": baseline,
                    "feature": feature,
                    "feature_value": value,
                    "shap_value": float(shap_value),
                    "local_accuracy_error": float(prediction - (baseline + contribution.sum())),
                }
            )
    return pd.DataFrame(records)


def synthetic_high_risk_case(features: list[str]) -> tuple[pd.Series, dict]:
    """Return a clinically plausible scenario that is not copied from a patient row."""
    clinical_input = {
        "age_years": 60.0,
        "dialysis_vintage_years": 5.25,
        "weightstart": 70.3,
        "dryweight": 64.8,
        "temperature": 36.4,
        "fluid_excess_kg": 5.5,
        "fluid_excess_pct": 8.487654,
        "baseline_sbp": 118.0,
        "baseline_dbp": 66.0,
        "baseline_map": 83.333333,
        "baseline_pulse_pressure": 52.0,
        "initial_uf_l_h": 1.2,
        "initial_uf_ml_kg_h": 17.069701,
        "initial_blood_flow_ml_min": 255.0,
        "initial_dialysate_temp_c": 36.2,
        "initial_conductivity_ms_cm": 14.1,
        "prior_session_idh": 1.0,
        "prior_nadir_sbp": 72.0,
        "prior_idh_rate": 0.62,
        "prior_session_count": 24,
        "gender": "F",
        "DM": 1,
    }
    model_input = dict(clinical_input)
    model_input["prior_session_count"] = float(
        np.log1p(clinical_input["prior_session_count"])
    )
    missing = sorted(set(features) - set(model_input))
    if missing:
        raise ValueError(f"Synthetic scenario is missing model features: {missing}")
    case = pd.Series({feature: model_input[feature] for feature in features})
    specification = {
        "scenario_type": "synthetic",
        "not_a_patient_record": True,
        "description": (
            "Clinically plausible teaching scenario constructed manually for local "
            "explainability. It is not copied from HEMOBP or any patient record."
        ),
        "clinical_input": clinical_input,
        "model_input_note": (
            "prior_session_count is transformed with log1p before scoring; all other "
            "features use the displayed clinical scale."
        ),
    }
    return case, specification


def lime_style_explanation(
    model,
    case: pd.Series,
    background: pd.DataFrame,
    samples: int,
    random_state: int,
) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(random_state)
    features = list(case.index)
    p = len(features)
    masks = rng.integers(0, 2, size=(samples, p), endpoint=False)
    masks[0, :] = 1
    masks[1, :] = 0
    donors = background.iloc[rng.integers(0, len(background), size=samples)].reset_index(drop=True)
    perturbed = donors.copy()
    for index, feature in enumerate(features):
        keep = masks[:, index].astype(bool)
        perturbed.loc[keep, feature] = case[feature]
    probability = model.predict_proba(perturbed)[:, 1]
    distance = np.sqrt(((1 - masks) ** 2).sum(axis=1) / p)
    kernel_width = 0.75
    weights = np.exp(-(distance**2) / (kernel_width**2))
    surrogate = Ridge(alpha=0.001)
    surrogate.fit(masks, probability, sample_weight=weights)
    score = float(surrogate.score(masks, probability, sample_weight=weights))
    surrogate_prediction = float(surrogate.predict(np.ones((1, p)))[0])
    model_prediction = float(model.predict_proba(case.to_frame().T)[:, 1][0])
    table = pd.DataFrame(
        {
            "feature": features,
            "feature_value": case.tolist(),
            "lime_coefficient": surrogate.coef_,
            "absolute_coefficient": np.abs(surrogate.coef_),
        }
    ).sort_values("absolute_coefficient", ascending=False)
    metadata = {
        "weighted_r2": score,
        "model_prediction": model_prediction,
        "surrogate_prediction": surrogate_prediction,
        "absolute_prediction_error": abs(model_prediction - surrogate_prediction),
        "samples": samples,
        "kernel_width": kernel_width,
    }
    return table, metadata


def human_feature(feature: str) -> str:
    labels = {
        "prior_nadir_sbp": "Prior-session nadir SBP",
        "prior_idh_rate": "Prior IDH rate",
        "prior_session_idh": "Prior-session IDH",
        "baseline_sbp": "Baseline SBP",
        "baseline_map": "Baseline MAP",
        "baseline_dbp": "Baseline DBP",
        "baseline_pulse_pressure": "Baseline pulse pressure",
        "fluid_excess_pct": "Fluid excess percent",
        "fluid_excess_kg": "Fluid excess kg",
        "initial_uf_ml_kg_h": "Initial UF rate",
        "prior_session_count": "Prior-session count log",
        "dialysis_vintage_years": "Dialysis vintage",
        "age_years": "Age",
        "gender": "Recorded sex",
        "DM": "Diabetes",
        "weightstart": "Starting weight",
        "dryweight": "Dry weight",
        "temperature": "Temperature",
        "initial_uf_l_h": "Initial UF L per hour",
        "initial_blood_flow_ml_min": "Initial blood flow",
        "initial_dialysate_temp_c": "Dialysate temperature",
        "initial_conductivity_ms_cm": "Conductivity",
    }
    return labels.get(feature, feature.replace("_", " ").title())


def save_fairness_overview(group_metrics: pd.DataFrame, output: Path) -> None:
    chart = group_metrics[group_metrics.attribute.isin(["Recorded sex", "Age group", "Diabetes status"])].copy()
    chart["label"] = chart.attribute + ": " + chart.group
    colors = {
        "Recorded sex": BLUE,
        "Age group": TEAL,
        "Diabetes status": ORANGE,
    }
    fig, axes = plt.subplots(1, 3, figsize=(14, 7.2), sharey=True)
    for ax, metric, title in zip(
        axes,
        ["selection_rate", "sensitivity", "false_positive_rate"],
        ["Alert selection rate", "Sensitivity", "False-positive rate"],
    ):
        ax.barh(
            chart.label,
            chart[metric],
            color=[colors[value] for value in chart.attribute],
            edgecolor="white",
        )
        ax.set_xlim(0, 0.8 if metric != "false_positive_rate" else 0.25)
        ax.set_title(title, fontsize=12, weight="bold")
        ax.set_xlabel("Rate")
        ax.grid(axis="x", alpha=0.25)
        for index, value in enumerate(chart[metric]):
            ax.text(value + 0.008, index, f"{value:.1%}", va="center", fontsize=8)
    fig.suptitle("Subgroup performance on the patient-disjoint test set", fontsize=16, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def save_disparity_summary(disparities: pd.DataFrame, output: Path) -> None:
    chart = disparities[disparities.attribute.isin(["Recorded sex", "Age group", "Diabetes status"])].copy()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    axes[0].barh(chart.attribute, chart.disparate_impact_ratio, color=[BLUE, TEAL, ORANGE])
    axes[0].axvline(0.8, color=RED, linestyle="--", linewidth=1.6, label="0.80 screening rule")
    axes[0].set(xlim=(0, 1.05), xlabel="Minimum to maximum selection-rate ratio", title="Disparate impact ratio")
    axes[0].legend(frameon=False, loc="lower right")
    for index, value in enumerate(chart.disparate_impact_ratio):
        axes[0].text(value + 0.015, index, f"{value:.2f}", va="center")
    axes[1].barh(chart.attribute, chart.equalized_odds_difference * 100, color=[BLUE, TEAL, ORANGE])
    axes[1].set(xlabel="Maximum TPR or FPR gap percentage points", title="Equalized odds difference")
    for index, value in enumerate(chart.equalized_odds_difference * 100):
        axes[1].text(value + 0.25, index, f"{value:.1f}", va="center")
    for ax in axes:
        ax.grid(axis="x", alpha=0.25)
    fig.suptitle("Fairness metrics diagnose different kinds of disparity", fontsize=15, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def save_mitigation_tradeoff(comparison: pd.DataFrame, output: Path) -> None:
    labels = comparison.strategy.tolist()
    colors = [BLUE, TEAL, ORANGE]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.7))
    panels = [
        ("average_precision", "Average precision", (0.35, 0.42)),
        ("sex_disparate_impact_ratio", "Sex disparate impact ratio", (0.5, 1.02)),
        ("sex_equalized_odds_difference", "Sex equalized odds gap", (0.0, 0.16)),
    ]
    for ax, (metric, title, limits) in zip(axes, panels):
        values = comparison[metric]
        ax.bar(range(len(labels)), values, color=colors)
        ax.set_xticks(range(len(labels)), labels, rotation=20, ha="right")
        ax.set_ylim(*limits)
        ax.set_title(title, fontsize=11, weight="bold")
        ax.grid(axis="y", alpha=0.25)
        if metric == "sex_disparate_impact_ratio":
            ax.axhline(0.8, color=RED, linestyle="--", linewidth=1.5)
        for index, value in enumerate(values):
            ax.text(index, value + (limits[1] - limits[0]) * 0.025, f"{value:.3f}", ha="center", fontsize=9)
    fig.suptitle("Mitigation changes fairness and performance together", fontsize=15, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def save_shap_global_summary(values: pd.DataFrame, output: Path) -> pd.DataFrame:
    global_table = (
        values.groupby("feature")
        .agg(mean_absolute_shap=("shap_value", lambda series: float(np.abs(series).mean())), mean_shap=("shap_value", "mean"))
        .sort_values("mean_absolute_shap", ascending=False)
        .reset_index()
    )
    chart = global_table.head(10).sort_values("mean_absolute_shap")
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.barh(
        [human_feature(feature) for feature in chart.feature],
        chart.mean_absolute_shap,
        color=BLUE,
    )
    ax.set_xlabel("Mean absolute approximate SHAP contribution")
    ax.set_title("Aggregate global model explanation", fontsize=15, weight="bold")
    ax.grid(axis="x", alpha=0.2)
    fig.text(
        0.98,
        0.02,
        "Only aggregate importance is published; no session-level values are shown.",
        ha="right",
        fontsize=9,
        color=GRAY,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return global_table


def save_local_explanation(table: pd.DataFrame, output: Path, title: str, value_column: str) -> None:
    chart = table.head(10).sort_values(value_column)
    values = chart[value_column]
    colors = [RED if value > 0 else BLUE for value in values]
    fig, ax = plt.subplots(figsize=(8.4, 5.4))
    ax.barh([human_feature(value) for value in chart.feature], values, color=colors)
    ax.axvline(0, color="#333333", linewidth=1)
    ax.set_xlabel("Contribution to predicted probability")
    ax.set_title(title, fontsize=14, weight="bold")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def synthetic_reference_profiles(reference: pd.DataFrame) -> pd.DataFrame:
    """Build synthetic anchors from aggregate statistics, never observed rows."""
    base: dict[str, object] = {}
    for feature in reference.columns:
        if pd.api.types.is_numeric_dtype(reference[feature]):
            base[feature] = float(reference[feature].median())
        else:
            mode = reference[feature].mode(dropna=True)
            base[feature] = mode.iloc[0] if not mode.empty else ""
    settings = [
        (120.0, 0.05, 2.0),
        (105.0, 0.18, 3.5),
        (92.0, 0.35, 5.0),
        (78.0, 0.55, 7.0),
        (68.0, 0.72, 9.0),
    ]
    profiles = []
    for nadir, rate, fluid in settings:
        profile = dict(base)
        profile.update(
            {
                "prior_nadir_sbp": nadir,
                "prior_idh_rate": rate,
                "fluid_excess_pct": fluid,
            }
        )
        profiles.append(profile)
    return pd.DataFrame(profiles, columns=reference.columns)


def save_pdp_ice(model, reference: pd.DataFrame, output: Path, random_state: int) -> None:
    features = ["prior_nadir_sbp", "prior_idh_rate", "fluid_excess_pct"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), squeeze=False)
    profiles = synthetic_reference_profiles(reference)
    for ax, feature in zip(axes.ravel(), features):
        lower, upper = reference[feature].quantile([0.05, 0.95])
        grid = np.linspace(float(lower), float(upper), 40)
        curves = []
        for index, (_, profile) in enumerate(profiles.iterrows(), start=1):
            scenario = pd.DataFrame([profile.to_dict()] * len(grid), columns=reference.columns)
            scenario[feature] = grid
            probability = model.predict_proba(scenario)[:, 1]
            curves.append(probability)
            ax.plot(
                grid,
                probability,
                color=BLUE,
                alpha=0.35,
                linewidth=1.1,
                label="Synthetic reference profile" if index == 1 else None,
            )
        ax.plot(
            grid,
            np.mean(curves, axis=0),
            color=RED,
            linewidth=2.8,
            label="Synthetic-profile average",
        )
        ax.set_xlabel(human_feature(feature))
        ax.set_ylabel("Predicted event probability")
        ax.grid(alpha=0.2)
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.suptitle(
        "Synthetic-profile dependence and conditional effects",
        fontsize=15,
        weight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)


def write_attribute_availability(frame: pd.DataFrame, output: Path) -> None:
    rows = [
        {
            "attribute": "Recorded sex",
            "source": "gender field with F and M categories",
            "availability": "Available",
            "missing_percent": float(frame.gender.isna().mean() * 100),
            "audit_use": "Primary protected-attribute audit",
            "limitation": "Binary recorded field does not represent gender identity or variation beyond F and M",
        },
        {
            "attribute": "Age",
            "source": "Derived age_years",
            "availability": "Available",
            "missing_percent": float(frame.age_years.isna().mean() * 100),
            "audit_use": "Four prespecified age bands",
            "limitation": "Age groups simplify a continuous and time-varying characteristic",
        },
        {
            "attribute": "Race or ethnicity",
            "source": "Not collected in the public dataset",
            "availability": "Unavailable",
            "missing_percent": 100.0,
            "audit_use": "Not auditable",
            "limitation": "Fairness across racial and ethnic groups cannot be assessed",
        },
        {
            "attribute": "Socioeconomic status",
            "source": "No income, education, insurance, occupation, or area-deprivation field",
            "availability": "Unavailable",
            "missing_percent": 100.0,
            "audit_use": "Not auditable",
            "limitation": "Diabetes and dialysis vintage are not treated as socioeconomic proxies",
        },
        {
            "attribute": "Diabetes status",
            "source": "DM field",
            "availability": "Available",
            "missing_percent": float(frame.DM.isna().mean() * 100),
            "audit_use": "Clinical subgroup audit",
            "limitation": "Clinical risk factor, not a substitute for socioeconomic status",
        },
    ]
    pd.DataFrame(rows).to_csv(output, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/processed/hemobp_session_level.csv.gz"))
    parser.add_argument("--splits", type=Path, default=Path("artifacts/split_assignments.csv.gz"))
    parser.add_argument("--config", type=Path, default=Path("configs/model_config.json"))
    parser.add_argument("--model", type=Path, default=Path("models/dial_alert_final_predictor.joblib"))
    parser.add_argument("--threshold", type=Path, default=Path("models/decision_threshold.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--models", type=Path, default=Path("models"))
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    args.models.mkdir(parents=True, exist_ok=True)

    config = load_json(args.config)
    threshold_spec = load_json(args.threshold)
    features = list(config["numeric_features"]) + list(config["categorical_features"])
    threshold = float(threshold_spec["threshold"])
    random_state = int(config["random_state"])
    bootstrap_iterations = int(config.get("bootstrap_iterations", 500))

    frame = pd.read_csv(args.data, parse_dates=["session_date", "index_datetime"])
    splits = pd.read_csv(args.splits, parse_dates=["session_date"])
    frame = frame.merge(splits, on=["pid", "session_date"], how="left", validate="one_to_one")
    if frame.split.isna().any():
        raise ValueError("Every session must have a locked Step 4 split assignment")
    frame["prior_session_count"] = np.log1p(frame.prior_session_count.clip(lower=0))
    frame["outcome"] = frame[config["primary_outcome"]].astype(int)
    frame["age_group"] = pd.cut(
        frame.age_years,
        [-np.inf, 54, 64, 74, np.inf],
        labels=["Under 55", "55 to 64", "65 to 74", "75 and older"],
    ).astype("string")
    frame["sex_group"] = frame.gender.astype("string")
    frame["diabetes_group"] = frame.DM.map({0: "No diabetes", 1: "Diabetes"}).astype("string")
    frame["sex_age_group"] = frame.sex_group + " and " + frame.age_group
    frame["patient_equal_weight"] = 1.0 / frame.groupby("pid").pid.transform("size")

    train = frame[frame.split == "training"].copy()
    validation = frame[frame.split == "validation"].copy()
    test = frame[frame.split == "test"].copy()
    overlap = {
        "training_validation": len(set(train.pid) & set(validation.pid)),
        "training_test": len(set(train.pid) & set(test.pid)),
        "validation_test": len(set(validation.pid) & set(test.pid)),
    }
    if any(overlap.values()):
        raise ValueError(f"Patient split leakage detected: {overlap}")

    model = joblib.load(args.model)
    for subset in [train, validation, test]:
        subset["probability"] = model.predict_proba(subset[features])[:, 1]
        subset["prediction"] = (subset.probability >= threshold).astype(int)

    audits = [
        ("Recorded sex", "sex_group"),
        ("Age group", "age_group"),
        ("Diabetes status", "diabetes_group"),
    ]
    point_tables = [group_metric_table(test, attribute, column) for attribute, column in audits]
    group_metrics = pd.concat(point_tables, ignore_index=True)
    group_metrics.to_csv(args.artifacts / "step5_group_metrics.csv", index=False)
    disparities = pd.DataFrame([disparity_row(table, attribute) for table, (attribute, _) in zip(point_tables, audits)])
    disparities.to_csv(args.artifacts / "step5_disparities.csv", index=False)

    patient_weighted_tables = [
        group_metric_table(test, attribute, column, weight_column="patient_equal_weight")
        for attribute, column in audits
    ]
    patient_weighted = pd.concat(patient_weighted_tables, ignore_index=True)
    patient_weighted.to_csv(args.artifacts / "step5_patient_weighted_group_metrics.csv", index=False)
    patient_weighted_disparities = pd.DataFrame(
        [disparity_row(table, attribute) for table, (attribute, _) in zip(patient_weighted_tables, audits)]
    )
    patient_weighted_disparities.to_csv(
        args.artifacts / "step5_patient_weighted_disparities.csv", index=False
    )

    intersection = group_metric_table(test, "Recorded sex and age", "sex_age_group")
    intersection.to_csv(args.artifacts / "step5_intersectional_metrics.csv", index=False)

    group_intervals, disparity_intervals = patient_bootstrap(
        test.reset_index(drop=True), audits, bootstrap_iterations, random_state + 50
    )
    group_intervals.to_csv(args.artifacts / "step5_group_metric_intervals.csv", index=False)
    disparity_intervals.to_csv(args.artifacts / "step5_disparity_intervals.csv", index=False)

    write_attribute_availability(frame, args.artifacts / "step5_attribute_availability.csv")

    # A limited counterfactual test swaps the recorded sex field while holding all
    # other predictors fixed. It diagnoses direct model dependence, not a causal effect.
    swapped = test[features].copy()
    swapped["gender"] = swapped.gender.map({"F": "M", "M": "F"}).fillna(swapped.gender)
    swapped_probability = model.predict_proba(swapped)[:, 1]
    counterfactual = {
        "mean_signed_probability_change": float((swapped_probability - test.probability).mean()),
        "mean_absolute_probability_change": float(np.abs(swapped_probability - test.probability).mean()),
        "median_absolute_probability_change": float(np.median(np.abs(swapped_probability - test.probability))),
        "maximum_absolute_probability_change": float(np.abs(swapped_probability - test.probability).max()),
        "alert_class_changed_percent": float(
            np.mean((swapped_probability >= threshold).astype(int) != test.prediction.to_numpy()) * 100
        ),
        "interpretation": "Associational diagnostic only; holding correlated physiology fixed is not a causal intervention on sex.",
    }
    (args.artifacts / "step5_counterfactual_sex_audit.json").write_text(
        json.dumps(counterfactual, indent=2), encoding="utf-8"
    )

    # Mitigation 1: training-sample reweighting across recorded-sex and outcome cells.
    sensitive = train.gender.astype(str)
    y_train = train.outcome.to_numpy()
    joint = pd.crosstab(sensitive, y_train, normalize=True)
    p_sensitive = sensitive.value_counts(normalize=True)
    p_outcome = pd.Series(y_train).value_counts(normalize=True)
    sample_weight = np.array(
        [
            p_sensitive[level] * p_outcome[int(outcome)] / joint.loc[level, int(outcome)]
            for level, outcome in zip(sensitive, y_train)
        ]
    )
    reweighted_model = clone(model)
    reweighted_model.fit(train[features], y_train, model__sample_weight=sample_weight)
    joblib.dump(reweighted_model, args.models / "dial_alert_step5_sex_reweighted.joblib")
    test["reweighted_probability"] = reweighted_model.predict_proba(test[features])[:, 1]
    test["reweighted_prediction"] = (test.reweighted_probability >= threshold).astype(int)

    # Mitigation 2: thresholds are tuned on validation patients to equalize
    # sensitivity around the global validation operating point, then locked.
    validation_target = metric_row(
        validation.outcome.to_numpy(),
        validation.probability.to_numpy(),
        validation.prediction.to_numpy(),
    )["sensitivity"]
    sex_thresholds = {}
    for level in sorted(validation.sex_group.dropna().unique()):
        mask = validation.sex_group == level
        sex_thresholds[str(level)] = choose_threshold_for_sensitivity(
            validation.loc[mask, "outcome"].to_numpy(),
            validation.loc[mask, "probability"].to_numpy(),
            validation_target,
        )
    test["sex_threshold_prediction"] = np.array(
        [
            int(probability >= sex_thresholds[str(level)])
            for probability, level in zip(test.probability, test.sex_group)
        ]
    )
    threshold_record = {
        "method": "Recorded-sex-specific thresholds tuned on validation patients for equal sensitivity",
        "validation_target_sensitivity": validation_target,
        "thresholds": sex_thresholds,
        "warning": "Uses a protected attribute at inference and is an exploratory governance option, not a deployment recommendation.",
    }
    (args.artifacts / "step5_sex_specific_thresholds.json").write_text(
        json.dumps(threshold_record, indent=2), encoding="utf-8"
    )

    mitigation_rows: list[dict] = []
    strategies = [
        ("Original model", "probability", "prediction"),
        ("Sex outcome reweighting", "reweighted_probability", "reweighted_prediction"),
        ("Sex specific thresholds", "probability", "sex_threshold_prediction"),
    ]
    for strategy, probability_column, prediction_column in strategies:
        overall = overall_metrics(
            test.outcome.to_numpy(),
            test[probability_column].to_numpy(),
            test[prediction_column].to_numpy(),
        )
        sex_table = group_metric_table(
            test,
            "Recorded sex",
            "sex_group",
            probability_column=probability_column,
            prediction_column=prediction_column,
        )
        sex_gap = disparity_row(sex_table, "Recorded sex")
        mitigation_rows.append(
            {
                "strategy": strategy,
                **overall,
                **{f"sex_{key}": value for key, value in sex_gap.items() if key != "attribute"},
            }
        )
        sex_table.assign(strategy=strategy).to_csv(
            args.artifacts / f"step5_{strategy.lower().replace(' ', '_')}_sex_metrics.csv",
            index=False,
        )
    mitigation = pd.DataFrame(mitigation_rows)
    mitigation.to_csv(args.artifacts / "step5_mitigation_comparison.csv", index=False)

    # Global explanations use a balanced sample internally, but only aggregate
    # importance is written. Local explanations use a declared synthetic case.
    positive = test[test.outcome == 1]
    negative = test[test.outcome == 0]
    positive_sample = positive.sample(n=min(40, len(positive)), random_state=random_state + 71)
    negative_sample = negative.sample(n=min(40, len(negative)), random_state=random_state + 72)
    explain_frame = (
        pd.concat([positive_sample, negative_sample])
        .drop_duplicates(subset=["pid", "session_date"])
        .head(80)
        .reset_index(drop=True)
    )
    background = train[features].sample(n=min(220, len(train)), random_state=random_state + 73)
    shap_values = approximate_interventional_shap(
        model,
        background,
        explain_frame[features],
        explain_frame.outcome.to_numpy(),
        permutations=48,
        random_state=random_state + 74,
    )
    shap_global = save_shap_global_summary(
        shap_values, args.artifacts / "step5_shap_summary.png"
    )
    shap_global.to_csv(args.artifacts / "step5_shap_global_importance.csv", index=False)

    synthetic_case, synthetic_specification = synthetic_high_risk_case(features)
    synthetic_frame = synthetic_case.to_frame().T
    synthetic_probability = float(model.predict_proba(synthetic_frame)[:, 1][0])
    synthetic_specification["model_probability"] = synthetic_probability
    synthetic_specification["operating_threshold"] = threshold
    synthetic_specification["model_flag"] = bool(synthetic_probability >= threshold)
    (args.artifacts / "step5_synthetic_case.json").write_text(
        json.dumps(synthetic_specification, indent=2), encoding="utf-8"
    )

    synthetic_shap = approximate_interventional_shap(
        model,
        background,
        synthetic_frame,
        outcomes=None,
        permutations=96,
        random_state=random_state + 75,
    )
    local_shap = (
        synthetic_shap
        .assign(absolute_shap=lambda table: table.shap_value.abs())
        .sort_values("absolute_shap", ascending=False)
    )
    local_shap.to_csv(args.artifacts / "step5_shap_local_synthetic.csv", index=False)
    save_local_explanation(
        local_shap,
        args.artifacts / "step5_shap_local_synthetic.png",
        "Approximate SHAP explanation for a synthetic high-risk scenario",
        "shap_value",
    )

    lime_table, lime_metadata = lime_style_explanation(
        model,
        synthetic_case,
        background,
        samples=2500,
        random_state=random_state + 76,
    )
    lime_table.to_csv(args.artifacts / "step5_lime_local_synthetic.csv", index=False)
    lime_metadata.update(
        {
            "scenario_type": "synthetic",
            "not_a_patient_record": True,
            "scenario_file": "artifacts/step5_shap_local_synthetic.csv",
        }
    )
    (args.artifacts / "step5_lime_local_metadata.json").write_text(
        json.dumps(lime_metadata, indent=2), encoding="utf-8"
    )
    save_local_explanation(
        lime_table,
        args.artifacts / "step5_lime_local_synthetic.png",
        "LIME-style local surrogate for the same synthetic scenario",
        "lime_coefficient",
    )

    save_pdp_ice(
        model,
        train[features],
        args.artifacts / "step5_pdp_ice.png",
        random_state + 77,
    )

    for legacy_name in [
        "step5_approximate_shap_values.csv",
        "step5_shap_local_high_risk.csv",
        "step5_lime_local_high_risk.csv",
        "step5_shap_local_high_risk.png",
        "step5_lime_local_high_risk.png",
    ]:
        (args.artifacts / legacy_name).unlink(missing_ok=True)

    save_fairness_overview(group_metrics, args.artifacts / "step5_fairness_overview.png")
    save_disparity_summary(disparities, args.artifacts / "step5_disparity_summary.png")
    save_mitigation_tradeoff(mitigation, args.artifacts / "step5_mitigation_tradeoff.png")

    model_comparison = pd.read_csv(args.artifacts / "model_comparison.csv")
    selected = model_comparison[model_comparison.model == "Random forest"].iloc[0]
    final_test = load_json(args.artifacts / "final_test_metrics.json")["test_metrics_calibrated"]
    robustness = pd.DataFrame(
        [
            {
                "risk": "Class imbalance",
                "evidence": f"Test prevalence {test.outcome.mean():.3%}; no-skill average precision equals prevalence",
                "assessment": "Material",
                "response": "Use average precision, sensitivity, precision, calibration, and workload metrics rather than accuracy alone",
            },
            {
                "risk": "Patient leakage",
                "evidence": f"Patient overlaps train-validation-test: {overlap}",
                "assessment": "Controlled in internal evaluation",
                "response": "Retain patient-disjoint splits and grouped cross-validation",
            },
            {
                "risk": "Temporal leakage",
                "evidence": "Only index-time or lagged prior-session predictors are used; subsequent blood pressures define the outcome",
                "assessment": "Controlled by feature design",
                "response": "Preserve the prediction-time boundary in production feature pipelines",
            },
            {
                "risk": "Overfitting or optimism",
                "evidence": f"Grouped-CV AP {selected.cv_average_precision_mean:.3f}, validation AP {selected.validation_average_precision:.3f}, test AP {final_test['average_precision']:.3f}",
                "assessment": "Residual concern",
                "response": "Report patient-bootstrap intervals and require external temporal and geographic validation",
            },
            {
                "risk": "Probability miscalibration",
                "evidence": f"Test Brier score {final_test['brier_score']:.3f}; calibration weakens in sparsely populated high-risk bins",
                "assessment": "Monitor",
                "response": "Recalibrate only on new local validation data and monitor calibration drift",
            },
            {
                "risk": "Repeated-session dominance",
                "evidence": f"{len(test):,} test sessions arise from {test.pid.nunique()} patients",
                "assessment": "Material",
                "response": "Use patient-cluster bootstrap intervals and patient-equal-weight sensitivity analyses",
            },
        ]
    )
    robustness.to_csv(args.artifacts / "step5_robustness_audit.csv", index=False)

    ethical_risks = pd.DataFrame(
        [
            ["Missed high-risk session", "Patient", "False negative", "High", "Clinician review, conservative sensitivity target, outcome monitoring", "Residual false negatives remain"],
            ["Alert fatigue", "Nurses and physicians", "False positives and excessive alert volume", "High", "Capacity-based alerting, configurable thresholds, burden dashboard", "20% capacity still produces substantial false-alert burden"],
            ["Unequal access to review", "Protected or underserved groups", "Different selection or error rates", "High", "Subgroup monitoring, reweighting study, governance review", "Race and socioeconomic fairness are unmeasured"],
            ["Automation bias", "Patients and clinicians", "Risk score treated as diagnosis or treatment order", "High", "Decision-support-only label, explanation, override and documentation", "Human factors require prospective testing"],
            ["Privacy and re-identification", "Patients", "Longitudinal dialysis data are linkable", "High", "Minimum necessary data, access controls, audit logs, retention limits", "Public data do not remove future deployment privacy duties"],
            ["Performance drift", "Future patients", "Population, protocol, or sensor changes", "Medium", "Calibration and subgroup drift monitoring with rollback", "No prospective drift evidence yet"],
        ],
        columns=["hazard", "stakeholder", "mechanism", "severity", "mitigation", "residual_risk"],
    )
    ethical_risks.to_csv(args.artifacts / "step5_ethical_risk_register.csv", index=False)

    summary = {
        "test_sessions": int(len(test)),
        "test_patients": int(test.pid.nunique()),
        "threshold": threshold,
        "recorded_attributes_audited": ["Recorded sex", "Age group"],
        "clinical_subgroups_audited": ["Diabetes status"],
        "unavailable_attributes": ["Race or ethnicity", "Socioeconomic status", "Gender identity"],
        "bootstrap_iterations": bootstrap_iterations,
        "patient_overlap": overlap,
        "counterfactual_sex_audit": counterfactual,
        "validation_sex_specific_thresholds": threshold_record,
        "lime_local_fidelity": lime_metadata,
        "interpretation": "Internal fairness audit only; not evidence of clinical benefit, causal fairness, or deployment readiness.",
    }
    (args.artifacts / "step5_audit_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print("Step 5 audit complete")
    print(disparities.to_string(index=False))
    print("\nMitigation comparison")
    print(
        mitigation[
            [
                "strategy",
                "average_precision",
                "sensitivity",
                "precision",
                "sex_disparate_impact_ratio",
                "sex_equalized_odds_difference",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
