"""Public contracts for invoice extraction and decisioning."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DecisionStatus(str, Enum):
    APPROVE = "APPROVE"
    APPROVE_WITH_VARIANCE = "APPROVE_WITH_VARIANCE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECT = "REJECT"


class RuleState(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class LineItem(BaseModel):
    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class InvoiceFields(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    po_reference: str | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    source_text: str = ""


class ExtractionResult(BaseModel):
    fields: InvoiceFields
    method: str
    source: str
    document_hash: str
    pages: int = 1
    ocr_attempted: bool = False
    warnings: list[str] = Field(default_factory=list)


class Vendor(BaseModel):
    id: str
    name: str
    approved: bool


class PurchaseOrder(BaseModel):
    po_number: str
    vendor_name: str
    currency: str
    total_amount: Decimal
    order_date: str
    status: str


class RuleCheck(BaseModel):
    name: str
    state: RuleState
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    name: str
    message: str
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Decision(BaseModel):

    id: str
    status: DecisionStatus
    reason: str
    created_at: str
    document_hash: str
    extraction: ExtractionResult
    vendor: Vendor | None = None
    purchase_order: PurchaseOrder | None = None
    rule_checks: list[RuleCheck] = Field(default_factory=list)
    audit_events: list[AuditEvent] = Field(default_factory=list)
    tolerance_amount: Decimal | None = None
    remaining_before: Decimal | None = None
    remaining_after: Decimal | None = None
    duplicate_of: str | None = None


class DemoScenario(BaseModel):
    key: str
    name: str
    description: str
    filename: str
    document_text: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
