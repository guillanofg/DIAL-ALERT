# Evaluation definitions and proposed pilot targets

## Prediction and eligibility

Primary outcome: any later observed SBP below 90 mmHg in an eligible session.

Eligibility requires at least two distinct later measurement minutes and an observation at or beyond elapsed dialysis minute 120. This is not a requirement for 120 minutes after prediction. The index observation is the earliest valid active-dialysis reading within minutes 0 to 30. Future observation requirements define the retrospective evaluation cohort and cannot be confirmed when a new session first receives a score.

## Implemented selection procedure

The split search considers 100 seeds to balance patient-fold session counts and outcome prevalence, without using model performance. Among eligible candidates, models within 0.01 of the best grouped-CV average precision are ordered by validation Brier score. The dummy baseline and PCA benchmark are excluded from the final selection pool. PCA was evaluated at 85% and 95% variance thresholds; 85% was selected. Calibration and threshold choices use validation patients. The final model uses no additional calibration. Lower raw Brier score does not establish superiority over every alternatively calibrated competitor.

## Distinct alert strategies

At the fixed threshold 0.1428558780 (rounded to 0.143), 3,918 of 21,354 test sessions are flagged (18.35%). Sensitivity is 66.1%, precision 30.6%, and false alerts are 12.73 per 100 total sessions. Separately, ranking the highest-risk 20% selects 4,271 sessions, captures 69.1% of events, has precision 29.4%, and produces 14.13 false alerts per 100 sessions. Ranking requires a defined batch and tie rule before local use; retrospective whole-test-set ranking is not an implemented live scheduling rule.

| Strategy | Sessions flagged | Sensitivity / event recall | Precision | False alerts per 100 total sessions |
|---|---:|---:|---:|---:|
| Fixed threshold 0.1428558780 | 3,918 (18.35%) | 66.1% | 30.6% | 12.73 |
| Highest-risk 20% | 4,271 (20.00%) | 69.1% | 29.4% | 14.13 |

False alerts here are flags in sessions without the recorded BP outcome. This is not the false-positive rate, whose denominator is only non-event sessions. Ranking metrics in final_test_metrics.json remain capacity metrics even when stored beside fixed-threshold metrics.

## Proposed future targets

The following are proposed feasibility targets drafted after the retrospective study, not original success criteria, observed achievements, or approved clinical standards. Before collecting pilot outcomes, local clinical and operational leads must agree the strategy, sample size, confidence-interval requirements, and stop rules. A proposed fixed-threshold silent evaluation seeks sensitivity at least 65%, at most 20 alerts and 15 false alerts per 100 sessions. Timed simulated reviews seek median active review time at most 2 minutes per alert and total active review time at most 40 minutes per 100 sessions. Median review time alone does not determine total workload. Report uncertainty and all failures. These illustrative targets assess feasibility only and do not establish patient benefit or safety.

| Measure | Proposed target | Measurement |
|---|---|---|
| Event detection | Sensitivity ≥65% | TP / (TP + FN), with patient-bootstrap 95% CI |
| Review volume | ≤20 alerts per 100 sessions | All flags / all evaluated eligible sessions ×100 |
| False-alert workload | ≤15 per 100 sessions | FP / all evaluated eligible sessions ×100 |
| Active review time | Median ≤2 minutes per alert | Timed simulation first; later supervised review only after approval |
| Total active review budget | ≤40 minutes per 100 sessions | Sum measured active review minutes; report tail and shift totals |

These draft values use existing retrospective results as feasibility reference points. They must not be represented as prospectively prespecified or independently achieved. Report calibration, subgroup errors, missingness, serious incidents and uncertainty alongside these targets. A point estimate passing a target alone does not authorize live clinical use. Leads must define acceptable uncertainty and subgroup sample sizes before starting. Silent mode cannot measure the effect of displayed alerts or prove cost savings.
