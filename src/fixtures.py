"""Reproducible invoices used by the UI, API, and acceptance walkthrough."""

from __future__ import annotations

from .models import DemoScenario


SCENARIOS = [
    DemoScenario(
        key="clean-approved",
        name="Clean invoice — approve",
        description="Machine-readable invoice with an explicit PO and matching total.",
        filename="acme-invoice-1001.txt",
        document_text="""Vendor: Acme Industrial Supplies
Invoice Number: INV-1001
Invoice Date: 2026-09-12
PO Number: PO-1001
Currency: USD
Subtotal: 925.00
Tax: 75.00
Total: 1,000.00
""",
    ),
    DemoScenario(
        key="scanned-review",
        name="Scanned image — manual review",
        description="Image-only PDF fallback with unavailable/low-confidence extraction.",
        filename="scanned-invoice.pdf",
        document_text="SCANNED IMAGE ONLY — no machine-readable invoice fields",
    ),
    DemoScenario(
        key="missing-number-review",
        name="Missing invoice number — manual review",
        description="The total and PO are usable, but invoice identity is incomplete.",
        filename="missing-invoice-number.txt",
        document_text="""Vendor: Acme Industrial Supplies
Invoice Date: 2026-09-13
PO Number: PO-1001
Currency: USD
Subtotal: 9.25
Tax: 0.75
Total: 10.00
""",
    ),
    DemoScenario(
        key="split-invoice",
        name="Split PO invoice — approve",
        description="A second invoice consumes the remaining balance on a partially billed PO.",
        filename="northstar-split-002.txt",
        document_text="""Vendor: Northstar Facilities
Invoice Number: INV-SPLIT-002
Invoice Date: 2026-09-14
PO Number: PO-2001
Currency: USD
Subtotal: 1,850.00
Tax: 150.00
Total: 2,000.00
""",
    ),
    DemoScenario(
        key="duplicate-reject",
        name="Duplicate invoice — reject",
        description="The vendor and normalized invoice number already exist in history.",
        filename="acme-duplicate-3001.txt",
        document_text="""Vendor: Acme Industrial Supplies
Invoice Number: INV-3001
Invoice Date: 2026-09-15
PO Number: PO-3001
Currency: USD
Subtotal: 231.48
Tax: 18.52
Total: 250.00
""",
    ),
    DemoScenario(
        key="over-tolerance-reject",
        name="Over tolerance — reject",
        description="The invoice exceeds the remaining PO amount beyond the configured tolerance.",
        filename="acme-overage-1002.txt",
        document_text="""Vendor: Acme Industrial Supplies
Invoice Number: INV-1002
Invoice Date: 2026-09-16
PO Number: PO-1001
Currency: USD
Subtotal: 1,017.50
Tax: 82.50
Total: 1,100.00
""",
    ),
]


def list_scenarios() -> list[DemoScenario]:
    return SCENARIOS.copy()


def scenario(key: str) -> DemoScenario:
    for item in SCENARIOS:
        if item.key == key:
            return item
    raise KeyError(f"Unknown demo scenario: {key}")
