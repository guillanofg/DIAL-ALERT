# Contributing to DIAL ALERT

Thank you for helping improve this academic project. Contributions should preserve the project's patient-level validation, prediction-time boundary, reproducibility, and safety constraints.

## Development workflow

1. Create a focused branch from the current main branch.
2. Install the pinned dependencies with `python -m pip install -r requirements.txt`.
3. Add or update tests for any changed behavior.
4. Run `pytest -q` before opening a pull request.
5. Explain the scientific reason for a modelling change and report its effect on average precision, calibration, alert workload, and subgroup performance.

## Data and privacy

Do not commit raw or processed patient-level data. Use `python src/download_data.py` to obtain the public HEMOBP files directly from Figshare. Do not add names, medical-record numbers, free text, or any other identifying information.

## Clinical safety

DIAL-ALERT is an academic prototype, not a medical device. Contributions must not describe the output as a diagnosis, treatment instruction, or substitute for clinician judgment. External and prospective validation is required before any clinical use.

## Reporting issues

Use a GitHub issue for reproducible bugs, documentation gaps, or proposed analyses. For a security or privacy concern, avoid posting sensitive details publicly and contact the repository owner through GitHub.

