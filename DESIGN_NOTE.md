# Design note

## 1. Failure modes, detection, and mitigation

First, a model could hallucinate a knowledge-base citation or quote. Triage accepts a citation only when its filename is present in the retrieved top three, its fused score clears the threshold, and its excerpt is an exact substring of that chunk. Brief risks are retained only when their quote is an exact substring of the source ticket body or an indexed escalation note. Citation existence, substring checks, and a faithfulness judge catch residual failures.

Second, a model could understate urgency. A deterministic safety net scans subject and body for `production down`, `data loss`, `all users`, `everyone blocked`, and similar signals. It floors urgency at P2 and marks human review in reasoning; P1 remains possible when the model returns it. This is intentionally conservative: classification is assistive, not an automatic incident declaration.

Third, an LLM provider can be unavailable or rate-limited. Calls retry once with exponential backoff, then return a clear degraded error through CLI/API boundaries. The API maps provider failures to HTTP 503 rather than returning fabricated content. Offline deterministic mode exists for evaluation and local demonstrations; production calls fail clearly when `LLM_API_KEY` is absent.

## 2. Latency versus quality

Task 2 uses prompt chaining: extraction first identifies signals and preserves source quotes, then synthesis writes the brief from validated signals and account data. This costs roughly two LLM round trips, but materially improves grounding and makes quote validation auditable. Under a hard latency budget, collapse both prompts into one structured call and cache extraction per account per day, accepting weaker separation of evidence from prose. Hybrid retrieval adds only milliseconds for this corpus; model latency dominates. The deterministic cache makes repeated identical calls byte-stable and removes repeat provider latency.

## 3. Data sensitivity and PII

BM25 and Chroma embeddings run locally; ticket and KB documents never go to an embedding API. Before an LLM request, common email and phone patterns are redacted. Only ticket/account text needed for the requested operation is sent to the configured model. `LLM_BASE_URL` can target a self-hosted or VPC OpenAI-compatible endpoint, so deployment can keep model traffic inside a controlled network. The supplied dataset is synthetic, but the same controls apply to production data; logs should avoid raw prompts.

## 4. Scaling ten times

A tenfold KB increase remains comfortable: Chroma persists vectors and BM25 rebuilds quickly at this scale. The first bottleneck is provider rate limits and LLM spend, not retrieval. Queue triage requests, batch similar tickets, deduplicate near-identical incidents, and cache account briefs per account per day. For larger corpora, shard or periodically rebuild the lexical index, monitor Chroma disk growth, and add retrieval latency/recall telemetry. Keep quote and citation validation deterministic at every scale.
