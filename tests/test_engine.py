from __future__ import annotations

from pathlib import Path

from src.models import DecisionStatus
from src.service import InvoiceDecisionEngine


CLEAN = """Vendor: Acme Industrial Supplies
Invoice Number: INV-TEST-001
Invoice Date: 2026-09-12
PO Number: PO-1001
Currency: USD
Subtotal: 925.00
Tax: 75.00
Total: 1000.00
"""

VIT_RECEIPT_TEXT = """VIT-AP UNIVERSITY (Event Registration) Beside AP Secretariat, Ainavolu - 522237. GSTN 37AACTV1896M2ZN
INVOICE CUM RECEIPT
Receipt Date: 2026-09-22 20:34:46 Receipt.No VIT-26-27-010718 Transaction Details
Description Unit Price
Graduands hostel accommodation 1 ₹350.00 Total Amount
Inclusive of GST ₹350.00
Payment Mode UPI
"""


def engine(tmp_path: Path) -> InvoiceDecisionEngine:
    return InvoiceDecisionEngine(tmp_path / "invoice.sqlite3")


def test_clean_invoice_is_approved_with_rule_evidence(tmp_path: Path) -> None:
    decision = engine(tmp_path).process_text(CLEAN)

    assert decision.status == DecisionStatus.APPROVE
    assert decision.purchase_order is not None
    assert decision.purchase_order.po_number == "PO-1001"
    assert any(rule.name == "tax_reconciliation" and rule.state.value == "PASS" for rule in decision.rule_checks)
    assert [event.name for event in decision.audit_events] == ["received", "extracted", "validated", "matched", "decided"]


def test_uploaded_receipt_extracts_visible_fields_but_requires_manual_review(tmp_path: Path) -> None:
    decision = engine(tmp_path).process_text(VIT_RECEIPT_TEXT, source="pdf-text")
    fields = decision.extraction.fields

    assert fields.vendor_name == "VIT-AP UNIVERSITY"
    assert fields.invoice_number == "VIT-26-27-010718"
    assert fields.invoice_date == "2026-09-22"
    assert fields.currency == "INR"
    assert fields.total == 350
    assert fields.po_reference is None
    assert decision.status == DecisionStatus.MANUAL_REVIEW
    assert "vendor is unknown" in decision.reason
    assert "PO matching could not run" in decision.reason


def test_missing_invoice_number_requires_manual_review(tmp_path: Path) -> None:
    text = CLEAN.replace("Invoice Number: INV-TEST-001\n", "")

    decision = engine(tmp_path).process_text(text)

    assert decision.status == DecisionStatus.MANUAL_REVIEW
    assert "missing invoice_number" in decision.reason


def test_split_invoice_uses_seeded_remaining_balance(tmp_path: Path) -> None:
    text = """Vendor: Northstar Facilities
Invoice Number: INV-SPLIT-TEST
Invoice Date: 2026-09-14
PO Number: PO-2001
Currency: USD
Subtotal: 1850.00
Tax: 150.00
Total: 2000.00
"""

    decision = engine(tmp_path).process_text(text)

    assert decision.status == DecisionStatus.APPROVE
    assert decision.remaining_before == 2000
    assert decision.remaining_after == 0


def test_duplicate_invoice_is_rejected_with_previous_id(tmp_path: Path) -> None:
    text = """Vendor: Acme Industrial Supplies
Invoice Number: INV-3001
Invoice Date: 2026-09-15
PO Number: PO-3001
Currency: USD
Subtotal: 231.48
Tax: 18.52
Total: 250.00
"""

    decision = engine(tmp_path).process_text(text)

    assert decision.status == DecisionStatus.REJECT
    assert decision.duplicate_of == "seed-duplicate-001"
    assert "duplicate" in decision.reason


def test_over_tolerance_invoice_is_rejected(tmp_path: Path) -> None:
    text = CLEAN.replace("INV-TEST-001", "INV-OVER-001").replace("Total: 1000.00", "Total: 1100.00")

    decision = engine(tmp_path).process_text(text)

    assert decision.status == DecisionStatus.REJECT
    assert "remaining PO balance" in decision.reason


def test_missing_po_uses_one_safe_fallback_with_variance(tmp_path: Path) -> None:
    text = CLEAN.replace("PO Number: PO-1001\n", "").replace("INV-TEST-001", "INV-FALLBACK-001")

    decision = engine(tmp_path).process_text(text)

    assert decision.status == DecisionStatus.APPROVE_WITH_VARIANCE
    assert decision.purchase_order is not None
    assert decision.purchase_order.po_number == "PO-1001"
    assert any(rule.name == "po_fallback_match" for rule in decision.rule_checks)


def test_unreadable_pdf_is_manual_review(tmp_path: Path) -> None:
    decision = engine(tmp_path).process_document(b"not a PDF", filename="scan.pdf")

    assert decision.status == DecisionStatus.MANUAL_REVIEW
    assert decision.extraction.method == "pdf-error"
