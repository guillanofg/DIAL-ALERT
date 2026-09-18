# Submission-readiness notes

Priority corrections applied to public documentation:

1. Outcome, cohort counts, model-selection rule, threshold, and test metrics are aligned across the README and model card.
2. The 120-minute eligibility rule is explicitly defined as **last observed dialysis minute >=120**, not 120 minutes after prediction.
3. Future pilot targets are labeled as proposed: >=65% event detection, <=15 false alerts per 100 eligible sessions, and median alert review <=2 minutes.
4. The 0.143 probability-threshold strategy is separated from the highest-risk-20% capacity strategy.
5. A clean-environment reproducibility checklist and execution record are included; successful execution remains pending until actually run.
6. Included versus regenerated artifacts and presentation rebuild dependencies are documented.
7. Presentation source already uses automated finalization/layout checks, but the current binary decks still require a final visual review of rendered slides before submission.
8. Step 8 now contains an actual local Flask app and instructions but no recorded screencast yet. Step 9 is accurately described as saved-draft replay with numeric validation, not live LLM generation.

## Secondary analyses

Advance-warning time, a simple clinical comparator, historical-feature ablation, equally calibrated finalist comparison, and sensitivity to extreme values/excluded sessions are useful secondary analyses. They should not be used for repeated tuning against the locked test set.

## Future validation

External/temporal validation, fairness confirmation on fresh data, and staged prospective evaluation remain future work.
