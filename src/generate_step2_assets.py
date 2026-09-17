"""Generate the data audit and dictionary inputs for DIAL ALERT Step 2.

The outputs from this script are machine-readable inputs for the polished
dataset overview report and workbook.  Raw source files are never modified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
ARTIFACTS = ROOT / "artifacts"
DOCS = ROOT / "docs"

BLUE = "#0B5C8E"
TEAL = "#2A9D8F"
ORANGE = "#E07A35"
PURPLE = "#7A5195"
PALE_BLUE = "#EAF3F8"
GRAY = "#5F6B76"


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def _fmt_number(value: float) -> str:
    if pd.isna(value):
        return "not observed"
    if float(value).is_integer():
        return f"{int(value):,}"
    if abs(value) < 1:
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _range_text(series: pd.Series) -> str:
    valid = series.dropna()
    if valid.empty:
        return "not observed"
    return f"{_fmt_number(float(valid.min()))} to {_fmt_number(float(valid.max()))}"


def raw_audit() -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    idp = pd.read_csv(RAW / "idp.csv", dtype={"pid": "string"})
    d1 = pd.read_csv(RAW / "d1.csv", dtype={"pid": "string"})
    raw_frames = {"idp": idp, "d1": d1}

    vip_rows = 0
    vip_missing: pd.Series | None = None
    vip_min: pd.Series | None = None
    vip_max: pd.Series | None = None
    vip_pids: set[str] = set()
    vip_date_min: pd.Timestamp | None = None
    vip_date_max: pd.Timestamp | None = None
    for chunk in pd.read_csv(RAW / "vip.csv", dtype={"pid": "string"}, chunksize=250_000):
        vip_rows += len(chunk)
        missing = chunk.isna().sum()
        vip_missing = missing if vip_missing is None else vip_missing.add(missing, fill_value=0)
        numeric = chunk.select_dtypes(include="number")
        chunk_min = numeric.min()
        chunk_max = numeric.max()
        vip_min = chunk_min if vip_min is None else pd.concat([vip_min, chunk_min], axis=1).min(axis=1)
        vip_max = chunk_max if vip_max is None else pd.concat([vip_max, chunk_max], axis=1).max(axis=1)
        vip_pids.update(chunk["pid"].dropna().astype(str).unique())
        dt = pd.to_datetime(chunk["datatime"], errors="coerce")
        cmin, cmax = dt.min(), dt.max()
        if pd.notna(cmin) and (vip_date_min is None or cmin < vip_date_min):
            vip_date_min = cmin
        if pd.notna(cmax) and (vip_date_max is None or cmax > vip_date_max):
            vip_date_max = cmax

    idp_first = pd.to_datetime(idp["first_dialysis"], errors="coerce")
    d1_dates = pd.to_datetime(d1["keyindate"], errors="coerce")
    d1_keys = pd.DataFrame({"pid": d1["pid"], "session_date": d1_dates.dt.normalize()})

    source_md5 = {
        "idp.csv": "31d269f59bf4acc719f392ad9164d08a",
        "d1.csv": "7db3b48bae2c73e3ecd731dbcd452233",
        "vip.csv": "ff1589610cf7aa3b3e01ba979b6bdc44",
    }
    table_rows = [
        {
            "table": "Idp",
            "file": "idp.csv",
            "grain": "One row per patient",
            "rows": len(idp),
            "columns": len(idp.columns),
            "unique_patients": idp["pid"].nunique(),
            "date_range": f"First dialysis {idp_first.min():%Y-%m} to {idp_first.max():%Y-%m}",
            "missing_cells": int(idp.isna().sum().sum()),
            "duplicate_note": f"{int(idp.duplicated().sum())} exact rows; {int(idp['pid'].duplicated().sum())} duplicate patient IDs",
        },
        {
            "table": "Hemrec D1",
            "file": "d1.csv",
            "grain": "One row per recorded dialysis session",
            "rows": len(d1),
            "columns": len(d1.columns),
            "unique_patients": d1["pid"].nunique(),
            "date_range": f"{d1_dates.min():%Y-%m-%d} to {d1_dates.max():%Y-%m-%d}",
            "missing_cells": int(d1.isna().sum().sum()),
            "duplicate_note": f"{int(d1.duplicated().sum())} exact rows; {int(d1_keys.dropna().duplicated().sum())} duplicate patient-date rows",
        },
        {
            "table": "Hemrec VIP",
            "file": "vip.csv",
            "grain": "One row per time-stamped dialysis monitor state",
            "rows": vip_rows,
            "columns": len(pd.read_csv(RAW / "vip.csv", nrows=0).columns),
            "unique_patients": len(vip_pids),
            "date_range": f"{vip_date_min:%Y-%m-%d %H:%M:%S} to {vip_date_max:%Y-%m-%d %H:%M:%S}",
            "missing_cells": int(vip_missing.sum()),
            "duplicate_note": "Exact duplicates assessed after linkage and plausibility screening",
        },
    ]
    for row in table_rows:
        path = RAW / row["file"]
        observed = _md5(path)
        expected = source_md5[row["file"]]
        row["size_bytes"] = path.stat().st_size
        row["observed_md5"] = observed
        row["source_md5"] = expected
        row["checksum_status"] = "Match" if observed == expected else "Mismatch"

    audit = {
        "tables": table_rows,
        "idp": {
            "missing_n": {k: int(v) for k, v in idp.isna().sum().items()},
            "missing_pct": {k: float(v) for k, v in (idp.isna().mean() * 100).items()},
            "birthday_min": int(idp["birthday"].min()),
            "birthday_max": int(idp["birthday"].max()),
            "first_dialysis_min": idp_first.min().strftime("%Y-%m"),
            "first_dialysis_max": idp_first.max().strftime("%Y-%m"),
            "gender_counts": {str(k): int(v) for k, v in idp["gender"].value_counts().items()},
            "dm_counts": {str(k): int(v) for k, v in idp["DM"].value_counts().items()},
        },
        "d1": {
            "missing_n": {k: int(v) for k, v in d1.isna().sum().items()},
            "missing_pct": {k: float(v) for k, v in (d1.isna().mean() * 100).items()},
            "numeric_min": {k: _json_value(v) for k, v in d1.select_dtypes(include="number").min().items()},
            "numeric_max": {k: _json_value(v) for k, v in d1.select_dtypes(include="number").max().items()},
        },
        "vip": {
            "rows": vip_rows,
            "missing_n": {k: int(v) for k, v in vip_missing.items()},
            "missing_pct": {k: float(v / vip_rows * 100) for k, v in vip_missing.items()},
            "numeric_min": {k: _json_value(v) for k, v in vip_min.items()},
            "numeric_max": {k: _json_value(v) for k, v in vip_max.items()},
            "date_min": vip_date_min.isoformat(),
            "date_max": vip_date_max.isoformat(),
        },
    }
    return audit, raw_frames


RAW_DEFINITIONS = {
    ("Idp", "pid"): ("string", "none", "De-identified patient identifier", "Primary patient key"),
    ("Idp", "gender"): ("categorical", "none", "Recorded sex field", "Patient characteristic and fairness attribute"),
    ("Idp", "birthday"): ("integer", "year", "Recorded birth year", "Source for age derivation"),
    ("Idp", "first_dialysis"): ("date", "year-month", "Month of first hemodialysis treatment", "Source for dialysis vintage"),
    ("Idp", "DM"): ("binary", "0 or 1", "Recorded diabetes status", "Patient characteristic"),
    ("Hemrec D1", "pid"): ("string", "none", "De-identified patient identifier", "Patient linkage key"),
    ("Hemrec D1", "keyindate"): ("datetime", "timestamp", "Date and time used to identify the dialysis session", "Session linkage key"),
    ("Hemrec D1", "dialysisstart"): ("time", "HH:MM", "Recorded dialysis start clock time", "Session audit field"),
    ("Hemrec D1", "dialysisend"): ("time", "HH:MM", "Recorded dialysis end clock time", "Post-session audit field"),
    ("Hemrec D1", "weightstart"): ("numeric", "kg", "Body weight before dialysis", "Baseline predictor source"),
    ("Hemrec D1", "weightend"): ("numeric", "kg", "Body weight after dialysis", "Post-session field"),
    ("Hemrec D1", "dryweight"): ("numeric", "kg", "Prescribed dry weight", "Baseline predictor source"),
    ("Hemrec D1", "temperature"): ("numeric", "degrees Celsius", "Body temperature recorded for the session", "Baseline predictor source"),
    ("Hemrec VIP", "pid"): ("string", "none", "De-identified patient identifier", "Patient linkage key"),
    ("Hemrec VIP", "datatime"): ("datetime", "timestamp", "Timestamp of the monitor record", "Patient-date linkage and ordering"),
    ("Hemrec VIP", "measuretime"): ("integer", "source-defined index", "Blood-pressure measurement index as stored", "Ordering audit; source unit not documented"),
    ("Hemrec VIP", "sbp"): ("numeric", "mmHg", "Systolic blood pressure", "Index predictor and later outcome source"),
    ("Hemrec VIP", "dbp"): ("numeric", "mmHg", "Diastolic blood pressure", "Index predictor source"),
    ("Hemrec VIP", "dia_temp_value"): ("numeric", "degrees Celsius", "Dialysate temperature setting", "Index predictor source"),
    ("Hemrec VIP", "conductivity"): ("numeric", "mS/cm", "Dialysate conductivity, a proxy for dialysate sodium concentration", "Index predictor source"),
    ("Hemrec VIP", "uf"): ("numeric", "L/hour", "Ultrafiltration rate", "Index predictor source"),
    ("Hemrec VIP", "blood_flow"): ("numeric", "mL/min", "Blood-flow rate through the extracorporeal circuit", "Index predictor source"),
    ("Hemrec VIP", "time"): ("numeric", "minutes", "Elapsed dialysis time", "Index selection and later outcome window"),
}


ANALYTIC_PROVENANCE = {
    "pid": ("Idp", "Identifier only"),
    "session_date": ("Hemrec D1 and Hemrec VIP", "Audit only"),
    "index_datetime": ("Hemrec VIP", "Audit only"),
    "index_minute": ("Hemrec VIP", "Audit only"),
    "baseline_sbp": ("Hemrec VIP index record", "Known at index"),
    "baseline_dbp": ("Hemrec VIP index record", "Known at index"),
    "initial_dialysate_temp_c": ("Hemrec VIP index record", "Known at index"),
    "initial_conductivity_ms_cm": ("Hemrec VIP index record", "Known at index"),
    "initial_uf_l_h": ("Hemrec VIP index record", "Known at index"),
    "initial_blood_flow_ml_min": ("Hemrec VIP index record", "Known at index"),
    "later_records": ("Hemrec VIP after index", "Post-index audit only"),
    "later_distinct_minutes": ("Hemrec VIP after index", "Post-index eligibility only"),
    "last_observed_minute": ("Hemrec VIP after index", "Post-index eligibility only"),
    "nadir_sbp": ("Hemrec VIP after index", "Post-index outcome derivation only"),
    "mean_later_sbp": ("Hemrec VIP after index", "Post-index outcome description only"),
    "idh_absolute": ("Derived from Hemrec VIP after index", "Primary outcome"),
    "idh_drop_20": ("Derived from Hemrec VIP after index", "Sensitivity outcome"),
    "idh_flythe": ("Derived from Hemrec VIP after index", "Sensitivity outcome"),
    "dialysisstart": ("Hemrec D1", "Audit only"),
    "dialysisend": ("Hemrec D1", "Post-index field; excluded"),
    "weightstart": ("Hemrec D1", "Known before treatment"),
    "weightend": ("Hemrec D1", "Post-treatment field; excluded"),
    "dryweight": ("Hemrec D1", "Known before treatment"),
    "temperature": ("Hemrec D1", "Known at session start"),
    "gender": ("Idp", "Known before treatment"),
    "birthday": ("Idp", "Source only; replaced by age"),
    "first_dialysis": ("Idp", "Source only; replaced by vintage"),
    "DM": ("Idp", "Known before treatment"),
    "age_years": ("Derived from session date and birth year", "Known before treatment"),
    "dialysis_vintage_years": ("Derived from session date and first dialysis", "Known before treatment"),
    "fluid_excess_kg": ("Derived from predialysis and dry weight", "Known before treatment"),
    "fluid_excess_pct": ("Derived from predialysis and dry weight", "Known before treatment"),
    "initial_uf_ml_kg_h": ("Derived from index UF rate and predialysis weight", "Known at index"),
    "baseline_map": ("Derived from index SBP and DBP", "Known at index"),
    "baseline_pulse_pressure": ("Derived from index SBP and DBP", "Known at index"),
    "session_year": ("Derived from session date", "Temporal audit only"),
    "prior_session_idh": ("Derived from earlier eligible sessions", "Prior sessions only"),
    "prior_nadir_sbp": ("Derived from earlier eligible sessions", "Prior sessions only"),
    "prior_session_count": ("Derived from earlier eligible sessions", "Prior sessions only"),
    "prior_idh_rate": ("Derived from earlier eligible sessions", "Prior sessions only"),
}


def _raw_observed(table: str, variable: str, audit: dict[str, Any], frames: dict[str, pd.DataFrame]) -> str:
    if table == "Idp":
        series = frames["idp"][variable]
        if variable == "pid":
            return "1,072 unique de-identified IDs"
        if variable == "gender":
            return "F or M"
        if variable == "DM":
            return "0 = no diabetes; 1 = diabetes"
        if variable == "birthday":
            return f"{int(series.min())} to {int(series.max())}"
        if variable == "first_dialysis":
            return f"{audit['idp']['first_dialysis_min']} to {audit['idp']['first_dialysis_max']}"
    if table == "Hemrec D1":
        series = frames["d1"][variable]
        if variable == "pid":
            return "1,072 unique de-identified IDs"
        if variable == "keyindate":
            return "2013-06-01 to 2018-05-31"
        if variable in {"dialysisstart", "dialysisend"}:
            return "24-hour clock time as stored"
        return _range_text(series)
    if table == "Hemrec VIP":
        if variable == "pid":
            return "1,072 unique de-identified IDs"
        if variable == "datatime":
            return "2013-06-01 14:56:40 to 2018-07-01 06:22:57"
        return f"{_fmt_number(audit['vip']['numeric_min'][variable])} to {_fmt_number(audit['vip']['numeric_max'][variable])}"
    return ""


def build_dictionary(audit: dict[str, Any], frames: dict[str, pd.DataFrame], analytic: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_frame_key = {"Idp": "idp", "Hemrec D1": "d1", "Hemrec VIP": "vip"}
    for (table, variable), (dtype, unit, definition, role) in RAW_DEFINITIONS.items():
        key = source_frame_key[table]
        if key in frames:
            missing_n = int(frames[key][variable].isna().sum())
            missing_pct = float(frames[key][variable].isna().mean() * 100)
        else:
            missing_n = int(audit["vip"]["missing_n"][variable])
            missing_pct = float(audit["vip"]["missing_pct"][variable])
        rows.append(
            {
                "dataset_layer": "Raw source",
                "table": table,
                "variable": variable,
                "data_type": dtype,
                "unit": unit,
                "allowed_or_observed_values": _raw_observed(table, variable, audit, frames),
                "missing_n": missing_n,
                "missing_pct": missing_pct,
                "definition": definition,
                "provenance": "Original public HEMOBP field",
                "analysis_role": role,
                "prediction_availability": "Depends on measurement timing",
                "quality_notes": "Source value retained; raw files are not overwritten",
            }
        )

    base = pd.read_csv(DOCS / "data_dictionary.csv")
    for record in base.to_dict("records"):
        variable = record["variable"]
        series = analytic[variable]
        dtype = record["type"]
        if variable == "pid":
            observed = f"{analytic['pid'].nunique():,} unique IDs in the analytic cohort"
        elif variable == "gender":
            observed = "F or M"
        elif variable == "DM":
            observed = "0 = no diabetes; 1 = diabetes"
        elif dtype == "binary":
            observed = "0 = no; 1 = yes"
        elif dtype == "date":
            parsed = pd.to_datetime(series, errors="coerce")
            observed = f"{parsed.min():%Y-%m-%d} to {parsed.max():%Y-%m-%d}"
        elif dtype == "datetime":
            parsed = pd.to_datetime(series, errors="coerce")
            observed = f"{parsed.min():%Y-%m-%d %H:%M:%S} to {parsed.max():%Y-%m-%d %H:%M:%S}"
        elif dtype == "time":
            observed = "24-hour clock time as stored"
        elif pd.api.types.is_numeric_dtype(series):
            observed = _range_text(series)
        else:
            observed = "; ".join(sorted(series.dropna().astype(str).unique())[:12])
        source, availability = ANALYTIC_PROVENANCE[variable]
        quality = "No missing values in the eligible table"
        if series.isna().any():
            quality = "Missing values arise from unavailable dialysis history or invalid first-dialysis chronology"
        if variable in {"nadir_sbp", "mean_later_sbp", "idh_absolute", "idh_drop_20", "idh_flythe", "weightend", "dialysisend"}:
            quality = "Excluded from predictors to prevent post-index leakage"
        if variable in {"fluid_excess_kg", "fluid_excess_pct", "initial_uf_ml_kg_h"}:
            quality = "Plausible but extreme values are retained and flagged for sensitivity analysis"
        rows.append(
            {
                "dataset_layer": "Analytic session table",
                "table": "hemobp_session_level",
                "variable": variable,
                "data_type": dtype,
                "unit": record["units_or_values"],
                "allowed_or_observed_values": observed,
                "missing_n": int(series.isna().sum()),
                "missing_pct": float(series.isna().mean() * 100),
                "definition": record["definition"],
                "provenance": source,
                "analysis_role": record["analysis_role"],
                "prediction_availability": availability,
                "quality_notes": quality,
            }
        )
    return rows


def save_architecture(output: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    nodes = [
        (0.30, 1.30, 2.65, 1.90, BLUE, "Idp", "Patient level\n1,072 rows\n5 variables"),
        (3.85, 1.30, 2.65, 1.90, TEAL, "Hemrec D1", "Session level\n165,986 rows\n8 variables"),
        (7.40, 1.30, 2.65, 1.90, ORANGE, "Hemrec VIP", "Monitor level\n4,366,298 rows\n10 variables"),
        (10.95, 1.30, 2.75, 1.90, PURPLE, "Analytic table", "Eligible session level\n106,758 rows\n40 variables"),
    ]
    for x, y, w, h, color, title, detail in nodes:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.09", fc="white", ec=color, lw=2.2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + 1.28, title, ha="center", va="center", fontsize=14, fontweight="bold", color=color)
        ax.text(x + w / 2, y + 0.62, detail, ha="center", va="center", fontsize=10.5, color=GRAY, linespacing=1.35)
    for start, end, label in [
        ((2.95, 2.25), (3.85, 2.25), "patient key"),
        ((6.50, 2.25), (7.40, 2.25), "patient and date"),
        ((10.05, 2.25), (10.95, 2.25), "eligibility rules"),
    ]:
        arrow = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, lw=1.8, color=GRAY)
        ax.add_patch(arrow)
        ax.text((start[0] + end[0]) / 2, 0.93, label, ha="center", fontsize=8.6, color=GRAY)
    ax.text(0.30, 4.05, "HEMOBP source tables and DIAL ALERT analytic unit", fontsize=17, fontweight="bold", color="#111827")
    ax.text(0.30, 3.68, "Repeated monitor records are reduced to one leakage-controlled row per eligible dialysis session.", fontsize=10.5, color=GRAY)
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    audit, frames = raw_audit()
    analytic = pd.read_csv(PROCESSED / "hemobp_session_level.csv.gz", low_memory=False)
    flow = json.loads((PROCESSED / "cohort_flow.json").read_text(encoding="utf-8"))
    outliers = pd.read_csv(ARTIFACTS / "outlier_summary.csv")

    analytic_missing = (
        pd.DataFrame(
            {
                "variable": analytic.columns,
                "missing_n": analytic.isna().sum().values,
                "missing_pct": (analytic.isna().mean() * 100).values,
            }
        )
        .sort_values(["missing_pct", "variable"], ascending=[False, True])
        .to_dict("records")
    )
    audit["analytic"] = {
        "rows": len(analytic),
        "columns": len(analytic.columns),
        "unique_patients": int(analytic["pid"].nunique()),
        "date_min": str(pd.to_datetime(analytic["session_date"]).min().date()),
        "date_max": str(pd.to_datetime(analytic["session_date"]).max().date()),
        "missing": analytic_missing,
        "complete_columns": int((analytic.isna().sum() == 0).sum()),
        "outcome_events": int(analytic["idh_absolute"].sum()),
        "outcome_prevalence": float(analytic["idh_absolute"].mean()),
        "drop20_events": int(analytic["idh_drop_20"].sum()),
        "drop20_prevalence": float(analytic["idh_drop_20"].mean()),
        "flythe_events": int(analytic["idh_flythe"].sum()),
        "flythe_prevalence": float(analytic["idh_flythe"].mean()),
        "index_at_zero_n": int((analytic["index_minute"] == 0).sum()),
        "index_at_zero_pct": float((analytic["index_minute"] == 0).mean() * 100),
        "index_by_five_pct": float((analytic["index_minute"] <= 5).mean() * 100),
    }
    audit["cohort_flow"] = flow
    audit["outliers"] = outliers.to_dict("records")
    audit["source_discrepancy"] = {
        "published_patients": 1075,
        "public_file_patient_rows": 1072,
        "difference": 3,
        "handling": "All reported analyses use the actual public file contents; the difference is disclosed rather than reconciled by invention.",
    }
    audit["sources"] = [
        {
            "citation": "Lin CJ, Chen YY, Pan CF, Wu V, Wu CJ. Dataset supporting blood pressure prediction for the management of chronic hemodialysis. Scientific Data. 2019;6:313.",
            "doi": "https://doi.org/10.1038/s41597-019-0319-8",
        },
        {
            "citation": "Chien CY. HEMOBP. Figshare. Version 3. Dataset. 2019.",
            "doi": "https://doi.org/10.6084/m9.figshare.6260654.v3",
            "license": "CC BY 4.0",
        },
    ]

    dictionary = build_dictionary(audit, frames, analytic)
    (ARTIFACTS / "step2_dataset_audit.json").write_text(json.dumps(audit, indent=2, default=_json_value), encoding="utf-8")
    (ARTIFACTS / "step2_dictionary_rows.json").write_text(json.dumps(dictionary, indent=2, default=_json_value), encoding="utf-8")
    save_architecture(ARTIFACTS / "data_architecture.png")
    print(f"Wrote Step 2 audit with {len(dictionary)} dictionary rows")


if __name__ == "__main__":
    main()
