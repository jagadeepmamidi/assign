"""Invoice processing orchestration behind the API and Streamlit interfaces."""

from __future__ import annotations

import hashlib
import json
import uuid
from decimal import Decimal
from pathlib import Path

from .extraction import extract_document, extract_structured, extract_text, normalize_name
from .fixtures import list_scenarios
from .models import (
    AuditEvent,
    Decision,
    DecisionStatus,
    ExtractionResult,
    InvoiceFields,
    PurchaseOrder,
    RuleCheck,
    RuleState,
    Vendor,
    utc_now,
)
from .repository import ProcurementRepository


class InvoiceDecisionEngine:
    """Deep processing interface: one deterministic path for UI, API, and tests."""

    def __init__(self, db_path: Path | None = None):
        from .config import settings

        self.repository = ProcurementRepository(db_path or settings.database_path)

    def process_text(self, text: str, *, filename: str = "invoice.txt", source: str = "text") -> Decision:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        extraction = extract_text(text, source=source, digest=digest)
        return self._decide(extraction)

    def process_document(self, data: bytes, *, filename: str) -> Decision:
        return self._decide(extract_document(data, filename))

    def process_structured(self, payload: dict, *, filename: str = "invoice.json") -> Decision:
        canonical = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        extraction = extract_structured(payload, source="structured", digest=hashlib.sha256(canonical).hexdigest())
        return self._decide(extraction)

    def get_decision(self, decision_id: str) -> Decision | None:
        return self.repository.get_decision(decision_id)

    def list_decisions(self, limit: int = 50) -> list[Decision]:
        return self.repository.list_decisions(limit)

    def reset_demo(self) -> None:
        self.repository.reset()

    def _decide(self, extraction: ExtractionResult) -> Decision:
        fields = extraction.fields
        events = [AuditEvent(name="received", message="Invoice input accepted.")]
        events.append(
            AuditEvent(
                name="extracted",
                message=f"Extracted fields using {extraction.method}; source={extraction.source}.",
            )
        )
        checks: list[RuleCheck] = []
        vendor = self.repository.vendor(fields.vendor_name)
        po: PurchaseOrder | None = None
        duplicate_of: str | None = None
        tolerance: Decimal | None = None
        remaining_before: Decimal | None = None
        remaining_after: Decimal | None = None
        variance = False
        hard_reject = False
        manual_reasons: list[str] = []
        reject_reasons: list[str] = []

        required = ("invoice_number", "invoice_date", "vendor_name", "currency", "total")
        for field in required:
            value = getattr(fields, field)
            confidence = fields.confidence.get(field, 0.0)
            if value is None or value == "":
                checks.append(RuleCheck(name=f"required_{field}", state=RuleState.FAIL, message=f"{field} is missing."))
                manual_reasons.append(f"missing {field}")
            elif confidence < 0.75:
                checks.append(
                    RuleCheck(
                        name=f"confidence_{field}",
                        state=RuleState.FAIL,
                        message=f"{field} confidence {confidence:.2f} is below 0.75.",
                        evidence={"confidence": confidence},
                    )
                )
                manual_reasons.append(f"low confidence for {field}")
            else:
                checks.append(
                    RuleCheck(
                        name=f"required_{field}",
                        state=RuleState.PASS,
                        message=f"{field} is present.",
                        evidence={"confidence": confidence},
                    )
                )

        if vendor is None:
            checks.append(RuleCheck(name="vendor_exists", state=RuleState.FAIL, message="Vendor is not in the procurement master."))
            manual_reasons.append("vendor is unknown")
        elif not vendor.approved:
            checks.append(RuleCheck(name="vendor_approved", state=RuleState.FAIL, message="Vendor is not approved for automatic payment."))
            manual_reasons.append("vendor is not approved")
        else:
            checks.append(RuleCheck(name="vendor_approved", state=RuleState.PASS, message="Vendor is approved."))

        duplicate = self.repository.duplicate(vendor, fields.invoice_number, extraction.document_hash)
        if duplicate:
            duplicate_of, duplicate_reason = duplicate
            checks.append(
                RuleCheck(
                    name="duplicate_detection",
                    state=RuleState.FAIL,
                    message=f"Duplicate detected by {duplicate_reason}.",
                    evidence={"previous_decision_id": duplicate_of},
                )
            )
            reject_reasons.append(f"duplicate of decision {duplicate_of}")
            hard_reject = True
        else:
            checks.append(RuleCheck(name="duplicate_detection", state=RuleState.PASS, message="No exact duplicate was found."))

        if fields.po_reference:
            po = self.repository.purchase_order(fields.po_reference)
            if po is None:
                checks.append(RuleCheck(name="po_reference", state=RuleState.FAIL, message="Referenced PO was not found."))
                manual_reasons.append("purchase order was not found")
            elif vendor and normalize_name(po.vendor_name) != normalize_name(vendor.name):
                checks.append(RuleCheck(name="po_vendor", state=RuleState.FAIL, message="PO vendor does not match invoice vendor."))
                manual_reasons.append("PO vendor does not match invoice vendor")
                po = None
            elif fields.currency and po.currency != fields.currency:
                checks.append(RuleCheck(name="currency_match", state=RuleState.FAIL, message="Invoice and PO currencies do not match."))
                manual_reasons.append("currency mismatch")
            else:
                checks.append(RuleCheck(name="po_reference", state=RuleState.PASS, message=f"Matched explicit PO {po.po_number}."))
        elif vendor and fields.total is not None:
            candidates = self.repository.candidates(vendor, fields.currency, fields.total)
            if len(candidates) == 1:
                po = candidates[0]
                variance = True
                checks.append(
                    RuleCheck(
                        name="po_fallback_match",
                        state=RuleState.WARN,
                        message=f"Matched one PO by vendor, currency, and amount: {po.po_number}.",
                    )
                )
            elif not candidates:
                checks.append(RuleCheck(name="po_fallback_match", state=RuleState.FAIL, message="No safe PO candidate was found."))
                manual_reasons.append("PO reference missing and no safe candidate found")
            else:
                checks.append(RuleCheck(name="po_fallback_match", state=RuleState.FAIL, message="Multiple PO candidates remain."))
                manual_reasons.append("PO reference missing and match is ambiguous")
        else:
            checks.append(RuleCheck(name="po_match", state=RuleState.FAIL, message="PO matching could not run."))
            manual_reasons.append("PO matching could not run")

        if po and fields.total is not None:
            tolerance = max(po.total_amount * Decimal("0.01"), Decimal("10.00"))
            approved_before = self.repository.approved_total(po.po_number)
            remaining_before = po.total_amount - approved_before
            remaining = remaining_before
            if fields.total > remaining + tolerance:
                checks.append(
                    RuleCheck(
                        name="po_remaining_balance",
                        state=RuleState.FAIL,
                        message=f"Invoice exceeds remaining PO balance by more than {tolerance:.2f}.",
                        evidence={"remaining": str(remaining), "invoice_total": str(fields.total), "tolerance": str(tolerance)},
                    )
                )
                reject_reasons.append("amount exceeds remaining PO balance beyond tolerance")
                hard_reject = True
            elif fields.total > remaining:
                checks.append(
                    RuleCheck(
                        name="po_remaining_balance",
                        state=RuleState.WARN,
                        message=f"Invoice uses {fields.total - remaining:.2f} of the {tolerance:.2f} tolerance.",
                        evidence={"remaining": str(remaining), "tolerance": str(tolerance)},
                    )
                )
                variance = True
            else:
                checks.append(
                    RuleCheck(
                        name="po_remaining_balance",
                        state=RuleState.PASS,
                        message=f"Invoice fits the remaining PO balance of {remaining:.2f}.",
                        evidence={"remaining": str(remaining)},
                    )
                )
            remaining_after = remaining - fields.total

        if fields.subtotal is not None and fields.tax is not None and fields.total is not None:
            tax_difference = abs(fields.subtotal + fields.tax - fields.total)
            tax_tolerance = tolerance or Decimal("0.01")
            if tax_difference > tax_tolerance:
                checks.append(
                    RuleCheck(
                        name="tax_reconciliation",
                        state=RuleState.FAIL,
                        message=f"Subtotal plus tax differs from total by {tax_difference:.2f}.",
                    )
                )
                manual_reasons.append("subtotal and tax do not reconcile to total")
            elif tax_difference > Decimal("0.01"):
                checks.append(RuleCheck(name="tax_reconciliation", state=RuleState.WARN, message="Tax reconciliation is within tolerance."))
                variance = True
            else:
                checks.append(RuleCheck(name="tax_reconciliation", state=RuleState.PASS, message="Subtotal and tax reconcile to total."))

        for warning in extraction.warnings:
            checks.append(RuleCheck(name="extraction_warning", state=RuleState.WARN, message=warning))
        if extraction.method in {"pdf-image-manual-review", "pdf-error"}:
            manual_reasons.append("document could not be reliably read")

        if hard_reject:
            status = DecisionStatus.REJECT
            reasons = reject_reasons
        elif manual_reasons:
            status = DecisionStatus.MANUAL_REVIEW
            reasons = manual_reasons
        elif variance:
            status = DecisionStatus.APPROVE_WITH_VARIANCE
            reasons = ["Invoice passed controls with an explainable variance or fallback match."]
        else:
            status = DecisionStatus.APPROVE
            reasons = ["Invoice passed vendor, PO, duplicate, amount, and tax controls."]

        events.append(AuditEvent(name="validated", message=f"Applied {len(checks)} validation and matching rules."))
        if po:
            events.append(AuditEvent(name="matched", message=f"PO match: {po.po_number}; remaining before: {remaining_before}."))
        events.append(AuditEvent(name="decided", message=f"Final decision: {status.value}."))
        decision = Decision(
            id=f"DEC-{uuid.uuid4().hex[:12].upper()}",
            status=status,
            reason="; ".join(reasons),
            created_at=utc_now(),
            document_hash=extraction.document_hash,
            extraction=extraction,
            vendor=vendor,
            purchase_order=po,
            rule_checks=checks,
            audit_events=events,
            tolerance_amount=tolerance,
            remaining_before=remaining_before,
            remaining_after=remaining_after,
            duplicate_of=duplicate_of,
        )
        self.repository.save_decision(decision, vendor)
        return decision


def default_engine() -> InvoiceDecisionEngine:
    return InvoiceDecisionEngine()


def demo_scenarios():
    return list_scenarios()
