"""Generate EDA figures and the DIAL-ALERT data dictionary."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd
import seaborn as sns


sns.set_theme(style="whitegrid", context="talk")
BLUE = "#0B5C8E"
ORANGE = "#E07A35"
TEAL = "#2A9D8F"
RED = "#C84630"

DISPLAY_NAMES = {
    "dialysis_vintage_years": "Dialysis vintage",
    "prior_idh_rate": "Prior IDH rate",
    "prior_nadir_sbp": "Prior nadir SBP",
    "prior_session_idh": "Prior-session IDH",
    "initial_conductivity_ms_cm": "Initial conductivity",
    "fluid_excess_pct": "Fluid excess percent",
    "fluid_excess_kg": "Fluid excess kg",
    "temperature": "Body temperature",
    "initial_blood_flow_ml_min": "Initial blood flow",
    "age_years": "Age",
    "dryweight": "Dry weight",
    "initial_uf_l_h": "Initial UF rate",
    "weightstart": "Predialysis weight",
    "initial_uf_ml_kg_h": "Weight-normalized UF rate",
    "baseline_dbp": "Baseline DBP",
    "baseline_sbp": "Baseline SBP",
    "baseline_map": "Baseline MAP",
    "baseline_pulse_pressure": "Baseline pulse pressure",
    "prior_session_count": "Prior session count",
}

CONTINUOUS_PREDICTORS = [
    "age_years",
    "dialysis_vintage_years",
    "weightstart",
    "dryweight",
    "temperature",
    "fluid_excess_kg",
    "fluid_excess_pct",
    "baseline_sbp",
    "baseline_dbp",
    "baseline_map",
    "baseline_pulse_pressure",
    "initial_uf_l_h",
    "initial_uf_ml_kg_h",
    "initial_blood_flow_ml_min",
    "initial_dialysate_temp_c",
    "initial_conductivity_ms_cm",
    "prior_nadir_sbp",
    "prior_idh_rate",
    "prior_session_count",
]


def save_cohort_flow(flow: dict, output: Path) -> None:
    labels = [
        "D1 patient-days with valid dates",
        "Patient-days linked to VIP",
        "Sessions with an index record",
        "Final eligible sessions",
    ]
    values = [
        flow["d1_valid_unique_patient_days"],
        flow["linked_patient_days"],
        flow["patient_days_with_index_record"],
        flow["final_eligible_sessions"],
    ]
    fig, ax = plt.subplots(figsize=(10, 5.8))
    bars = ax.barh(labels[::-1], values[::-1], color=[TEAL, BLUE, ORANGE, "#7A5195"])
    ax.bar_label(bars, labels=[f"{v:,}" for v in values[::-1]], padding=8, fontsize=12)
    ax.set(title="Cohort construction", xlabel="Patient-days or sessions", xlim=(0, max(values) * 1.18))
    ax.xaxis.set_major_locator(MaxNLocator(5))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_outcome_definitions(df: pd.DataFrame, output: Path) -> None:
    rates = pd.Series(
        {
            "SBP below 90 mmHg": df.idh_absolute.mean(),
            "SBP drop of at least 20 mmHg": df.idh_drop_20.mean(),
            "Baseline-adjusted nadir threshold": df.idh_flythe.mean(),
        }
    ).sort_values()
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    bars = ax.barh(rates.index, rates.values * 100, color=[BLUE, TEAL, ORANGE])
    ax.bar_label(bars, labels=[f"{x:.1f}%" for x in rates.values * 100], padding=6)
    ax.set(title="Outcome definition sensitivity analysis", xlabel="Sessions meeting the definition (%)", xlim=(0, rates.max() * 110))
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_bp_distributions(df: pd.DataFrame, output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    sns.histplot(data=df, x="baseline_sbp", hue="idh_absolute", bins=45, stat="density", common_norm=False, element="step", ax=axes[0], palette=[BLUE, RED])
    axes[0].set(title="Baseline systolic blood pressure", xlabel="SBP at the index measurement (mmHg)", ylabel="Density")
    sns.histplot(data=df, x="nadir_sbp", hue="idh_absolute", bins=45, stat="density", common_norm=False, element="step", ax=axes[1], palette=[BLUE, RED])
    axes[1].set(title="Later intradialytic nadir", xlabel="Nadir SBP after the index measurement (mmHg)", ylabel="Density")
    for ax in axes:
        legend = ax.get_legend()
        if legend:
            legend.set_title("BP-defined IDH")
            for text, label in zip(legend.texts, ["No", "Yes"]):
                text.set_text(label)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_subgroup_prevalence(df: pd.DataFrame, output: Path) -> None:
    age_group = pd.cut(df.age_years, [-np.inf, 54, 64, 74, np.inf], labels=["Under 55", "55 to 64", "65 to 74", "75 and older"])
    frames = []
    for label, series in [
        ("Sex", df.gender.map({"F": "Female", "M": "Male"})),
        ("Age group", age_group),
        ("Diabetes", df.DM.map({0: "No diabetes", 1: "Diabetes"})),
    ]:
        temp = df.groupby(series, observed=True).idh_absolute.agg(["size", "sum", "mean"]).reset_index()
        temp.columns = ["group", "sessions", "events", "prevalence"]
        temp["attribute"] = label
        frames.append(temp)
    table = pd.concat(frames, ignore_index=True)
    table.to_csv(output.with_suffix(".csv"), index=False)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    for ax, (attribute, group) in zip(axes, table.groupby("attribute", sort=False)):
        x = np.arange(len(group))
        bars = ax.bar(x, group.prevalence, color=BLUE, width=0.65)
        ax.set(title=attribute, xlabel="", ylabel="IDH prevalence", ylim=(0, max(0.13, group.prevalence.max() * 1.2)))
        ax.set_xticks(x, group.group)
        ax.tick_params(axis="x", rotation=25)
        ax.bar_label(bars, labels=[f"{v:.1%}" for v in group.prevalence], padding=3, fontsize=10)
    fig.suptitle("Observed BP-defined IDH prevalence by subgroup", y=1.04)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_correlation(df: pd.DataFrame, output: Path) -> None:
    columns = [
        "age_years",
        "dialysis_vintage_years",
        "fluid_excess_pct",
        "baseline_sbp",
        "baseline_dbp",
        "initial_uf_ml_kg_h",
        "initial_blood_flow_ml_min",
        "prior_nadir_sbp",
        "prior_idh_rate",
        "idh_absolute",
    ]
    labels = ["Age", "Vintage", "Fluid excess", "Baseline SBP", "Baseline DBP", "UF rate", "Blood flow", "Prior nadir", "Prior IDH rate", "IDH"]
    corr = df[columns].corr(method="spearman")
    corr.index = labels
    corr.columns = labels
    fig, ax = plt.subplots(figsize=(10, 8.2))
    sns.heatmap(corr, cmap="vlag", center=0, vmin=-1, vmax=1, square=True, linewidths=0.5, cbar_kws={"label": "Spearman correlation"}, ax=ax)
    ax.set_title("Feature correlation matrix")
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_missingness(df: pd.DataFrame, output: Path) -> None:
    missing = (df.isna().mean() * 100).sort_values(ascending=False)
    missing = missing[missing > 0]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    labels = [DISPLAY_NAMES.get(name, name) for name in missing.index[::-1]]
    bars = ax.barh(labels, missing.values[::-1], color=ORANGE)
    ax.bar_label(bars, labels=[f"{v:.2f}%" for v in missing.values[::-1]], padding=5)
    ax.set(title="Missingness in the eligible session table", xlabel="Missing values (%)", xlim=(0, max(2, missing.max() * 1.25)))
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_index_time_distribution(df: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.9))
    sns.histplot(df["index_minute"], bins=np.arange(-0.5, 31.5, 1), color=BLUE, ax=ax)
    ax.axvline(df["index_minute"].median(), color=ORANGE, linestyle="--", linewidth=2,
               label=f"Median {df['index_minute'].median():.0f} minutes")
    ax.set(
        title="Timing of the prediction index record",
        xlabel="Elapsed treatment time at index record (minutes)",
        ylabel="Sessions",
        xlim=(-0.5, 30.5),
    )
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_feature_distributions(df: pd.DataFrame, output: Path) -> None:
    features = [
        ("baseline_sbp", "Baseline SBP (mmHg)"),
        ("fluid_excess_pct", "Fluid excess (% dry weight)"),
        ("initial_uf_ml_kg_h", "Initial UF rate (mL/kg/hour)"),
        ("prior_nadir_sbp", "Previous-session nadir SBP (mmHg)"),
        ("prior_idh_rate", "Previous IDH rate"),
        ("age_years", "Age (years)"),
    ]
    sample = df.sample(min(50000, len(df)), random_state=42)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8.6))
    for ax, (feature, label) in zip(axes.ravel(), features):
        values = sample[feature]
        low, high = values.quantile([0.005, 0.995])
        plot = sample.loc[values.between(low, high), [feature, "idh_absolute"]].copy()
        sns.histplot(
            data=plot,
            x=feature,
            hue="idh_absolute",
            bins=35,
            stat="density",
            common_norm=False,
            element="step",
            palette=[BLUE, RED],
            legend=False,
            ax=ax,
        )
        ax.set(title=label, xlabel="", ylabel="Density")
    handles = [
        plt.Line2D([0], [0], color=BLUE, lw=3, label="No BP-defined IDH"),
        plt.Line2D([0], [0], color=RED, lw=3, label="BP-defined IDH"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False)
    fig.suptitle("Predictor distributions by outcome", y=1.01)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_binned_relationships(df: pd.DataFrame, output: Path, csv_output: Path) -> None:
    features = [
        ("baseline_sbp", "Baseline SBP"),
        ("fluid_excess_pct", "Fluid excess"),
        ("initial_uf_ml_kg_h", "Initial UF rate"),
        ("prior_nadir_sbp", "Previous nadir SBP"),
    ]
    rows: list[pd.DataFrame] = []
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5))
    for ax, (feature, label) in zip(axes.ravel(), features):
        temp = df[[feature, "idh_absolute"]].dropna().copy()
        temp["bin"] = pd.qcut(temp[feature], q=10, duplicates="drop")
        summary = temp.groupby("bin", observed=True).agg(
            midpoint=(feature, "median"),
            sessions=("idh_absolute", "size"),
            events=("idh_absolute", "sum"),
            event_rate=("idh_absolute", "mean"),
        ).reset_index(drop=True)
        summary["standard_error"] = np.sqrt(
            summary.event_rate * (1 - summary.event_rate) / summary.sessions
        )
        summary["feature"] = feature
        rows.append(summary)
        ax.errorbar(
            summary.midpoint,
            summary.event_rate * 100,
            yerr=1.96 * summary.standard_error * 100,
            marker="o",
            linewidth=2.2,
            capsize=3,
            color=BLUE,
        )
        ax.set(title=label, xlabel="Decile median", ylabel="BP-defined IDH (%)")
    pd.concat(rows, ignore_index=True).to_csv(csv_output, index=False)
    fig.suptitle("Observed outcome rate across predictor deciles", y=1.01)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_outlier_summary(df: pd.DataFrame, output: Path, csv_output: Path) -> None:
    rows = []
    for feature in CONTINUOUS_PREDICTORS:
        values = df[feature].dropna()
        q1, median, q3 = values.quantile([0.25, 0.5, 0.75])
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        flagged = ((values < lower) | (values > upper)).sum()
        rows.append(
            {
                "feature": feature,
                "nonmissing": int(len(values)),
                "minimum": float(values.min()),
                "q1": float(q1),
                "median": float(median),
                "q3": float(q3),
                "maximum": float(values.max()),
                "iqr_lower_fence": float(lower),
                "iqr_upper_fence": float(upper),
                "iqr_flagged_n": int(flagged),
                "iqr_flagged_pct": float(flagged / len(values) * 100),
                "disposition": "Retained after physiologic-range screening; IQR flags are descriptive, not automatic exclusions",
            }
        )
    summary = pd.DataFrame(rows).sort_values("iqr_flagged_pct", ascending=False)
    summary.to_csv(csv_output, index=False)
    top = summary.head(12).sort_values("iqr_flagged_pct")
    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    labels = [DISPLAY_NAMES.get(name, name) for name in top.feature]
    bars = ax.barh(labels, top.iqr_flagged_pct, color=ORANGE)
    ax.bar_label(bars, labels=[f"{v:.1f}%" for v in top.iqr_flagged_pct], padding=4, fontsize=9)
    ax.set(
        title="Descriptive IQR outlier flags after physiologic screening",
        xlabel="Observations outside 1.5 IQR fences (%)",
        xlim=(0, max(1, top.iqr_flagged_pct.max() * 1.18)),
    )
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_pca_variance(pca_csv: Path, output: Path) -> None:
    pca = pd.read_csv(pca_csv)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.plot(pca.component, pca.cumulative_explained_variance * 100, marker="o", color=BLUE, linewidth=2.5)
    ax.axhline(85, color=ORANGE, linestyle="--", label="85% variance threshold")
    ax.set(
        title="PCA cumulative explained variance",
        xlabel="Principal components",
        ylabel="Cumulative explained variance (%)",
        ylim=(0, 100),
        xticks=pca.component,
    )
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_cleaning_audit(flow: dict, output: Path) -> None:
    rows = [
        ("Raw patient table", flow["patient_rows"], "Retained as the source of patient-level characteristics"),
        ("Raw session table", flow["d1_rows"], "Inspected dates and patient-day keys"),
        ("Session rows with missing dates removed", flow["d1_missing_date_rows_removed"], "Excluded because no session date was available for linkage"),
        ("Duplicate patient-day session rows removed", flow["d1_duplicate_patient_day_rows_removed"], "Stable chronological rule retained the first row per patient-day"),
        ("Valid unique patient-days", flow["d1_valid_unique_patient_days"], "Used as the session linkage frame"),
        ("Raw monitoring records", flow["vip_rows"], "Linked by patient and calendar date"),
        ("Linked monitoring records", flow["vip_rows_linked_to_d1"], "Screened against the documented SBP, DBP, and elapsed-time envelope"),
        ("Linked monitoring rows outside bounds removed", flow["vip_rows_outside_documented_bounds_removed"], "Excluded only when outside the documented source envelope"),
        ("Exact linked monitoring duplicates removed", flow["exact_vip_duplicates_removed"], "Exact duplicate records only; repeated valid readings were preserved"),
        ("Linked patient-days", flow["linked_patient_days"], "Required a valid active-dialysis index record"),
        ("Patient-days with index record", flow["patient_days_with_index_record"], "Required at least one record after the index time"),
        ("Sessions with post-index records", flow["sessions_with_post_index_records"], "Applied sequential outcome-eligibility criteria"),
        ("Sessions removed for baseline SBP below 90", flow["sessions_removed_baseline_sbp_below_90"], "Excluded prevalent hypotension at prediction time"),
        ("Sessions removed for fewer than two later minutes", flow["sessions_removed_insufficient_later_minutes"], "Reduced false negatives from sparse follow-up"),
        ("Sessions removed for follow-up below 120 minutes", flow["sessions_removed_followup_below_120_minutes"], "Reduced false negatives from truncated observation"),
        ("Final eligible sessions", flow["final_eligible_sessions"], "Used for EDA and modelling"),
    ]
    pd.DataFrame(rows, columns=["stage", "records_or_sessions", "action"]).to_csv(output, index=False)


def save_numeric_summary(df: pd.DataFrame, output: Path) -> None:
    """Save a complete descriptive audit for every continuous predictor."""
    rows = []
    total = len(df)
    for feature in CONTINUOUS_PREDICTORS:
        values = pd.to_numeric(df[feature], errors="coerce")
        observed = values.dropna()
        rows.append(
            {
                "feature": feature,
                "display_name": DISPLAY_NAMES.get(feature, feature.replace("_", " ").title()),
                "sessions": total,
                "nonmissing_n": int(observed.size),
                "missing_n": int(values.isna().sum()),
                "missing_pct": float(values.isna().mean() * 100),
                "mean": float(observed.mean()),
                "standard_deviation": float(observed.std()),
                "minimum": float(observed.min()),
                "q1": float(observed.quantile(0.25)),
                "median": float(observed.median()),
                "q3": float(observed.quantile(0.75)),
                "maximum": float(observed.max()),
            }
        )
    pd.DataFrame(rows).to_csv(output, index=False)


def save_outcome_group_summary(df: pd.DataFrame, output: Path) -> None:
    """Save outcome-stratified summaries behind the main EDA comparisons."""
    features = [
        "baseline_sbp",
        "fluid_excess_pct",
        "initial_uf_ml_kg_h",
        "prior_nadir_sbp",
        "prior_idh_rate",
        "age_years",
    ]
    rows = []
    for feature in features:
        for outcome_value, group in df.groupby("idh_absolute", sort=True):
            values = group[feature].dropna()
            rows.append(
                {
                    "feature": feature,
                    "outcome": int(outcome_value),
                    "outcome_label": "BP-defined IDH" if outcome_value else "No BP-defined IDH",
                    "nonmissing_n": int(values.size),
                    "mean": float(values.mean()),
                    "standard_deviation": float(values.std()),
                    "q1": float(values.quantile(0.25)),
                    "median": float(values.median()),
                    "q3": float(values.quantile(0.75)),
                }
            )
    pd.DataFrame(rows).to_csv(output, index=False)


def save_preprocessing_specification(output: Path) -> None:
    rows = [
        ("Numeric predictors", "Median imputation", "Fit inside each training fold", "Robust to skew and prevents validation leakage"),
        ("Categorical predictors", "Most-frequent imputation", "Fit inside each training fold", "Provides a deterministic category for missing values"),
        ("Gender and diabetes", "One-hot encoding", "Unknown categories ignored", "Converts nominal fields without imposing an ordinal scale"),
        ("Linear and PCA numeric inputs", "StandardScaler", "Fit inside each training fold", "Places coefficients and principal components on comparable scales"),
        ("Tree-model numeric inputs", "No scaling", "Original measurement scale retained", "Tree splits do not require standardisation"),
        ("Prior session count", "log1p transformation", "Before model-specific scaling", "Reduces right skew while retaining zero-history sessions"),
        ("EDA relationship plots", "Outcome-blind quantile bins", "Diagnostic only", "Reveals nonlinear associations without becoming a model input"),
        ("Plausible extreme values", "Retained after documented bounds", "IQR flags reported separately", "Avoids deleting clinically possible high-risk observations"),
    ]
    pd.DataFrame(
        rows,
        columns=["input", "transformation", "implementation", "justification"],
    ).to_csv(output, index=False)


def save_feature_engineering_dictionary(output: Path) -> None:
    rows = [
        ("age_years", "session year - birth year", "Age at each treatment session"),
        ("dialysis_vintage_years", "(session date - first dialysis date) / 365.25", "Duration of dialysis exposure"),
        ("fluid_excess_kg", "predialysis weight - prescribed dry weight", "Absolute excess fluid before treatment"),
        ("fluid_excess_pct", "100 x fluid excess / dry weight", "Patient-size-normalized fluid excess"),
        ("initial_uf_ml_kg_h", "1000 x initial UF L/hour / predialysis weight", "Patient-size-normalized initial UF intensity"),
        ("baseline_map", "DBP + (SBP - DBP) / 3", "Mean arterial pressure approximation"),
        ("baseline_pulse_pressure", "SBP - DBP", "Arterial pulse-pressure estimate"),
        ("prior_session_idh", "previous eligible session outcome", "Recent within-patient instability history"),
        ("prior_nadir_sbp", "previous eligible session later nadir SBP", "Previous-session BP tolerance"),
        ("prior_idh_rate", "cumulative earlier IDH events / earlier sessions", "Longitudinal recurrence burden"),
        ("prior_session_count", "number of earlier eligible sessions", "Available history depth; log transformed before modelling"),
    ]
    pd.DataFrame(rows, columns=["engineered_feature", "formula", "rationale"]).to_csv(output, index=False)


def data_dictionary() -> pd.DataFrame:
    rows = [
        ("pid", "string", "Identifier", "De-identified patient identifier", "Grouping and split only; never a predictor"),
        ("session_date", "date", "Date", "Date used to link a dialysis session across source tables", "Identifier and temporal audit"),
        ("index_datetime", "datetime", "Timestamp", "Timestamp of the earliest valid active-dialysis record within 30 minutes", "Index-time documentation"),
        ("index_minute", "numeric", "minutes", "Elapsed dialysis minute at the index record", "Cohort audit; not a predictor"),
        ("baseline_sbp", "numeric", "mmHg", "Systolic BP at the index record", "Predictor"),
        ("baseline_dbp", "numeric", "mmHg", "Diastolic BP at the index record", "Predictor"),
        ("initial_dialysate_temp_c", "numeric", "degrees Celsius", "Dialysate temperature at the index record", "Predictor"),
        ("initial_conductivity_ms_cm", "numeric", "mS/cm", "Dialysate conductivity at the index record", "Predictor"),
        ("initial_uf_l_h", "numeric", "L/hour", "Ultrafiltration rate at the index record", "Predictor"),
        ("initial_blood_flow_ml_min", "numeric", "mL/min", "Blood-flow rate at the index record", "Predictor"),
        ("later_records", "integer", "records", "Number of records after the index measurement", "Outcome-quality audit; not a predictor"),
        ("later_distinct_minutes", "integer", "distinct minutes", "Distinct elapsed-time values after the index measurement", "Eligibility; not a predictor"),
        ("last_observed_minute", "numeric", "minutes", "Latest elapsed dialysis time recorded after index", "Eligibility; not a predictor"),
        ("nadir_sbp", "numeric", "mmHg", "Lowest SBP recorded after index", "Outcome derivation; never a predictor"),
        ("mean_later_sbp", "numeric", "mmHg", "Mean SBP after index", "Outcome description; never a predictor"),
        ("idh_absolute", "binary", "0 or 1", "Later SBP below 90 mmHg", "Primary outcome"),
        ("idh_drop_20", "binary", "0 or 1", "Later SBP at least 20 mmHg below baseline", "Sensitivity outcome"),
        ("idh_flythe", "binary", "0 or 1", "Later nadir below 90 mmHg when baseline is below 160, otherwise below 100", "Sensitivity outcome"),
        ("dialysisstart", "time", "Clock time", "Recorded dialysis start time", "Audit; not a predictor"),
        ("dialysisend", "time", "Clock time", "Recorded dialysis end time", "Post-index field; excluded"),
        ("weightstart", "numeric", "kg", "Body weight before dialysis", "Predictor"),
        ("weightend", "numeric", "kg", "Body weight after dialysis", "Post-index field; excluded"),
        ("dryweight", "numeric", "kg", "Prescribed dry weight", "Predictor"),
        ("temperature", "numeric", "degrees Celsius", "Body temperature recorded for the session", "Predictor"),
        ("gender", "categorical", "F or M", "Recorded sex field in the source data", "Predictor and fairness audit"),
        ("birthday", "integer", "year", "Recorded birth year", "Used to derive age; excluded directly"),
        ("first_dialysis", "date", "Year and month", "Recorded month of first dialysis", "Used to derive vintage"),
        ("DM", "binary", "0 or 1", "Recorded diabetes status", "Predictor and subgroup audit"),
        ("age_years", "numeric", "years", "Session year minus birth year", "Predictor and fairness audit"),
        ("dialysis_vintage_years", "numeric", "years", "Time from first dialysis to session date", "Predictor"),
        ("fluid_excess_kg", "numeric", "kg", "Predialysis weight minus dry weight", "Engineered predictor"),
        ("fluid_excess_pct", "numeric", "percent of dry weight", "Fluid excess divided by dry weight", "Engineered predictor"),
        ("initial_uf_ml_kg_h", "numeric", "mL/kg/hour", "Initial UF rate normalized by predialysis weight", "Engineered predictor"),
        ("baseline_map", "numeric", "mmHg", "DBP plus one-third of pulse pressure", "Engineered predictor"),
        ("baseline_pulse_pressure", "numeric", "mmHg", "Baseline SBP minus DBP", "Engineered predictor"),
        ("session_year", "integer", "year", "Calendar year of the session", "Temporal audit; excluded from model"),
        ("prior_session_idh", "binary", "0 or 1", "Primary outcome in the immediately preceding observed session", "History predictor; earlier sessions only"),
        ("prior_nadir_sbp", "numeric", "mmHg", "Later nadir SBP in the preceding observed session", "History predictor; earlier sessions only"),
        ("prior_session_count", "integer", "sessions", "Number of earlier eligible sessions for the patient", "History predictor; log transformed"),
        ("prior_idh_rate", "numeric", "0 to 1", "Cumulative BP-defined IDH rate across earlier sessions", "History predictor; earlier sessions only"),
    ]
    return pd.DataFrame(rows, columns=["variable", "type", "units_or_values", "definition", "analysis_role"])


def main() -> None:
    root = Path(".")
    artifacts = root / "artifacts"
    docs = root / "docs"
    artifacts.mkdir(exist_ok=True)
    docs.mkdir(exist_ok=True)
    df = pd.read_csv(root / "data/processed/hemobp_session_level.csv.gz", parse_dates=["session_date"])
    flow = json.loads((root / "data/processed/cohort_flow.json").read_text(encoding="utf-8"))

    save_cohort_flow(flow, artifacts / "cohort_flow.png")
    save_outcome_definitions(df, artifacts / "outcome_definition_sensitivity.png")
    save_bp_distributions(df, artifacts / "bp_distributions.png")
    save_subgroup_prevalence(df, artifacts / "subgroup_prevalence.png")
    save_correlation(df, artifacts / "correlation_heatmap.png")
    save_missingness(df, artifacts / "missingness.png")
    save_index_time_distribution(df, artifacts / "index_time_distribution.png")
    save_feature_distributions(df, artifacts / "feature_distributions.png")
    save_binned_relationships(
        df,
        artifacts / "binned_relationships.png",
        artifacts / "binned_relationships.csv",
    )
    save_outlier_summary(
        df,
        artifacts / "outlier_summary.png",
        artifacts / "outlier_summary.csv",
    )
    save_pca_variance(artifacts / "pca_explained_variance.csv", artifacts / "pca_variance.png")
    save_cleaning_audit(flow, artifacts / "cleaning_audit.csv")
    save_numeric_summary(df, artifacts / "numeric_summary.csv")
    save_outcome_group_summary(df, artifacts / "outcome_group_summary.csv")
    save_feature_engineering_dictionary(docs / "feature_engineering_dictionary.csv")
    save_preprocessing_specification(docs / "preprocessing_specification.csv")

    dictionary = data_dictionary()
    dictionary.to_csv(docs / "data_dictionary.csv", index=False)
    columns = list(dictionary.columns)
    markdown = [
        "# DIAL-ALERT Data Dictionary",
        "",
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in dictionary.itertuples(index=False, name=None):
        cells = [str(value).replace("|", "\\|") for value in row]
        markdown.append("| " + " | ".join(cells) + " |")
    (docs / "data_dictionary.md").write_text("\n".join(markdown), encoding="utf-8")
    print(f"Generated {len(dictionary)} dictionary entries and EDA figures")


if __name__ == "__main__":
    main()
