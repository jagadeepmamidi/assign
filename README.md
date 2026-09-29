# Zycus Support AI

Zycus Support AI is a mock-data support copilot implementing intelligent ticket triage and TAM account-health briefs. Task 1 retrieves relevant knowledge-base context with hybrid BM25 lexical search plus dense local Chroma search, fuses rankings with RRF, and asks an OpenAI-compatible LLM for validated JSON. Task 2 uses a deterministic, dataset-anchored account/ticket join and a two-step extraction-to-synthesis prompt chain. Evaluation includes RAGAS-style faithfulness, answer relevancy, context precision, and account-summary groundedness judges.

## Architecture

- `rank-bm25` and persistent local ChromaDB (default ONNX MiniLM embeddings) are fused with Reciprocal Rank Fusion (`k=60`). No embedding API is used.
- OpenAI Python SDK targets Groq by default through `LLM_BASE_URL`; any compatible provider works without code changes.
- JSON mode plus Pydantic validation retries once with validation feedback. Task 2 LLM calls are cached on disk by SHA-256 of model, prompt filename, and rendered prompt.
- Ticket/account joining uses `account_id` OR case-insensitive company name, deduplicated by `ticket_id`. Dataset verification found direct `account_id` matching for only 4 of 50 accounts, while all 50 company names match tickets (4–17 tickets each); the company fallback is therefore required. The dataset's maximum ticket timestamp anchors the last-90-day window; wall-clock time is never used.

## Setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS/Linux; then add key
```

Add an OpenAI-compatible key to `.env`. Never commit `.env`. First run downloads Chroma's local ONNX embedding model (~80 MB, one time; internet required) and builds the tiny index in a few seconds.

## Sample runs

Task 1, JSON input:

```bash
python -m src.triage --subject "CloudSync timeout" --body "Files stopped syncing; ERR_CONNECTION_TIMEOUT after 30s"
```

Expected shape: `{ "product": "CloudSync", "category": "Performance", "urgency": "P2/P3", "matched_kb_doc": {...}, "draft_first_response": "..." }`.

Task 1, raw text:

```bash
python -m src.triage --text $'CloudSync timeout\\nFiles stopped syncing in production'
```

Task 2:

```bash
python -m src.account_brief --account-id ACC-3336
```

Expected shape: stable JSON with `executive_summary`, `open_risks` (verbatim quotes), and `talking_points`, followed by rendered Markdown.

Task 3:

```bash
python -m evals.run_evals
```

Writes `evals/eval_report.json` and `evals/eval_report.md`. Adversarial cases (ambiguous or empty tickets) use a behavioural acceptance criterion - the draft must ask a clarifying question - because RAG grounding metrics are undefined when no knowledge-base context can apply. With no key, deterministic rule checks run in offline fallback and judge rows are marked skipped; configure a key for LLM-as-judge scores.

## API and UI

```bash
uvicorn src.api:app --reload
streamlit run app.py
```

Endpoints: `POST /triage` accepts `{"subject": "...", "body": "..."}` or `{"text": "..."}`; `GET /account-brief/{account_id}` returns the brief. `POST /triage/stream` emits a classification SSE event first, then draft tokens from a second streaming call. `GET /account-brief/{account_id}/stream` streams the brief section by section over SSE; the brief is computed and cached before streaming starts, so Task 2 determinism is preserved - streaming is delivery, not generation. Structured classification is intentionally completed before streaming because JSON mode cannot be safely token-streamed.

## Design

See [DESIGN_NOTE.md](DESIGN_NOTE.md) for failure modes, latency/quality tradeoffs, PII handling, and 10x scaling.
