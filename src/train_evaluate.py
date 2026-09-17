"""Train, compare, calibrate, explain, and fairness-audit DIAL-ALERT models."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, CalibrationDisplay
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_selection import SelectFromModel
from sklearn.frozen import FrozenEstimator
from sklearn.impute import SimpleImputer
from sklearn.inspection import PartialDependenceDisplay, permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedGroupKFold,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
import sklearn


warnings.filterwarnings("ignore", category=FutureWarning)
sns.set_theme(style="whitegrid", context="talk")


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def choose_grouped_folds(df: pd.DataFrame, y: pd.Series) -> tuple[np.ndarray, int]:
    """Choose a reproducible five-fold patient split with balanced row counts."""
    best: tuple[float, int, np.ndarray] | None = None
    overall = float(y.mean())
    target = 1 / 5
    for seed in range(1, 101):
        cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        folds = np.full(len(df), -1, dtype=np.int8)
        for fold, (_, idx) in enumerate(cv.split(df, y, groups=df["pid"])):
            folds[idx] = fold
        props = np.array([(folds == i).mean() for i in range(5)])
        prevs = np.array([y.iloc[folds == i].mean() for i in range(5)])
        score = float(np.abs(props - target).sum() + 2 * np.abs(prevs - overall).sum())
        if best is None or score < best[0]:
            best = (score, seed, folds.copy())
    assert best is not None
    return best[2], best[1]


def make_preprocessor(numeric: list[str], categorical: list[str], scale: bool) -> ColumnTransformer:
    numeric_steps: list[tuple[str, object]] = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer(
        [
            ("numeric", Pipeline(numeric_steps), numeric),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def make_pca_preprocessor(numeric: list[str], categorical: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "numeric_pca",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                        ("pca", PCA(n_components=0.95, svd_solver="full")),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        (
                            "onehot",
                            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        ),
                    ]
                ),
                categorical,
            ),
        ],
        remainder="drop",
    )


def model_searches(
    numeric: list[str], categorical: list[str], random_state: int, n_jobs: int
) -> dict[str, tuple[Pipeline, dict, str, int | None]]:
    linear_pre = make_preprocessor(numeric, categorical, scale=True)
    tree_pre = make_preprocessor(numeric, categorical, scale=False)

    return {
        "Logistic regression": (
            Pipeline(
                [
                    ("preprocess", linear_pre),
                    (
                        "model",
                        LogisticRegression(
                            solver="liblinear", max_iter=2000, random_state=random_state
                        ),
                    ),
                ]
            ),
            {
                "model__C": [0.01, 0.1, 1.0, 10.0],
                "model__class_weight": [None, "balanced"],
            },
            "grid",
            None,
        ),
        "L1 feature selection": (
            Pipeline(
                [
                    ("preprocess", make_preprocessor(numeric, categorical, scale=True)),
                    (
                        "select",
                        SelectFromModel(
                            LogisticRegression(
                                l1_ratio=1.0,
                                solver="liblinear",
                                class_weight="balanced",
                                max_iter=2000,
                                random_state=random_state,
                            ),
                            threshold="median",
                        ),
                    ),
                    (
                        "model",
                        LogisticRegression(
                            solver="liblinear",
                            class_weight="balanced",
                            max_iter=2000,
                            random_state=random_state,
                        ),
                    ),
                ]
            ),
            {
                "select__estimator__C": [0.01, 0.1, 1.0],
                "model__C": [0.1, 1.0],
            },
            "grid",
            None,
        ),
        "Decision tree": (
            Pipeline(
                [
                    ("preprocess", make_preprocessor(numeric, categorical, scale=False)),
                    (
                        "model",
                        DecisionTreeClassifier(random_state=random_state),
                    ),
                ]
            ),
            {
                "model__max_depth": [3, 5, 8, 12, None],
                "model__min_samples_leaf": [20, 50, 100, 250],
                "model__class_weight": [None, "balanced"],
                "model__ccp_alpha": [0.0, 0.0001, 0.001],
            },
            "random",
            12,
        ),
        "PCA logistic regression": (
            Pipeline(
                [
                    ("preprocess", make_pca_preprocessor(numeric, categorical)),
                    (
                        "model",
                        LogisticRegression(
                            solver="liblinear", max_iter=2000, random_state=random_state
                        ),
                    ),
                ]
            ),
            {
                "preprocess__numeric_pca__pca__n_components": [0.85, 0.95],
                "model__C": [0.1, 1.0],
                "model__class_weight": [None, "balanced"],
            },
            "grid",
            None,
        ),
        "Random forest": (
            Pipeline(
                [
                    ("preprocess", tree_pre),
                    (
                        "model",
                        RandomForestClassifier(
                            n_estimators=250,
                            random_state=random_state,
                            n_jobs=n_jobs,
                        ),
                    ),
                ]
            ),
            {
                "model__max_depth": [8, 12, 18, None],
                "model__min_samples_leaf": [5, 15, 40],
                "model__max_features": ["sqrt", 0.7],
                "model__class_weight": [None, "balanced_subsample"],
            },
            "random",
            8,
        ),
        "Histogram gradient boosting": (
            Pipeline(
                [
                    ("preprocess", make_preprocessor(numeric, categorical, scale=False)),
                    (
                        "model",
                        HistGradientBoostingClassifier(
                            max_iter=250,
                            early_stopping=True,
                            random_state=random_state,
                        ),
                    ),
                ]
            ),
            {
                "model__learning_rate": [0.03, 0.06, 0.1],
                "model__max_leaf_nodes": [15, 31, 63],
                "model__min_samples_leaf": [20, 50, 100],
                "model__l2_regularization": [0.0, 0.5, 2.0],
                "model__class_weight": [None, "balanced"],
            },
            "random",
            10,
        ),
    }


def top_capacity_metrics(y: np.ndarray, probability: np.ndarray, capacity: float) -> dict:
    n_selected = max(1, int(math.ceil(len(y) * capacity)))
    order = np.argsort(-probability)
    selected = np.zeros(len(y), dtype=bool)
    selected[order[:n_selected]] = True
    event_rate = y.mean()
    precision = y[selected].mean() if selected.any() else np.nan
    recall = y[selected].sum() / y.sum() if y.sum() else np.nan
    return {
        "alert_capacity": capacity,
        "selected_sessions": int(selected.sum()),
        "precision_at_capacity": float(precision),
        "recall_at_capacity": float(recall),
        "lift_at_capacity": float(precision / event_rate) if event_rate else np.nan,
        "false_alerts_per_100_sessions": float((selected & (y == 0)).sum() / len(y) * 100),
    }


def classification_metrics(
    y: np.ndarray, probability: np.ndarray, threshold: float = 0.5, capacity: float = 0.2
) -> dict:
    pred = probability >= threshold
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    result = {
        "average_precision": float(average_precision_score(y, probability)),
        "roc_auc": float(roc_auc_score(y, probability)),
        "brier_score": float(brier_score_loss(y, probability)),
        "log_loss": float(log_loss(y, probability, labels=[0, 1])),
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y, pred)),
        "sensitivity": float(recall_score(y, pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else np.nan,
        "precision": float(precision_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
    result.update(top_capacity_metrics(y, probability, capacity))
    return result


def f2_threshold(y: np.ndarray, probability: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y, probability)
    precision = precision[:-1]
    recall = recall[:-1]
    score = 5 * precision * recall / np.maximum(4 * precision + recall, 1e-12)
    return float(thresholds[int(np.nanargmax(score))])


def patient_bootstrap_intervals(
    y: np.ndarray,
    probability: np.ndarray,
    groups: np.ndarray,
    threshold: float,
    capacity: float,
    iterations: int,
    random_state: int,
) -> pd.DataFrame:
    """Estimate percentile intervals while preserving within-patient dependence."""
    rng = np.random.default_rng(random_state)
    unique_groups = np.unique(groups)
    group_indices = {group: np.flatnonzero(groups == group) for group in unique_groups}
    records = []
    for _ in range(iterations):
        sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        idx = np.concatenate([group_indices[group] for group in sampled_groups])
        metrics = classification_metrics(y[idx], probability[idx], threshold, capacity)
        records.append(
            {
                "average_precision": metrics["average_precision"],
                "roc_auc": metrics["roc_auc"],
                "brier_score": metrics["brier_score"],
                "sensitivity": metrics["sensitivity"],
                "specificity": metrics["specificity"],
                "precision": metrics["precision"],
                "f1": metrics["f1"],
                "precision_at_capacity": metrics["precision_at_capacity"],
                "recall_at_capacity": metrics["recall_at_capacity"],
                "lift_at_capacity": metrics["lift_at_capacity"],
            }
        )
    samples = pd.DataFrame(records)
    point = classification_metrics(y, probability, threshold, capacity)
    rows = []
    for metric in samples.columns:
        rows.append(
            {
                "metric": metric,
                "estimate": float(point[metric]),
                "ci_lower_95": float(samples[metric].quantile(0.025)),
                "ci_upper_95": float(samples[metric].quantile(0.975)),
                "method": f"Patient-cluster bootstrap with {iterations} resamples",
            }
        )
    return pd.DataFrame(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def group_metrics(
    y: np.ndarray,
    probability: np.ndarray,
    pred: np.ndarray,
    group: pd.Series,
    group_name: str,
) -> tuple[pd.DataFrame, dict]:
    rows = []
    group_values = group.astype("string").fillna("Missing")
    for level in sorted(group_values.unique()):
        mask = (group_values == level).to_numpy()
        yg, pg, pr = y[mask], probability[mask], pred[mask]
        tn, fp, fn, tp = confusion_matrix(yg, pr, labels=[0, 1]).ravel()
        rows.append(
            {
                "attribute": group_name,
                "group": str(level),
                "n": int(mask.sum()),
                "events": int(yg.sum()),
                "prevalence": float(yg.mean()),
                "selection_rate": float(pr.mean()),
                "sensitivity": float(tp / (tp + fn)) if tp + fn else np.nan,
                "false_positive_rate": float(fp / (fp + tn)) if fp + tn else np.nan,
                "specificity": float(tn / (tn + fp)) if tn + fp else np.nan,
                "precision": float(tp / (tp + fp)) if tp + fp else np.nan,
                "average_precision": float(average_precision_score(yg, pg)) if len(np.unique(yg)) > 1 else np.nan,
                "brier_score": float(brier_score_loss(yg, pg)),
            }
        )
    table = pd.DataFrame(rows)
    summary = {
        "attribute": group_name,
        "demographic_parity_difference": float(table.selection_rate.max() - table.selection_rate.min()),
        "disparate_impact_ratio": float(table.selection_rate.min() / table.selection_rate.max())
        if table.selection_rate.max() > 0
        else np.nan,
        "equal_opportunity_difference": float(table.sensitivity.max() - table.sensitivity.min()),
        "false_positive_rate_difference": float(
            table.false_positive_rate.max() - table.false_positive_rate.min()
        ),
    }
    summary["equalized_odds_difference"] = max(
        summary["equal_opportunity_difference"], summary["false_positive_rate_difference"]
    )
    return table, summary


def save_roc_pr_plot(y: np.ndarray, probability: np.ndarray, output: Path) -> None:
    fpr, tpr, _ = roc_curve(y, probability)
    precision, recall, _ = precision_recall_curve(y, probability)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    axes[0].plot(fpr, tpr, color="#0B5C8E", linewidth=3)
    axes[0].plot([0, 1], [0, 1], "--", color="#8C8C8C")
    axes[0].set(title="Receiver operating characteristic", xlabel="False positive rate", ylabel="Sensitivity")
    axes[1].plot(recall, precision, color="#C84630", linewidth=3)
    axes[1].axhline(y.mean(), linestyle="--", color="#8C8C8C", label="Event prevalence")
    axes[1].set(title="Precision recall curve", xlabel="Recall", ylabel="Precision")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_capacity_curve(y: np.ndarray, probability: np.ndarray, output: Path, csv_output: Path) -> None:
    rows = [top_capacity_metrics(y, probability, float(c)) for c in np.arange(0.05, 0.51, 0.05)]
    table = pd.DataFrame(rows)
    table.to_csv(csv_output, index=False)
    fig, ax1 = plt.subplots(figsize=(8.5, 5.4))
    ax1.plot(table.alert_capacity * 100, table.recall_at_capacity * 100, marker="o", linewidth=2.5, label="Cases captured")
    ax1.plot(table.alert_capacity * 100, table.precision_at_capacity * 100, marker="s", linewidth=2.5, label="Positive predictive value")
    ax1.set(xlabel="Sessions receiving an alert (%)", ylabel="Percent", ylim=(0, 100), title="Clinical alert workload")
    ax1.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def transformed_feature_names(pipeline: Pipeline) -> tuple[np.ndarray, np.ndarray | None]:
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    support = None
    if "select" in pipeline.named_steps:
        support = pipeline.named_steps["select"].get_support()
        names = names[support]
    return np.asarray(names), support


def generate_explanations(
    base_pipeline: Pipeline,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    output_dir: Path,
    random_state: int,
) -> None:
    for stale in [
        "shap_beeswarm.png",
        "shap_local_high_risk.png",
        "partial_dependence_ice.png",
        "shap_error.txt",
    ]:
        (output_dir / stale).unlink(missing_ok=True)
    sample = X_test.sample(min(3000, len(X_test)), random_state=random_state)
    sample_y = y_test[sample.index.to_numpy()] if isinstance(X_test.index, pd.RangeIndex) else None

    perm = permutation_importance(
        base_pipeline,
        sample,
        y_test[X_test.index.get_indexer(sample.index)],
        scoring="average_precision",
        n_repeats=8,
        random_state=random_state,
        n_jobs=2,
    )
    importance = pd.DataFrame(
        {
            "feature": X_test.columns,
            "importance_mean": perm.importances_mean,
            "importance_sd": perm.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)
    importance.to_csv(output_dir / "permutation_importance.csv", index=False)
    top = importance.head(12).sort_values("importance_mean")
    fig, ax = plt.subplots(figsize=(8.6, 6.2))
    ax.barh(top.feature, top.importance_mean, xerr=top.importance_sd, color="#0B5C8E")
    ax.set(title="Permutation importance on the test set", xlabel="Decrease in average precision")
    fig.tight_layout()
    fig.savefig(output_dir / "permutation_importance.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    numeric_top = [f for f in importance.feature if pd.api.types.is_numeric_dtype(X_test[f])][:3]
    if numeric_top:
        fig, axes = plt.subplots(1, len(numeric_top), figsize=(5 * len(numeric_top), 4.6), squeeze=False)
        PartialDependenceDisplay.from_estimator(
            base_pipeline,
            sample,
            features=numeric_top,
            kind="average",
            ax=axes.ravel(),
        )
        fig.suptitle("Aggregate partial dependence", y=1.03)
        fig.tight_layout()
        fig.savefig(output_dir / "partial_dependence.png", dpi=220, bbox_inches="tight")
        plt.close(fig)

    # SHAP explains the uncalibrated base model because calibration remaps the
    # score after model fitting and does not change the underlying predictors.
    try:
        import shap

        background_raw = X_train.sample(min(200, len(X_train)), random_state=random_state)
        explain_raw = X_test.sample(min(800, len(X_test)), random_state=random_state + 1)
        pre = base_pipeline.named_steps["preprocess"]
        background = pre.transform(background_raw)
        explain_data = pre.transform(explain_raw)
        names, support = transformed_feature_names(base_pipeline)
        if support is not None:
            selector = base_pipeline.named_steps["select"]
            background = selector.transform(background)
            explain_data = selector.transform(explain_data)
        model = base_pipeline.named_steps["model"]
        explainer = shap.Explainer(model, background, feature_names=names)
        explanation = explainer(explain_data, check_additivity=False)
        if explanation.values.ndim == 3:
            explanation = shap.Explanation(
                values=explanation.values[:, :, 1],
                base_values=explanation.base_values[:, 1],
                data=explanation.data,
                feature_names=names,
            )
        mean_absolute = np.abs(explanation.values).mean(axis=0)
        summary = (
            pd.DataFrame({"feature": names, "mean_absolute_shap": mean_absolute})
            .sort_values("mean_absolute_shap", ascending=False)
            .reset_index(drop=True)
        )
        summary.to_csv(output_dir / "shap_global_importance.csv", index=False)
        chart = summary.head(12).sort_values("mean_absolute_shap")
        fig, ax = plt.subplots(figsize=(9, 6.5))
        ax.barh(chart.feature, chart.mean_absolute_shap, color="#0B5C8E")
        ax.set(
            title="Aggregate SHAP feature importance",
            xlabel="Mean absolute SHAP value",
        )
        fig.tight_layout()
        fig.savefig(output_dir / "shap_global_bar.png", dpi=220, bbox_inches="tight")
        plt.close(fig)
    except Exception as exc:  # Keep the core analysis reproducible if SHAP lacks model support.
        (output_dir / "shap_error.txt").write_text(str(exc), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/processed/hemobp_session_level.csv.gz"))
    parser.add_argument("--config", type=Path, default=Path("configs/model_config.json"))
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    parser.add_argument("--models", type=Path, default=Path("models"))
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    args.models.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)
    random_state = int(config["random_state"])
    n_jobs = int(config.get("n_jobs", 2))
    grouped_cv_folds = int(config.get("grouped_cv_folds", 3))
    bootstrap_iterations = int(config.get("bootstrap_iterations", 500))
    selection_tolerance = float(config.get("model_selection_tolerance", 0.01))
    numeric = list(config["numeric_features"])
    categorical = list(config["categorical_features"])
    features = numeric + categorical
    target = config["primary_outcome"]
    capacity = float(config["alert_capacity"])

    df = pd.read_csv(args.data, parse_dates=["session_date", "index_datetime"])
    df["prior_session_count"] = np.log1p(df["prior_session_count"])
    y = df[target].astype(int)
    folds, split_seed = choose_grouped_folds(df, y)
    df["split"] = np.where(folds == 0, "test", np.where(folds == 1, "validation", "training"))
    df[["pid", "session_date", "split"]].to_csv(
        args.artifacts / "split_assignments.csv.gz", index=False, compression="gzip"
    )

    split_summary = (
        df.groupby("split")[target]
        .agg(sessions="size", events="sum", prevalence="mean")
        .reset_index()
    )
    patient_counts = df.groupby("split")["pid"].nunique().rename("patients")
    split_summary = split_summary.merge(patient_counts, on="split")
    split_summary.to_csv(args.artifacts / "split_summary.csv", index=False)
    (args.artifacts / "split_metadata.json").write_text(
        json.dumps({"selected_seed": split_seed}, indent=2), encoding="utf-8"
    )

    train = df[df.split == "training"].copy()
    val = df[df.split == "validation"].copy()
    test = df[df.split == "test"].copy()
    X_train, y_train = train[features], train[target].astype(int).to_numpy()
    X_val, y_val = val[features], val[target].astype(int).to_numpy()
    X_test, y_test = test[features], test[target].astype(int).to_numpy()

    cv = StratifiedGroupKFold(n_splits=grouped_cv_folds, shuffle=True, random_state=random_state)
    searches = model_searches(numeric, categorical, random_state, n_jobs)
    fitted: dict[str, Pipeline] = {}
    comparison_rows: list[dict] = []
    cv_detail: list[pd.DataFrame] = []

    dummy = Pipeline(
        [
            ("preprocess", make_preprocessor(numeric, categorical, scale=False)),
            ("model", DummyClassifier(strategy="prior")),
        ]
    )
    dummy_started = time.perf_counter()
    dummy.fit(X_train, y_train)
    dummy_fit_seconds = time.perf_counter() - dummy_started
    fitted["Dummy prevalence baseline"] = dummy
    dummy_prob = dummy.predict_proba(X_val)[:, 1]
    row = {"model": "Dummy prevalence baseline", "cv_average_precision_mean": y_train.mean(), "cv_average_precision_sd": 0.0, "search_fit_seconds": dummy_fit_seconds}
    row.update({f"validation_{k}": v for k, v in classification_metrics(y_val, dummy_prob, capacity=capacity).items()})
    comparison_rows.append(row)

    for name, (pipeline, parameters, search_type, n_iter) in searches.items():
        if search_type == "grid":
            search = GridSearchCV(
                pipeline,
                parameters,
                scoring="average_precision",
                cv=cv,
                n_jobs=n_jobs,
                refit=True,
                return_train_score=False,
            )
        else:
            search = RandomizedSearchCV(
                pipeline,
                parameters,
                n_iter=int(n_iter or 8),
                scoring="average_precision",
                cv=cv,
                n_jobs=n_jobs,
                refit=True,
                random_state=random_state,
                return_train_score=False,
            )
        search_started = time.perf_counter()
        search.fit(X_train, y_train, groups=train["pid"])
        search_fit_seconds = time.perf_counter() - search_started
        fitted[name] = search.best_estimator_
        probability = search.best_estimator_.predict_proba(X_val)[:, 1]
        row = {
            "model": name,
            "cv_average_precision_mean": float(search.best_score_),
            "cv_average_precision_sd": float(search.cv_results_["std_test_score"][search.best_index_]),
            "best_parameters": json.dumps(search.best_params_, sort_keys=True),
            "search_fit_seconds": float(search_fit_seconds),
        }
        row.update({f"validation_{k}": v for k, v in classification_metrics(y_val, probability, capacity=capacity).items()})
        comparison_rows.append(row)
        detail = pd.DataFrame(search.cv_results_).sort_values("rank_test_score").head(10)
        detail.insert(0, "model", name)
        cv_detail.append(detail)
        joblib.dump(search.best_estimator_, args.models / f"candidate_{name.lower().replace(' ', '_')}.joblib")

    comparison = pd.DataFrame(comparison_rows).sort_values("cv_average_precision_mean", ascending=False)
    comparison.to_csv(args.artifacts / "model_comparison.csv", index=False)
    if cv_detail:
        pd.concat(cv_detail, ignore_index=True).to_csv(args.artifacts / "cv_search_top_results.csv", index=False)

    eligible = comparison.loc[
        ~comparison.model.isin(["Dummy prevalence baseline", "PCA logistic regression"])
    ].copy()
    best_cv = eligible.cv_average_precision_mean.max()
    shortlist = eligible[
        eligible.cv_average_precision_mean >= best_cv - selection_tolerance
    ].copy()
    shortlist = shortlist.sort_values(
        ["validation_brier_score", "cv_average_precision_mean"], ascending=[True, False]
    )
    selected_name = str(shortlist.iloc[0].model)
    base_model = fitted[selected_name]

    # Split validation patients again: one half fits calibration mappings and
    # the other selects the mapping and operating threshold. The test set stays
    # untouched until all choices have been locked.
    validation_cv = StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=random_state)
    calibration_index, decision_index = next(
        validation_cv.split(X_val, y_val, groups=val["pid"])
    )
    X_calibration = X_val.iloc[calibration_index]
    y_calibration = y_val[calibration_index]
    X_decision = X_val.iloc[decision_index]
    y_decision = y_val[decision_index]

    predictors: dict[str, object] = {"none": base_model}
    for method in ["sigmoid", "isotonic"]:
        calibrator = CalibratedClassifierCV(FrozenEstimator(base_model), method=method)
        calibrator.fit(X_calibration, y_calibration)
        predictors[method] = calibrator
    calibration_rows = []
    for method, predictor in predictors.items():
        p = predictor.predict_proba(X_decision)[:, 1]
        calibration_rows.append(
            {
                "method": method,
                "decision_brier_score": brier_score_loss(y_decision, p),
                "decision_log_loss": log_loss(y_decision, p, labels=[0, 1]),
                "decision_average_precision": average_precision_score(y_decision, p),
            }
        )
    calibration_comparison = pd.DataFrame(calibration_rows).sort_values(
        ["decision_brier_score", "decision_log_loss"]
    )
    calibration_comparison.to_csv(args.artifacts / "calibration_method_comparison.csv", index=False)
    selected_calibration = str(calibration_comparison.iloc[0].method)
    final_predictor = predictors[selected_calibration]
    decision_probability = final_predictor.predict_proba(X_decision)[:, 1]
    threshold = f2_threshold(y_decision, decision_probability)

    raw_test_probability = base_model.predict_proba(X_test)[:, 1]
    test_probability = final_predictor.predict_proba(X_test)[:, 1]
    test_metrics = classification_metrics(y_test, test_probability, threshold, capacity)
    test_raw_metrics = classification_metrics(y_test, raw_test_probability, 0.5, capacity)
    final_summary = {
        "selected_model": selected_name,
        "selection_rule": "Highest grouped-CV average precision; within 0.01, lower validation Brier score",
        "calibration_method": selected_calibration,
        "calibration_selection_rule": "Lowest Brier score on a patient-disjoint decision subset",
        "operating_threshold_rule": "F2 maximum on the patient-disjoint decision subset",
        "operating_threshold": threshold,
        "test_metrics_calibrated": test_metrics,
        "test_metrics_uncalibrated": test_raw_metrics,
    }
    (args.artifacts / "final_test_metrics.json").write_text(
        json.dumps(final_summary, indent=2), encoding="utf-8"
    )
    patient_bootstrap_intervals(
        y_test,
        test_probability,
        test["pid"].astype(str).to_numpy(),
        threshold,
        capacity,
        bootstrap_iterations,
        random_state,
    ).to_csv(args.artifacts / "test_metric_confidence_intervals.csv", index=False)
    # LZMA compression keeps the publication artifact comfortably below
    # GitHub's browser/API upload limits without changing the fitted pipeline.
    joblib.dump(
        final_predictor,
        args.models / "dial_alert_final_predictor.joblib",
        compress=("lzma", 6),
    )
    joblib.dump(base_model, args.models / "dial_alert_base_model.joblib")
    (args.models / "decision_threshold.json").write_text(
        json.dumps({"threshold": threshold, "features": features}, indent=2), encoding="utf-8"
    )

    # Core evaluation graphics.
    fig, ax = plt.subplots(figsize=(9, 5.5))
    chart = comparison.sort_values("cv_average_precision_mean")
    ax.barh(chart.model, chart.cv_average_precision_mean, xerr=chart.cv_average_precision_sd, color="#0B5C8E")
    ax.axvline(y_train.mean(), linestyle="--", color="#C84630", label="Training prevalence")
    ax.set(title="Patient-grouped cross-validation", xlabel="Average precision", ylabel="")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(args.artifacts / "model_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    save_roc_pr_plot(y_test, test_probability, args.artifacts / "roc_pr_curves.png")
    save_capacity_curve(
        y_test,
        test_probability,
        args.artifacts / "capacity_curve.png",
        args.artifacts / "capacity_metrics.csv",
    )
    fig, ax = plt.subplots(figsize=(6.4, 5.5))
    CalibrationDisplay.from_predictions(y_test, raw_test_probability, n_bins=10, name="Raw model", ax=ax)
    if selected_calibration != "none":
        CalibrationDisplay.from_predictions(
            y_test,
            test_probability,
            n_bins=10,
            name=f"{selected_calibration.title()} calibrated",
            ax=ax,
        )
    ax.set_title("Probability calibration on the test set")
    fig.tight_layout()
    fig.savefig(args.artifacts / "calibration_plot.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    pred = test_probability >= threshold
    cm = confusion_matrix(y_test, pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax)
    ax.set(title="Test-set confusion matrix", xlabel="Predicted class", ylabel="Observed class")
    ax.set_xticklabels(["No IDH", "IDH"])
    ax.set_yticklabels(["No IDH", "IDH"], rotation=0)
    fig.tight_layout()
    fig.savefig(args.artifacts / "confusion_matrix.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Fairness audit across available demographic and clinically relevant groups.
    test_age_group = pd.cut(
        test["age_years"], [-np.inf, 54, 64, 74, np.inf], labels=["Under 55", "55 to 64", "65 to 74", "75 and older"]
    )
    fairness_tables = []
    fairness_summaries = []
    for group_series, name in [
        (test["gender"], "Sex"),
        (test_age_group, "Age group"),
        (test["DM"].map({0: "No diabetes", 1: "Diabetes"}), "Diabetes status"),
    ]:
        table, summary = group_metrics(y_test, test_probability, pred, group_series.reset_index(drop=True), name)
        fairness_tables.append(table)
        fairness_summaries.append(summary)
    fairness = pd.concat(fairness_tables, ignore_index=True)
    fairness_summary = pd.DataFrame(fairness_summaries)
    fairness.to_csv(args.artifacts / "fairness_group_metrics.csv", index=False)
    fairness_summary.to_csv(args.artifacts / "fairness_disparities.csv", index=False)

    sex_table = fairness[fairness.attribute == "Sex"].copy()
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    for ax, metric, title in zip(
        axes,
        ["sensitivity", "false_positive_rate", "selection_rate"],
        ["Sensitivity", "False positive rate", "Selection rate"],
    ):
        sns.barplot(data=sex_table, x="group", y=metric, hue="group", legend=False, palette=["#5B8FF9", "#F6BD16"], ax=ax)
        ax.set(title=title, xlabel="", ylabel="Rate", ylim=(0, 1))
    fig.suptitle("Sex subgroup audit on the untouched test set", y=1.03)
    fig.tight_layout()
    fig.savefig(args.artifacts / "fairness_sex.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    # Quantitative mitigation experiment: reweight training rows so sex and
    # outcome combinations contribute equally relative to their marginals.
    sensitive = train["gender"].astype(str)
    weight_table = pd.crosstab(sensitive, y_train, normalize=True)
    p_a = sensitive.value_counts(normalize=True)
    p_y = pd.Series(y_train).value_counts(normalize=True)
    sample_weight = np.array(
        [p_a[a] * p_y[int(label)] / weight_table.loc[a, int(label)] for a, label in zip(sensitive, y_train)]
    )
    mitigation_model = clone(base_model)
    mitigation_model.fit(X_train, y_train, model__sample_weight=sample_weight)
    mitigation_predictor: object = mitigation_model
    if selected_calibration != "none":
        mitigation_predictor = CalibratedClassifierCV(
            FrozenEstimator(mitigation_model), method=selected_calibration
        )
        mitigation_predictor.fit(X_calibration, y_calibration)
    mitigation_probability = mitigation_predictor.predict_proba(X_test)[:, 1]
    mitigation_pred = mitigation_probability >= threshold
    mitigation_sex, mitigation_summary = group_metrics(
        y_test,
        mitigation_probability,
        mitigation_pred,
        test["gender"].reset_index(drop=True),
        "Sex reweighted model",
    )
    mitigation_sex.to_csv(args.artifacts / "mitigation_sex_metrics.csv", index=False)
    mitigation_record = {
        "method": "Training-sample reweighting across sex and outcome combinations",
        "overall_metrics": classification_metrics(y_test, mitigation_probability, threshold, capacity),
        "fairness_summary": mitigation_summary,
    }
    (args.artifacts / "mitigation_results.json").write_text(
        json.dumps(mitigation_record, indent=2), encoding="utf-8"
    )
    joblib.dump(mitigation_predictor, args.models / "dial_alert_gender_reweighted_model.joblib")

    # Record feature-selection and PCA evidence required by the rubric.
    selector_pipeline = fitted["L1 feature selection"]
    selector_names = selector_pipeline.named_steps["preprocess"].get_feature_names_out()
    selector_mask = selector_pipeline.named_steps["select"].get_support()
    pd.DataFrame(
        {"feature": selector_names, "selected": selector_mask.astype(int)}
    ).to_csv(args.artifacts / "l1_selected_features.csv", index=False)
    pca_pipeline = fitted["PCA logistic regression"]
    pca = pca_pipeline.named_steps["preprocess"].named_transformers_["numeric_pca"].named_steps["pca"]
    pd.DataFrame(
        {
            "component": np.arange(1, len(pca.explained_variance_ratio_) + 1),
            "explained_variance_ratio": pca.explained_variance_ratio_,
            "cumulative_explained_variance": np.cumsum(pca.explained_variance_ratio_),
        }
    ).to_csv(args.artifacts / "pca_explained_variance.csv", index=False)

    # Reset indices so explanation sampling maps cleanly to test labels.
    generate_explanations(
        base_model,
        X_train.reset_index(drop=True),
        X_test.reset_index(drop=True),
        y_test,
        args.artifacts,
        random_state,
    )

    candidate_model_files = [
        args.models / f"candidate_{name.lower().replace(' ', '_')}.joblib"
        for name in searches
    ]
    model_files = candidate_model_files + [
        args.models / "dial_alert_base_model.joblib",
        args.models / "dial_alert_final_predictor.joblib",
        args.models / "decision_threshold.json",
    ]
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
        "data_file": str(args.data),
        "data_sha256": sha256_file(args.data),
        "config_file": str(args.config),
        "config_sha256": sha256_file(args.config),
        "random_state": random_state,
        "n_jobs": n_jobs,
        "grouped_cv_folds": grouped_cv_folds,
        "split_seed": split_seed,
        "selected_model": selected_name,
        "selected_calibration": selected_calibration,
        "model_files": [
            {
                "file": str(path.relative_to(args.models.parent)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in model_files
        ],
    }
    (args.models / "model_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print(json.dumps(final_summary, indent=2))
    print("\nSplit summary\n", split_summary.to_string(index=False))
    print("\nModel comparison\n", comparison[["model", "cv_average_precision_mean", "validation_average_precision", "validation_brier_score"]].to_string(index=False))


if __name__ == "__main__":
    main()
