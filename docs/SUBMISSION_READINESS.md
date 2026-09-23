# Submission-readiness status

Updated: 23 September 2026.

End-to-end reproduction was completed on 20 September 2026. The final report and both presentation decks were checked at commit 32191898a332ec96d334315ad0892652e139d4d8. Repository documentation and generation scripts were subsequently synchronized with those deliverables. The correction set was verified on 23 September 2026, including a successful GitHub Actions run after restoration of the presentation revision script and alignment of the Step 8 Flask dependency.

## Verified evidence

| Area | Status |
| --- | --- |
| Report and PDF | The supplied final report and PDF match the files at the audited commit. Corrected references and updated Step 9 wording are present. |
| Eligibility | The rule requires an observation at or beyond dialysis minute 120, not 120 minutes after prediction. |
| Proposed pilot targets | At least 65% event detection, no more than 15 false alerts per 100 eligible sessions, and median review time no longer than 2 minutes. These are proposed targets, not demonstrated prospective results. |
| Alert strategies | The fixed probability threshold of 0.143 and highest-risk 20% review strategy are reported separately. |
| Fresh reproduction | The execution record documents successful Python 3.12 source-data acquisition, checksum verification, cohort rebuilding, model training and evaluation, regenerated analysis outputs, and 15 passed tests on 20 September 2026. Results were numerically consistent with the locked reference, not byte-for-byte identical. |
| Presentations | The 16-slide technical deck and 11-slide business deck were rendered and inspected. Main results agree with the report. |
| Step 8 | Local Flask inference, synthetic input, recorded HTTP evidence, and demo playback are included. This does not establish clinical or cloud deployment. |
| Step 9 | An earlier saved-draft replay and a later live local AI assistant demonstration are included. Observed answer-quality limitations remain. Citation and numeric checks do not establish semantic correctness. |

## Final documentation verification

The artifact inventory, README_Step5.md, report revision script, final report generator, and presentation revision script have been synchronized with the audited deliverables and successful reproduction record.

The presentation revision script was restored and the Step 8 Flask dependency was aligned with the main environment. The subsequent GitHub Actions workflow completed successfully, including dependency installation and repository tests.

No model retraining was required for these documentation and generation-script corrections.

## Further research

Warning-time analysis, a small clinical comparator, history ablation, equally calibrated finalist comparisons, and extreme-value or short-session sensitivity analyses remain planned. See SECONDARY_ANALYSIS_PLAN.md.

External or temporal validation, confirmation of fairness findings on fresh patients, and prospective workflow evaluation remain future work. No clinical benefit or financial savings have been demonstrated.

## Evidence records

- REPRODUCIBILITY_RECORD.md
- ARTIFACT_INVENTORY.md
- ../step9_assistant/evidence/LIVE_REVIEW.md

The September 18 acquisition failure is historical context. It does not describe the later successful September 20 reproduction. The September 23 consistency audit did not independently repeat model training.