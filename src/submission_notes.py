"""Shared submission clarifications; no changes to fitted models or outcomes."""
ELIGIBILITY_NOTE = (
    "Eligibility requires at least two distinct later measurement minutes and an observation "
    "at or beyond elapsed dialysis minute 120. This is not a requirement for 120 minutes "
    "after prediction. The index observation is the earliest valid active-dialysis reading "
    "within minutes 0 to 30. Future observation requirements define the retrospective "
    "evaluation cohort and cannot be confirmed when a new session first receives a score."
)
SELECTION_NOTE = (
    "The split search considers 100 seeds to balance patient-fold session counts and outcome "
    "prevalence, without using model performance. Among eligible candidates, models within "
    "0.01 of the best grouped-CV average precision are ordered by validation Brier score. "
    "The dummy baseline and PCA benchmark are excluded from the final selection pool. "
    "PCA was evaluated at 85% and 95% variance thresholds; 85% was selected. "
    "Calibration and threshold choices use validation patients. The final model uses no "
    "additional calibration. Lower raw Brier score does not establish superiority over "
    "every alternatively calibrated competitor."
)
ALERT_NOTE = (
    "At the fixed threshold 0.1428558780 (rounded to 0.143), 3,918 of 21,354 test sessions "
    "are flagged (18.35%). Sensitivity is 66.1%, precision 30.6%, and false alerts are "
    "12.73 per 100 total sessions. Separately, ranking the highest-risk 20% selects 4,271 "
    "sessions, captures 69.1% of events, has precision 29.4%, and produces 14.13 false "
    "alerts per 100 sessions. Ranking requires a defined batch and tie rule before local "
    "use; retrospective whole-test-set ranking is not an implemented live scheduling rule."
)
PILOT_NOTE = (
    "The following are proposed feasibility targets drafted after the retrospective study, "
    "not original success criteria, observed achievements, or approved clinical standards. "
    "Before collecting pilot outcomes, local clinical and operational leads must agree "
    "the strategy, sample size, confidence-interval requirements, and stop rules. A proposed "
    "fixed-threshold silent evaluation seeks sensitivity at least 65%, at most 20 alerts "
    "and 15 false alerts per 100 sessions. Timed simulated reviews seek median active "
    "review time at most 2 minutes per alert and total active review time at most 40 minutes "
    "per 100 sessions. Median review time alone does not determine total workload. Report uncertainty and all failures. These illustrative "
    "targets assess feasibility only and do not establish patient benefit or safety."
)
REPRO_NOTE = (
    "The public release includes the selected predictor, threshold, metrics, and configuration. "
    "Candidate models, patient-level split assignments, and source data are regenerated locally. "
    "A fresh Python 3.12 environment installed the pinned dependencies and passed saved-model "
    "inference and repository tests. Source-data acquisition returned HTTP 403, so complete "
    "raw-data-to-training reproduction was not completed in this verification. See "
    "docs/reproducibility_record.md for commands and evidence."
)
def append_submission_notes(doc):
    doc.add_page_break()
    doc.add_heading("Evaluation Definitions and Operating Strategies", level=1)
    for heading, text in [("Eligibility",ELIGIBILITY_NOTE),("Model selection",SELECTION_NOTE),("Operating strategies",ALERT_NOTE)]:
        doc.add_heading(heading,level=2)
        doc.add_paragraph(text)
    doc.add_page_break()
    doc.add_heading("Proposed Pilot Targets and Reproduction Status",level=1)
    doc.add_heading("Future feasibility targets",level=2)
    doc.add_paragraph(PILOT_NOTE)
    doc.add_heading("Reproduction status",level=2)
    doc.add_paragraph(REPRO_NOTE)
    doc.add_heading("Optional deliverables",level=2)
    doc.add_paragraph("The published repository supports command-line model inference. A complete Step 8 web-app deployment package is not included in this release. Step 9 demonstrates saved AI-assisted text with source-linked numeric validation and a replay demo. It does not demonstrate live LLM generation. Separately prepared apps or recordings require separate verification before inclusion. Investigator review of the Step 9 narrative remains pending.")
