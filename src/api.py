"""FastAPI interface for invoice processing and decision history."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, model_validator

from .config import settings
from .models import Decision, DemoScenario
from .service import InvoiceDecisionEngine, demo_scenarios

app = FastAPI(title="Invoice Decision Engine", version="2.0.0")
engine = InvoiceDecisionEngine()


class ProcessRequest(BaseModel):
    document_text: str | None = None
    filename: str = "invoice.txt"
    structured_invoice: dict[str, Any] | None = None

    @model_validator(mode="after")
    def has_input(self):
        if self.document_text is None and self.structured_invoice is None:
            raise ValueError("Provide document_text or structured_invoice.")
        return self


class HistoryResponse(BaseModel):
    decisions: list[Decision]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invoices/process", response_model=Decision)
def process_invoice(request: ProcessRequest) -> Decision:
    try:
        if request.structured_invoice is not None:
            return engine.process_structured(request.structured_invoice, filename=request.filename)
        return engine.process_text(request.document_text or "", filename=request.filename, source="api-text")
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/invoices/upload", response_model=Decision)
async def upload_invoice(file: UploadFile = File(...)) -> Decision:
    data = await file.read()
    if len(data) > settings.upload_max_bytes:
        raise HTTPException(status_code=413, detail="Invoice file is larger than the configured upload limit.")
    try:
        return engine.process_document(data, filename=file.filename or "invoice.pdf")
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/decisions/{decision_id}", response_model=Decision)
def get_decision(decision_id: str) -> Decision:
    decision = engine.get_decision(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Decision not found.")
    return decision


@app.get("/decisions", response_model=HistoryResponse)
def list_decisions(limit: int = 50) -> HistoryResponse:
    return HistoryResponse(decisions=engine.list_decisions(limit))


@app.post("/demo/reset")
def reset_demo() -> dict[str, str]:
    engine.reset_demo()
    return {"status": "reset", "message": "Seeded vendors, POs, and demonstration history restored."}


@app.get("/demo/scenarios", response_model=list[DemoScenario])
def scenarios() -> list[DemoScenario]:
    return demo_scenarios()
