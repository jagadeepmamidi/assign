"""FastAPI entry point for triage and account briefs."""

from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator

from .account_brief import AccountBrief, build_account_brief  # pyright: ignore[reportMissingImports]
from .retrieval import get_retriever  # pyright: ignore[reportMissingImports]
from .triage import (  # pyright: ignore[reportMissingImports]
    TriageResult,
    stream_draft,
    triage_ticket,
    triage_ticket_text,
)

app = FastAPI(title="Zycus Support AI", version="1.0.0")


class TriageRequest(BaseModel):
    subject: str | None = None
    body: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def one_input_shape(self):
        if self.text is None and (self.subject is None or self.body is None):
            raise ValueError("Provide either text or both subject and body")
        if self.text is not None and (self.subject is not None or self.body is not None):
            raise ValueError("Provide text, or subject and body, not both")
        return self


def _triage(request: TriageRequest) -> tuple[TriageResult, str, str]:
    if request.text is not None:
        result = triage_ticket_text(request.text)
        lines = request.text.splitlines()
        return result, lines[0] if lines else "", "\n".join(lines[1:])
    return triage_ticket(request.subject or "", request.body or ""), request.subject or "", request.body or ""


@app.post("/triage", response_model=TriageResult)
def triage(request: TriageRequest) -> TriageResult:
    try:
        return _triage(request)[0]
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/triage/stream")
def triage_stream(request: TriageRequest):
    try:
        result, subject, body = _triage(request)
        hits = get_retriever().search(f"Subject: {subject}\n\nBody: {body}", k=3)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    def events():
        classification = {
            key: value
            for key, value in result.model_dump().items()
            if key in {"product", "product_area", "category", "urgency", "recommended_team", "matched_kb_doc"}
        }
        yield f"event: classification\ndata: {json.dumps(classification, ensure_ascii=False, sort_keys=True)}\n\n"
        try:
            for token in stream_draft(subject, body, result, hits):
                yield f"event: draft\ndata: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except RuntimeError as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/account-brief/{account_id}", response_model=AccountBrief)
def account_brief(account_id: str) -> AccountBrief:
    try:
        return build_account_brief(account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/account-brief/{account_id}/stream")
def account_brief_stream(account_id: str):
    """Stream the deterministic brief section by section over SSE.

    The brief itself is computed (and cached) before streaming starts, so the
    determinism guarantee is preserved; streaming here is delivery, not generation.
    """
    try:
        brief = build_account_brief(account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    def events():
        header = {
            "account_id": brief.account_id,
            "company": brief.company,
            "account_found": brief.account_found,
            "executive_summary": brief.executive_summary,
        }
        yield f"event: summary\ndata: {json.dumps(header, ensure_ascii=False, sort_keys=True)}\n\n"
        for risk in brief.open_risks:
            yield f"event: risk\ndata: {risk.model_dump_json()}\n\n"
        for point in brief.talking_points:
            yield f"event: talking_point\ndata: {json.dumps({'point': point}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
