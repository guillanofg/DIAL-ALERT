# Step 9: Use of Generative AI
## DIAL-ALERT Project Q&A Assistant

September 2026. Alternative application-focused submission.

## Purpose

This component helps a reviewer understand the DIAL-ALERT project through short, source-linked explanations. A user selects a question such as “What is the alert threshold and what does it mean?” The application retrieves relevant project documentation and can ask a locally hosted language model to generate an explanation.

The original random forest remains the risk estimator. This companion does not run or modify that estimator, change its threshold, recommend treatment, or process individual patient records.

## How Generative AI is used

The implemented runtime integration uses Ollama's local chat API with `llama3.2:3b`. The model receives a selected question and retrieved source excerpts. It is instructed to return one to three short claims with source IDs in JSON. This is a small retrieval-augmented generation (RAG) workflow: retrieve project evidence, then generate language using that evidence.

The application chooses the two highest-scoring passages using keyword overlap. This simple retriever is appropriate for the deliberately small six-topic corpus and six supported questions. It has no embeddings, vector database, conversation memory, fine-tuning or autonomous actions. It is a bounded project Q&A assistant rather than an unrestricted medical chatbot.

An authoring assistant helped draft the implementation, documentation and illustrative wording. The package includes operational application instructions needed to reproduce its behavior. It excludes private authoring conversation history, private prompts and credentials. The runtime model is Llama through Ollama. The illustrative answer below was composed during authoring and is not a recorded Llama response.

## Execution status

| Component | Actual status |
|---|---|
| Retrieval and source display | Implemented and locally executed |
| Local HTTP interface | Routes and requests tested |
| LLM adapter and answer validation | Unit-tested and demonstrated through the user’s browser recording |
| Live local Llama generation | User recording shows generation in progress and a resulting answer on the Mac |
| Generated-answer quality | Qualitative review identifies supported threshold statements and incomplete or unsupported wording in other answers |
| Demo video | Edited excerpts from the user’s live screen recording |
| Browser interaction on the user's Mac | Observed in the uploaded recording |
| Clinical effectiveness | Not studied by this component |
| GitHub publication | Included in this repository |

The uploaded recording now demonstrates the browser generation workflow on the user’s Mac. This is functional demonstration evidence, not a comprehensive answer-quality or clinical validation. The live API payloads, model digest and Ollama version were not supplied with the recording.

## Application workflow

1. Select one of six project questions. The API accepts only its question ID and a mode.
2. Retrieve up to two relevant source excerpts with stable IDs.
3. In source mode, display exact excerpts and explicitly state that no LLM was called.
4. In generation mode, confirm the local model exists and capture its digest.
5. Submit the selected question and excerpts to the local chat API.
6. Validate response completion, JSON schema, claim count, citation membership and literal numeric values.
7. Display generated claims as a draft beside the source excerpts, or display an error with no answer.

There is no silent fallback that could make a source excerpt look like a freshly generated answer.

## Input, code and example

Input:

```json
{"question_id":"threshold","mode":"generate"}
```

The relevant source says:

> An alert occurs when model probability is greater than or equal to 0.1428558780357408 (approximately 14.29%). This is the original validation-selected F2 threshold. It is not a clinical treatment threshold or an enforced 20% alert quota. A below-threshold result does not rule out an event.

Core call, condensed from `src/assistant.py`:

```python
response = transport('/api/chat', {
    'model': 'llama3.2:3b',
    'stream': False,
    'format': 'json',
    'options': {'temperature': 0, 'seed': 42,
                'num_predict': 400, 'num_ctx': 4096},
    'messages': messages,
})
```

Illustrative generated-answer format, authored for explanation and **not obtained from a live Llama run**:

```json
{"claims":[
  {"text":"The alert threshold is approximately 14.29%.","source_id":"S2"},
  {"text":"A below-threshold result does not rule out an event.","source_id":"S2"}
]}
```

The initial build-workspace generation request returned HTTP 503 because no model was installed there. That historical evidence remains in evidence/http_demo.json. Subsequently, the user installed the model and supplied a live screen recording. The new video shows the threshold generation request and its resulting source-linked answer. The illustrative JSON above remains labeled as illustrative; the observed screen text is separately documented in evidence/LIVE_REVIEW.md.

## Grounding and privacy

The knowledge base is a curated project summary based on the current Step 8 deployment guide (release 1.0.1), sections 1, 3, 4, 5 and 8, read on 18 September 2026. The corpus covers the prediction target, threshold, inputs, scope, previously documented synthetic examples and deployment behavior. It does not contain raw patient tables or newly inferred clinical results.

The selected-question interface prevents arbitrary patient narratives from entering the supported workflow. Extra fields are rejected. Application model traffic uses a fixed loopback endpoint, disables proxy use and refuses redirects. The application itself has no cloud API keys, external retrieval, patient database connection or request-body logging. No weights are redistributed.

Version the knowledge JSON, source references, code and model digest together. A SHA-256 of the knowledge file accompanies each answer. The model tag alone is mutable; a successful run must record its resolved digest. Temperature zero and a seed aid repeatability but do not guarantee identical wording across hardware, model or runtime changes. The uploaded video does not expose the live Ollama version or model digest. These remain unrecorded in the submitted evidence and are not invented.

## Evaluation

Nine local unit tests passed, including all six expected first-ranked source matches. Tests cover source mode without model calls, rejection of unsupported questions, invented numbers, invalid source IDs, malformed generated JSON and missing models. A test double exercises the successful API contract, but does not measure LLM performance.

One test explicitly demonstrates that an unsupported nonnumeric sentence can pass the validator. Source IDs show where a statement claims support; they do not prove semantic entailment. Numbers can also be used incorrectly while matching an excerpt. Human review remains necessary.

Actual loopback HTTP requests verified four source-mode questions, rejection of an extra field and the missing-model failure. Evidence is in `evidence/http_demo.json`. No clinical data or estimated patient outcomes were used.

For a complete answer-quality evaluation beyond the observed live workflow, run all six questions with the installed model and preserve the actual outputs. Review each claim for source support, completeness, clear limits and absence of treatment advice. Report the number of supported claims divided by all claims, invalid-citation count, unsupported-number count, abstention rate and latency. These are proposed measures, not already measured quality results. Broader paraphrase testing would be needed before adding free-text questions.

## Demo and submission

The current demo is a silent edited screencast from the user’s uploaded recording. It keeps original intervals 0–13 seconds, 36–41.5 seconds and 56–86 seconds, at their original speed, joined and tail-trimmed into 46 seconds. Cuts remove unrelated windows and idle time. The title identifies the edit. Only surrounding margins are cropped; generated wording is not corrected or replaced in the video.

The first excerpt shows threshold generation in progress and the resulting answer. The later excerpts show selection/generation for the limitations question and its result after a cut. The full interval between that request and result is not retained, so the edited clip cannot establish generation latency. The original recording remains separate and is not included in the shareable package.

The threshold answer is consistent with the displayed excerpts. However, the limitations answer drops the qualifier “starting” before systolic blood pressure and omits the external/temporal and prospective validation requirement. Another answer in the original recording describes “future conditions” too broadly. These observations show why source-linked generated answers still need human review. See evidence/LIVE_REVIEW.md.

The presentation reflects the live demonstration and its limitations. The reviewed package is included in this repository. The Mac recording guide remains available for reproducing or improving the demonstration.

## Requirement mapping

| Requested deliverable | Included artifact |
|---|---|
| GenAI-enhanced application | Local project Q&A application with implemented LLM adapter |
| Document how GenAI was used | This report |
| Code and examples in repo or presentation | Full source package and PowerPoint with code and examples |
| Demo video | MP4 containing edited excerpts of the live browser workflow |

## References

DIAL-ALERT Step 8 Deployment Guide, release 1.0.1, current project file read 18 September 2026.

[Ollama chat API](https://docs.ollama.com/api/chat) describes the chat endpoint and structured JSON option. [Local model inventory](https://docs.ollama.com/api/tags) supplies model names and digests. [Llama 3.2 model listing](https://ollama.com/library/llama3.2) provides the model variants and license links. Documentation checked 18 September 2026.
