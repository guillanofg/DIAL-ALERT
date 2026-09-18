from __future__ import annotations

import csv
import json
import re
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.splitlines())


def test_patient_level_files_are_not_tracked() -> None:
    tracked = tracked_files()
    prohibited = {
        "artifacts/split_assignments.csv.gz",
        "artifacts/step5_approximate_shap_values.csv",
        "artifacts/step5_shap_local_high_risk.csv",
        "artifacts/step5_lime_local_high_risk.csv",
        "data/processed/hemobp_session_level.csv.gz",
        "data/raw/d1.csv",
        "data/raw/idp.csv",
        "data/raw/vip.csv",
    }
    assert tracked.isdisjoint(prohibited)

    forbidden_columns = {"pid", "patient_id", "session_date", "index_datetime"}
    for relative in sorted(path for path in tracked if path.startswith("artifacts/") and path.endswith(".csv")):
        with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
            header = set(next(csv.reader(handle), []))
        assert header.isdisjoint(forbidden_columns), relative


def test_detailed_audit_intermediates_are_not_tracked() -> None:
    tracked = tracked_files()
    excluded = {
        "artifacts/step2_dataset_audit.json",
        "artifacts/step2_dictionary_rows.json",
        "artifacts/step5_group_metrics.csv",
        "artifacts/step5_intersectional_metrics.csv",
        "artifacts/step5_original_model_sex_metrics.csv",
        "artifacts/step5_patient_weighted_group_metrics.csv",
        "artifacts/step5_sex_outcome_reweighting_sex_metrics.csv",
        "artifacts/step5_sex_specific_thresholds_sex_metrics.csv",
        "artifacts/step5_synthetic_case.json",
        "artifacts/subgroup_prevalence.csv",
    }
    assert tracked.isdisjoint(excluded)


def test_local_explanations_are_declared_synthetic() -> None:
    specification = json.loads(
        (ROOT / "artifacts/step5_lime_local_metadata.json").read_text(encoding="utf-8")
    )
    assert specification["scenario_type"] == "synthetic"
    assert specification["not_a_patient_record"] is True


def test_no_conversation_or_assistant_tooling_markers_are_tracked() -> None:
    markers = (
        "chat" + "gpt",
        "open" + "ai",
        "co" + "dex",
        "begin additional" + " message",
        "system" + " prompt",
        "conversation" + " transcript",
    )
    text_suffixes = {".cff", ".csv", ".json", ".md", ".mjs", ".py", ".toml", ".txt", ".yaml", ".yml"}
    for relative in sorted(tracked_files()):
        path = ROOT / relative
        if path.suffix.lower() not in text_suffixes and path.name not in {"Makefile", "LICENSE"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for marker in markers:
            assert marker not in text, f"{marker!r} found in {relative}"


def test_no_credential_shaped_tokens_are_tracked() -> None:
    patterns = {
        "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "GitHub token": re.compile(r"\b(?:gh[opurs]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
        ("Open" + "AI-style token"): re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    }
    text_suffixes = {".cff", ".csv", ".json", ".md", ".mjs", ".py", ".toml", ".txt", ".yaml", ".yml"}
    for relative in sorted(tracked_files()):
        path = ROOT / relative
        if path.suffix.lower() not in text_suffixes and path.name not in {"Makefile", "LICENSE"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in patterns.items():
            assert pattern.search(text) is None, f"{label} found in {relative}"


def test_office_packages_have_no_assistant_or_exporter_identity() -> None:
    prohibited = (
        ("Walnut" + " Exporter"),
        ("Chat" + "GPT"),
        ("Open" + "AI"),
        ("begin additional" + " message"),
        ("system" + " prompt"),
    )
    office_paths = sorted((ROOT / "reports").glob("*.docx"))
    office_paths.extend(sorted((ROOT / "reports").glob("*.pptx")))
    office_paths.extend(sorted((ROOT / "reports").glob("*.xlsx")))
    for path in office_paths:
        with zipfile.ZipFile(path) as archive:
            package_xml = "\n".join(
                archive.read(name).decode("utf-8", errors="replace")
                for name in archive.namelist()
                if name.endswith((".xml", ".rels"))
            )
        for marker in prohibited:
            assert marker not in package_xml, f"{marker!r} found in {path.name}"
        if path.suffix.lower() == ".pptx":
            assert "Franklin B. Guillano" in package_xml

