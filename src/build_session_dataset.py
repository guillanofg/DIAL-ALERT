"""Build the leakage-controlled, session-level DIAL-ALERT modelling table.

The raw HEMOBP VIP table contains repeated measurements within dialysis
sessions. This script links those records to session and patient tables,
chooses an index measurement during the first 30 minutes of active dialysis,
and derives outcomes only from later measurements.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


KEY = ["pid", "session_date"]


def _read_raw(raw_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    idp = pd.read_csv(
        raw_dir / "idp.csv",
        dtype={"pid": "string", "gender": "string", "DM": "Int8"},
    )
    idp["first_dialysis"] = pd.to_datetime(idp["first_dialysis"], errors="coerce")

    d1 = pd.read_csv(
        raw_dir / "d1.csv",
        dtype={"pid": "string"},
        parse_dates=["keyindate"],
    )
    d1["session_date"] = d1["keyindate"].dt.normalize()

    vip = pd.read_csv(
        raw_dir / "vip.csv",
        dtype={
            "pid": "string",
            "measuretime": "float32",
            "sbp": "float32",
            "dbp": "float32",
            "dia_temp_value": "float32",
            "conductivity": "float32",
            "uf": "float32",
            "blood_flow": "float32",
            "time": "float32",
        },
        parse_dates=["datatime"],
    )
    vip["session_date"] = vip["datatime"].dt.normalize()
    return idp, d1, vip


def build_dataset(raw_dir: Path, output_dir: Path) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    idp, d1, vip = _read_raw(raw_dir)

    flow: dict[str, int | float | str] = {
        "patient_rows": int(len(idp)),
        "d1_rows": int(len(d1)),
        "vip_rows": int(len(vip)),
    }

    # One row per patient-day is retained after removing unusable dates and
    # applying a stable chronological de-duplication rule.
    flow["d1_missing_date_rows_removed"] = int(d1["session_date"].isna().sum())
    d1_dated = d1.dropna(subset=["session_date"])
    d1_valid = (
        d1_dated
        .sort_values(KEY + ["keyindate"], kind="stable")
        .drop_duplicates(KEY, keep="first")
    )
    flow["d1_duplicate_patient_day_rows_removed"] = int(len(d1_dated) - len(d1_valid))
    flow["d1_valid_unique_patient_days"] = int(len(d1_valid))

    vip = vip.merge(d1_valid[KEY], on=KEY, how="inner", validate="many_to_one")
    flow["vip_rows_linked_to_d1"] = int(len(vip))
    flow["linked_patient_days"] = int(vip[KEY].drop_duplicates().shape[0])

    # Source-supported physiologic and elapsed-time bounds define the accepted
    # monitoring envelope. Counts are retained even when no rows are excluded.
    before_bounds = len(vip)
    vip = vip.loc[
        vip["sbp"].between(31, 200)
        & vip["dbp"].between(30, 192)
        & vip["time"].between(0, 370)
    ].copy()
    flow["vip_rows_outside_documented_bounds_removed"] = int(before_bounds - len(vip))
    flow["vip_rows_after_documented_bounds"] = int(len(vip))

    # Exact duplicate rows can arise when the gateway emits the same state
    # repeatedly. Removing only exact duplicates preserves true repeat readings.
    duplicate_columns = [
        "pid",
        "session_date",
        "datatime",
        "measuretime",
        "sbp",
        "dbp",
        "dia_temp_value",
        "conductivity",
        "uf",
        "blood_flow",
        "time",
    ]
    before = len(vip)
    vip = vip.drop_duplicates(duplicate_columns)
    flow["exact_vip_duplicates_removed"] = int(before - len(vip))

    vip = vip.sort_values(KEY + ["time", "datatime", "measuretime"], kind="stable")

    # The index record is the earliest valid BP reading during active dialysis
    # in the first 30 minutes. Later observations alone define the outcome.
    candidates = vip.loc[
        vip["time"].between(0, 30)
        & (vip["blood_flow"] > 0)
        & vip["sbp"].between(60, 200)
        & vip["dbp"].between(30, 150)
    ]
    index = candidates.drop_duplicates(KEY, keep="first").copy()
    flow["patient_days_with_index_record"] = int(len(index))

    index = index.rename(
        columns={
            "datatime": "index_datetime",
            "time": "index_minute",
            "sbp": "baseline_sbp",
            "dbp": "baseline_dbp",
            "dia_temp_value": "initial_dialysate_temp_c",
            "conductivity": "initial_conductivity_ms_cm",
            "uf": "initial_uf_l_h",
            "blood_flow": "initial_blood_flow_ml_min",
        }
    )

    indexed_vip = vip.merge(
        index[KEY + ["index_minute", "baseline_sbp"]],
        on=KEY,
        how="inner",
        validate="many_to_one",
    )
    future = indexed_vip.loc[indexed_vip["time"] > indexed_vip["index_minute"]].copy()
    future["is_idh_absolute"] = future["sbp"] < 90
    future["is_drop_20"] = future["sbp"] <= (future["baseline_sbp"] - 20)
    future["is_flythe_nadir"] = np.where(
        future["baseline_sbp"] < 160,
        future["sbp"] < 90,
        future["sbp"] < 100,
    )

    outcomes = (
        future.groupby(KEY, sort=False)
        .agg(
            later_records=("sbp", "size"),
            later_distinct_minutes=("time", "nunique"),
            last_observed_minute=("time", "max"),
            nadir_sbp=("sbp", "min"),
            mean_later_sbp=("sbp", "mean"),
            idh_absolute=("is_idh_absolute", "max"),
            idh_drop_20=("is_drop_20", "max"),
            idh_flythe=("is_flythe_nadir", "max"),
        )
        .reset_index()
    )

    sessions = (
        index[
            KEY
            + [
                "index_datetime",
                "index_minute",
                "baseline_sbp",
                "baseline_dbp",
                "initial_dialysate_temp_c",
                "initial_conductivity_ms_cm",
                "initial_uf_l_h",
                "initial_blood_flow_ml_min",
            ]
        ]
        .merge(outcomes, on=KEY, how="inner", validate="one_to_one")
        .merge(
            d1_valid[
                KEY
                + [
                    "dialysisstart",
                    "dialysisend",
                    "weightstart",
                    "weightend",
                    "dryweight",
                    "temperature",
                ]
            ],
            on=KEY,
            how="left",
            validate="one_to_one",
        )
        .merge(idp, on="pid", how="left", validate="many_to_one")
    )
    flow["sessions_with_post_index_records"] = int(len(sessions))

    # Adequate follow-up reduces false negatives caused by truncated sessions.
    # IMPORTANT: the 120-minute rule is anchored to dialysis elapsed time:
    # last_observed_minute >= 120. It does NOT require 120 minutes of follow-up
    # after the index/prediction observation, which can occur during minutes 0-30.
    baseline_eligible = sessions.loc[sessions["baseline_sbp"] >= 90].copy()
    flow["sessions_removed_baseline_sbp_below_90"] = int(len(sessions) - len(baseline_eligible))
    minute_eligible = baseline_eligible.loc[baseline_eligible["later_distinct_minutes"] >= 2].copy()
    flow["sessions_removed_insufficient_later_minutes"] = int(
        len(baseline_eligible) - len(minute_eligible)
    )
    sessions = minute_eligible.loc[minute_eligible["last_observed_minute"] >= 120].copy()
    flow["sessions_removed_followup_below_120_minutes"] = int(
        len(minute_eligible) - len(sessions)
    )
    flow["final_eligible_sessions"] = int(len(sessions))

    sessions["age_years"] = sessions["session_date"].dt.year - sessions["birthday"]
    sessions["dialysis_vintage_years"] = (
        sessions["session_date"] - sessions["first_dialysis"]
    ).dt.days / 365.25
    sessions.loc[sessions["dialysis_vintage_years"] < 0, "dialysis_vintage_years"] = np.nan
    sessions["fluid_excess_kg"] = sessions["weightstart"] - sessions["dryweight"]
    sessions["fluid_excess_pct"] = 100 * sessions["fluid_excess_kg"] / sessions["dryweight"]
    sessions["initial_uf_ml_kg_h"] = (
        1000 * sessions["initial_uf_l_h"] / sessions["weightstart"]
    )
    sessions["baseline_map"] = (
        sessions["baseline_dbp"]
        + (sessions["baseline_sbp"] - sessions["baseline_dbp"]) / 3
    )
    sessions["baseline_pulse_pressure"] = sessions["baseline_sbp"] - sessions["baseline_dbp"]
    sessions["session_year"] = sessions["session_date"].dt.year

    # History features use only earlier sessions for the same patient.
    sessions = sessions.sort_values(["pid", "session_date", "index_datetime"], kind="stable")
    grouped = sessions.groupby("pid", sort=False)
    sessions["prior_session_idh"] = grouped["idh_absolute"].shift(1)
    sessions["prior_nadir_sbp"] = grouped["nadir_sbp"].shift(1)
    sessions["prior_session_count"] = grouped.cumcount()
    prior_events = grouped["idh_absolute"].cumsum() - sessions["idh_absolute"].astype(int)
    sessions["prior_idh_rate"] = prior_events / sessions["prior_session_count"].replace(0, np.nan)

    # Outcome and audit fields remain in the processed table but are excluded
    # from the model feature list by the modelling configuration.
    sessions["idh_absolute"] = sessions["idh_absolute"].astype("int8")
    sessions["idh_drop_20"] = sessions["idh_drop_20"].astype("int8")
    sessions["idh_flythe"] = sessions["idh_flythe"].astype("int8")

    flow["primary_idh_events"] = int(sessions["idh_absolute"].sum())
    flow["primary_idh_prevalence"] = float(sessions["idh_absolute"].mean())
    flow["drop_20_events"] = int(sessions["idh_drop_20"].sum())
    flow["flythe_events"] = int(sessions["idh_flythe"].sum())
    flow["unique_patients_final"] = int(sessions["pid"].nunique())

    out_csv = output_dir / "hemobp_session_level.csv.gz"
    sessions.to_csv(out_csv, index=False, compression="gzip")
    with (output_dir / "cohort_flow.json").open("w", encoding="utf-8") as handle:
        json.dump(flow, handle, indent=2)

    print(json.dumps(flow, indent=2))
    print(f"Wrote {out_csv} with shape {sessions.shape}")
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    build_dataset(args.raw_dir, args.output_dir)


if __name__ == "__main__":
    main()
