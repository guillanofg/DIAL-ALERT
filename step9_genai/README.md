# DIAL-ALERT — Step 9: Use of Generative AI

AIM AI/ML Capstone · September 2026

## What was implemented

Generative AI was used during authoring to draft a plain-language summary of aggregate DIAL-ALERT cohort/model results and to assist with validation code, tests, documentation, and the demonstration script. The exact underlying model identifier and sampling settings were not recorded and are not claimed.

This package contains a **saved AI-drafted example**, frozen aggregate source facts, runnable source-checking/rendering code, tests, and a captioned demo video. It is an **authoring-assistance workflow**, not a live LLM-backed clinical application. The random-forest predictor remains separate.

## What the demo proves — and does not prove

The demo shows that the saved draft can be replayed and its numeric placeholders checked against frozen aggregate source artifacts. It **does not show live LLM generation**, a live chatbot, an LLM recommender, or a live clinical model call. Fresh language generation is not reproduced by this package.

## Run the saved-draft replay

Python 3.10 or newer; standard library only:

```bash
python3 step9_genai/src/replay_summary.py
python3 -m unittest discover -s step9_genai/tests -v
```

Optional export:

```bash
python3 step9_genai/src/replay_summary.py --output summary.md
```

No API account, key, network connection, model download, or patient-level dataset is needed.

## Input -> AI-assisted draft -> checked output

1. Read frozen aggregate model/cohort sources.
2. Extract a small approved set of facts.
3. Use an authoring assistant to draft short explanatory prose.
4. Keep numeric values bound to named placeholders.
5. Run schema/numeric checks and render the saved draft.
6. Present the rendered text for investigator review.

The workflow demonstrates a key limitation: correct numbers do not guarantee that every sentence is clinically justified, so human review remains necessary.

## Example

The saved example reports the 106,758-session / 830-patient cohort, 8.49% event prevalence, test average precision 0.395, ROC AUC 0.852, and Brier score 0.062. These are existing project results, not new model performance computed by Step 9.

## Files

- `src/`: saved-draft replay and demo-generation code.
- `examples/`: aggregate input, saved draft, rendered summary.
- `demo/`: captioned walkthrough video and preview.
- `evidence/`: frozen source artifacts and verification records.
- `tests/`: numeric/schema/publication checks.

## Limitations

The validator is specific to this frozen example. It is not a general hallucination detector. No data-dictionary generator, autonomous recommender, retrieval chatbot, external LLM API, Ollama live-generation workflow, or live LLM integration is claimed by the published package.

The video is a rendered walkthrough of local replay/test evidence. It is **not** evidence of live AI generation.

## Privacy/publication scope

Only aggregate project facts and final example artifacts are included. Raw patient records, private dialogue, authoring instruction history, and API credentials are excluded.

## Suggested presentation explanation

“I used Generative AI to help draft a plain-language summary and supporting validation code. The published demonstration replays a saved draft and checks its numbers against frozen aggregate source artifacts. It does not make a live LLM call, and the predictive model remains the random forest.”
