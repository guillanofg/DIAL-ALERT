# Record the live GenAI demonstration on a Mac

Allow about two minutes for the recording, excluding installation and model download.

## Setup

1. Install Ollama from https://ollama.com/download/mac and open it.
2. In Terminal, run `ollama pull llama3.2:3b`.
3. From the extracted `step9_assistant` folder run `python3 src/server.py`.
4. Open http://127.0.0.1:8099.
5. Confirm `python3 src/assistant.py threshold --mode generate` returns a real generated draft. If it fails, resolve the error before calling the demonstration complete.

## Recording script

Use Shift-Command-5 and select Record Selected Portion. Include only the application window.

- 0:00–0:15: “This is the DIAL-ALERT project Q&A assistant. It explains project documentation using a local language model.”
- 0:15–0:40: Select the threshold question and click Show source excerpts. “These are the source facts. Source mode does not call the language model.”
- 0:40–1:15: Click Generate explanation. Wait for the actual response. “The local model drafts an answer from these excerpts and attaches source IDs.”
- 1:15–1:40: Compare the answer and source. “Automatic checks examine citations and numbers. I still review the meaning of each statement.”
- 1:40–2:00: Select the limitations question and repeat generation. “This component explains the project. The original random forest remains responsible for prediction.”

Do not read out an expected answer before the model produces it. If the model fails, record the failure honestly and retry after correcting the cause.

## Save live evidence

With the server running:

```bash
mkdir -p runs
ollama --version > runs/ollama_version.txt
python3 src/assistant.py threshold --mode generate > runs/live_threshold.json
python3 src/assistant.py limitations --mode generate > runs/live_limitations.json
```

Review outputs before publication. Keep the actual model digest and corpus hash with the recording. The `runs/` directory is ignored by Git until files are deliberately reviewed and selected. The packaged video contains edited live recording excerpts; see ../evidence/LIVE_REVIEW.md for evidence and limitations.
