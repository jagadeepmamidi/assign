"""Task 1: support-ticket triage using hybrid retrieval and structured generation."""

from __future__ import annotations

import argparse
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .llm import complete_json, stream_text
from .retrieval import HybridRetriever, get_retriever

Category = Literal[
    "Bug", "Feature Request", "How-To", "Performance", "Billing", "Integration", "Onboarding", "Data Loss"
]
Urgency = Literal["P1", "P2", "P3", "P4"]
_PRODUCTS = ["DataBridge Pro", "CloudSync", "AnalyticsHub", "SecureVault", "WorkflowEngine"]
_URGENCY_ORDER = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}


class KBMatch(BaseModel):
    source_file: str
    section_heading: str
    excerpt: str


class TriageResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product: str = "Unknown"
    product_area: str = "Unknown"
    category: Category
    urgency: Urgency
    reasoning: str = Field(min_length=1)
    matched_kb_doc: KBMatch | None = None
    recommended_team: str
    draft_first_response: str = Field(min_length=1)


def _team(category: str, urgency: str) -> str:
    if category == "Billing":
        return "Billing Ops"
    if category == "Data Loss" or urgency == "P1":
        return "Escalation Engineering"
    if category == "Integration":
        return "Integrations Team"
    if category in {"How-To", "Onboarding"}:
        return "Customer Education"
    return "Tier-1 Support"


def _safety_floor(result: TriageResult, text: str) -> TriageResult:
    lower = text.casefold()
    critical = ("production down", "data loss", "all users", "everyone blocked", "complete outage", "business stopped")
    if any(term in lower for term in critical) and _URGENCY_ORDER[result.urgency] > _URGENCY_ORDER["P2"]:
        result.urgency = "P2"
        result.reasoning = result.reasoning.rstrip(".") + ". Safety rule raised floor to P2; human review required."
    result.recommended_team = _team(result.category, result.urgency)
    return result


def _citation(result: TriageResult, hits: list[dict]) -> TriageResult:
    if not result.matched_kb_doc:
        return result
    allowed: dict[str, dict] = {}
    for hit in hits:  # hits are rank-ordered; keep the best chunk per file
        allowed.setdefault(hit["chunk"].source_file, hit)
    match = result.matched_kb_doc
    hit = allowed.get(match.source_file)
    if hit is None or hit["score"] < 0.025:
        result.matched_kb_doc = None
    elif match.excerpt not in hit["chunk"].text:
        # Model paraphrased the excerpt: keep the verified citation, swap in real chunk text.
        result.matched_kb_doc = KBMatch(
            source_file=hit["chunk"].source_file,
            section_heading=hit["chunk"].section_heading,
            excerpt=hit["chunk"].text[:240],
        )
    return result


def _heuristic(text: str, hits: list[dict]) -> TriageResult:
    lower = text.casefold()
    product = next((p for p in _PRODUCTS if p.casefold() in lower), "Unknown")
    if any(x in lower for x in ["invoice", "charged", "billing", "seat", "renew"]):
        category: Category = "Billing"
    elif any(x in lower for x in ["how do i", "how to", "configure", "documentation"]):
        category = "How-To"
    elif any(x in lower for x in ["slow", "timeout", "latency", "performance"]):
        category = "Performance"
    elif any(x in lower for x in ["integrat", "webhook", "oauth", "sso"]):
        category = "Integration"
    elif any(x in lower for x in ["feature", "request", "would like"]):
        category = "Feature Request"
    elif any(x in lower for x in ["onboard", "new user", "provision"]):
        category = "Onboarding"
    elif any(x in lower for x in ["lost", "missing data", "corrupt"]):
        category = "Data Loss"
    else:
        category = "Bug"
    urgency: Urgency = (
        "P2" if any(x in lower for x in ["critical", "urgent", "blocked", "production", "all users"]) else "P3"
    )
    best = hits[0] if hits and hits[0]["score"] >= 0.025 else None
    citation = None
    if best:
        chunk = best["chunk"]
        citation = KBMatch(
            source_file=chunk.source_file, section_heading=chunk.section_heading, excerpt=chunk.text[:240]
        )
    return TriageResult(
        product=product,
        product_area="Unknown",
        category=category,
        urgency=urgency,
        reasoning="Offline deterministic fallback based on explicit ticket terms.",
        matched_kb_doc=citation,
        recommended_team=_team(category, urgency),
        draft_first_response="Thanks for reporting this. We are reviewing the details and will follow up with next steps.",
    )


def _render_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] {h['chunk'].source_file} :: {h['chunk'].section_heading}\n{h['chunk'].text}"
        for i, h in enumerate(hits, 1)
    )


def triage_ticket(
    subject: str, body: str, *, retriever: HybridRetriever | None = None, allow_offline: bool = False
) -> TriageResult:
    subject, body = subject.strip(), body.strip()
    text = f"Subject: {subject}\n\nBody: {body}".strip()
    hits = (retriever or get_retriever()).search(text, k=3)
    if allow_offline:
        return _safety_floor(_heuristic(text, hits), text)
    prompt = f"TICKET\n{text}\n\nRETRIEVED KNOWLEDGE BASE CHUNKS\n{_render_context(hits)}"
    result = complete_json("triage_v1.txt", prompt, TriageResult)
    result = _citation(result, hits)
    return _safety_floor(result, text)


def triage_ticket_text(text: str, **kwargs) -> TriageResult:
    lines = text.splitlines()
    return triage_ticket(lines[0] if lines else "", "\n".join(lines[1:]), **kwargs)


def stream_draft(subject: str, body: str, result: TriageResult, hits: list[dict]):
    prompt = f"Ticket subject: {subject}\nTicket body: {body}\nClassification: {result.model_dump_json()}\nRetrieved KB:\n{_render_context(hits)}\nWrite only the final customer-facing first response."
    return stream_text("draft_v1.txt", prompt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify one support ticket")
    parser.add_argument("--subject", default="")
    parser.add_argument("--body", default="")
    parser.add_argument("--text")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    result = (
        triage_ticket_text(args.text, allow_offline=args.offline)
        if args.text is not None
        else triage_ticket(args.subject, args.body, allow_offline=args.offline)
    )
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
