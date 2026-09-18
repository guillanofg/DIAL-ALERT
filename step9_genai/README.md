# DIAL-ALERT — Step 9: Use of Generative AI

AIM AI/ML Capstone · September 2026

## What was implemented

Generative AI was used during authoring to draft a plain-language summary of the DIAL-ALERT cohort and model results, and to assist in writing the accompanying Python validation code, tests, documentation, and demonstration script. The exact underlying model identifier and sampling settings were not recorded and are not claimed here.

This package contains the resulting AI-drafted example, its aggregate source facts, a runnable source-checking and rendering program, executed tests, and a captioned demo video. This is an **authoring-assistance use case**, not a live LLM-backed clinical application. The random-forest predictor remains responsible for risk estimation.

**Investigator review is pending.** Automated numeric verification was performed; no claim is made that the investigator has already approved every sentence or executed these files on their own computer.

## Run the example

Python 3.10 or newer; standard library only. From the repository root:

```bash
python3 step9_genai/src/replay_summary.py
python3 -m unittest discover -s step9_genai/tests -v
```

After downloading the standalone ZIP, open Terminal in the extracted `step9_genai` folder:

```bash
python3 src/replay_summary.py
python3 -m unittest discover -s tests -v
```

The program validates the saved aggregate facts, substitutes checked numeric values into the saved AI draft, and prints the summary. Optional export:

```bash
python3 src/replay_summary.py --output summary.md
```

No API account, key, network connection, model download, or patient-level dataset is needed. Re-running this program reproduces the saved example; it does not generate new language or call an LLM.

## Input → AI assistance → checked output

1. Read the frozen model card, locked test metrics, and feature/threshold contract from Step 8.
2. Extract a small set of aggregate cohort and model facts.
3. Use the authoring assistant to draft four short paragraphs: cohort and imbalance; repeated observations and partitioning; model results; limitations.
4. Keep numbers as named placeholders bound to source values. Publish the final draft artifact, not private dialogue or instruction history.
5. Run numeric/schema checks, render the text, and present the result for investigator review.

The workflow also demonstrates why AI-generated prose needs review: a statement can use correct numbers while making an unsupported clinical claim.

## Concrete example

The cohort paragraph renders as:

> The analytic cohort contains 106,758 dialysis sessions from 830 patients. The recorded event prevalence is 8.49%. Events are therefore less common than non-events, so accuracy alone would be an incomplete description of prediction performance.

The complete example is [examples/rendered_summary.md](examples/rendered_summary.md). It also reports test average precision 0.395, ROC AUC 0.852, and Brier score 0.062. These are existing project results, not newly computed model performance.

## Files

- `src/`: runnable summary validation and video-generation code.
- `examples/`: aggregate input, saved AI draft and rendered summary.
- `demo/`: captioned video and preview.
- `evidence/`: frozen source artifacts and verification records.
- `tests/`: numerical and publication checks.

## Evidence and source traceability

| Facts | Frozen source |
| --- | --- |
| Cohort, event prevalence, test patients, study limitations | `evidence/model_card.md`, copied unchanged from the Step 8 package |
| Locked test metrics, selected model, confusion counts | `evidence/original_test_metrics.json`, copied unchanged from Step 8 |
| Feature count and operating threshold | `evidence/decision_threshold.json`, copied unchanged from Step 8 |
| Language drafted for this step | `examples/ai_draft.json` |
| Curated aggregate input | `examples/aggregate_facts.json` |

The Step 8 sources were derived from the earlier capstone analysis. This step does not independently reproduce raw-data cohort construction or model fitting. Aggregate values were cross-checked against the public repository README at commit `64f12f80fe4de8c7aa11702e28517dbbc873dd41`. The model card and metrics remain the authority for the saved example.

## Verification and limitations

Eight local unit tests passed. Checks reject changed cohort counts, altered metrics, unexpected aggregate fields, invented numeric literals, unsupported placeholders, and removal of the pending-review status. The test suite deliberately demonstrates that unsupported **nonnumeric prose** can still pass the numeric validator. Therefore, a passing result is not a clinical-safety certificate or a complete hallucination detector.

The validator is specific to this frozen example. Changed source artifacts require reconciliation; it is not a generic EDA engine. No data-dictionary generator, autonomous recommender, retrieval chatbot, external LLM API, or live LLM integration was implemented. No missingness statistics or other EDA findings absent from the reviewed sources were invented.

The video is a rendered walkthrough of actual local output and test evidence. It is captioned and silent, not a browser recording or a recording of live LLM generation. The saved summary can be reproduced exactly. Fresh LLM wording cannot be reproduced exactly from this package because authoring instructions and generation settings are not included.

No improvement in clinical accuracy, patient outcomes, writing quality, or authoring speed was measured. Benefits are limited to demonstrating a practical documentation workflow with source-linked numeric checks.

## Publication and review

Only aggregate project facts and final example artifacts are included. This package contains no raw patient records, private dialogue, authoring instruction history, or API credentials. The description of Generative AI use documents the implemented Step 9 workflow.

Before submission, the investigator should read the rendered summary against the frozen sources, confirm that it accurately reflects their work, and retain or revise the pending-review label. A future live GenAI extension would need separate evaluation of factual consistency, privacy, failure handling, and clinical scope; it is not part of this deliverable.

## Suggested presentation explanation

“I used Generative AI to help draft a plain-language summary and the supporting validation code. The summary uses aggregate project facts. The program checks the numbers against saved source artifacts before rendering the text. My predictive model remains the random forest. This demonstration replays a saved AI draft and does not provide treatment advice or make a live LLM call.”

## Public documentation and verification

The [PDF report](DIAL_ALERT_Step9_Report.pdf) describes the implemented
workflow, example, reproduction commands and limitations.

The original eight summary tests are retained. Additional publication tests
check reviewed-file hashes, credential/contact patterns, dialogue markers,
and accidental authoring-tool identifiers. They complement
manual review; they cannot prove the absence of every possible secret or
identify every form of personal information.

The publication manifest freezes the reviewed release. Intentional edits or
regenerated media require a fresh review and updated hashes before publication.
