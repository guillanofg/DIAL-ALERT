# DIAL-ALERT Project Q&A Assistant

Alternative Step 9: Use of Generative AI. Academic documentation prototype.

This application retrieves DIAL-ALERT source excerpts and can ask a local language model to explain them. Six selectable questions cover the prediction target, threshold, inputs, limitations, synthetic examples and privacy.

**Current status:** local source retrieval and tests passed during the original build. The user subsequently demonstrated generation in the browser on a Mac and uploaded the recording. The revised demo contains edited excerpts of that real interaction. Review found incomplete and unsupported wording in some generated answers. This remains an academic prototype requiring source review, not a clinically validated assistant. Live model digest, Ollama version and a complete six-question evaluation remain outstanding.

## Start on your Mac

1. Extract this folder and open Terminal inside `step9_assistant`.
2. Check `python3 --version` (Python 3.10 or newer).
3. Run `python3 src/server.py`.
4. Open http://127.0.0.1:8099 on the same computer.
5. Choose a question and click **Show source excerpts**. This works without installing any Python packages.

## Enable fresh language generation

Install the desktop application from https://ollama.com/download/mac and open it. In Terminal:

```bash
ollama pull llama3.2:3b
ollama list
python3 src/assistant.py threshold --mode generate
```

If Ollama is already running, do not start a second server. If using the CLI without the desktop app, run `ollama serve` in a separate Terminal. The model download requires internet access and approximately 2 GB for the model file, plus runtime memory and disk overhead. Review the model's license before redistribution. The package does not include model weights.

With `src/server.py` running, click **Generate explanation**. The application contacts only `127.0.0.1:11434`, records the model digest in the response, and requests structured JSON. It never silently substitutes source quotes for a generated answer. Generation failure displays no generated answer. Keep the app bound to loopback.

If generation succeeds, manually compare every sentence with the displayed source. An answer that fails automatic citation or numeric checks is withheld. These checks can still accept incorrect nonnumeric prose or misused numbers.

## Reproduce the demonstrations

```bash
python3 -m unittest discover -s tests -v
python3 src/assistant.py threshold --mode sources
# Start src/server.py in another Terminal first:
python3 src/record_demo.py
```

`record_demo.py` records actual HTTP results to `evidence/http_demo.json`. If Ollama is available it records live generation; otherwise it records the actual 503 failure. It does not fabricate a successful generation.

The included MP4 is a silent edited live browser screencast supplied by the user. The cut list and qualitative review are in `evidence/LIVE_REVIEW.md`. The original build HTTP transcript is historical evidence of the then-unavailable model. To record another live demo, follow `docs/LIVE_DEMO.md`.

## Files

- `src/assistant.py`: retrieval, local LLM call, structured answer checks and CLI.
- `src/server.py`, `src/index.html`: local web interface.
- `knowledge/project.json`: curated excerpts with source section references.
- `docs/GENAI_REPORT.md`: use of GenAI, architecture, examples and limitations.
- `docs/DIAL_ALERT_Step9_Project_Assistant.pptx`: presentation with code and examples.
- `examples/source_answers.json`: actual source-mode results.
- `examples/illustrative_generated_answer.json`: clearly labeled authoring-time example, not Llama output.
- `demo/DIAL_ALERT_Step9_Live_Demo.mp4`: captioned video.
- `evidence/`: actual HTTP transcript and test record.

## GitHub integration

Copy this complete folder into the existing repository as `step9_assistant/`. It is an independent companion and does not change the prediction model or Step 8 dependencies. Link the report, deck and demo from the repository README. The presentation already includes code and examples, satisfying that alternative deliverable route. This package is included in the project repository.

## Data boundary

The interface accepts only an enumerated question ID and mode. It rejects arbitrary text and extra fields, so the supported workflow does not ingest patient records. The knowledge base contains project-level methodology and previously documented synthetic examples. The app has no uploads, external search, treatment tools or database connection. It does not log request bodies. Local Ollama behavior outside this application is governed by its own configuration.

## References

- Project source: `DIAL_ALERT_Step8_Deployment_Guide.md`, release 1.0.1, read 18 September 2026. Excerpts are curated summaries of sections 1, 3, 4, 5 and 8.
- Ollama chat API: https://docs.ollama.com/api/chat
- Ollama local model inventory: https://docs.ollama.com/api/tags
- Model listing and license links: https://ollama.com/library/llama3.2
