from __future__ import annotations

from fastapi.testclient import TestClient

from src import api
from src.service import InvoiceDecisionEngine


def test_process_endpoint_returns_explainable_decision(tmp_path) -> None:
    api.engine = InvoiceDecisionEngine(tmp_path / "api.sqlite3")
    client = TestClient(api.app)

    response = client.post(
        "/invoices/process",
        json={
            "document_text": """Vendor: Acme Industrial Supplies
Invoice Number: INV-API-001
Invoice Date: 2026-09-12
PO Number: PO-1001
Currency: USD
Subtotal: 925.00
Tax: 75.00
Total: 1000.00
"""
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "APPROVE"
    assert payload["rule_checks"]
    assert payload["audit_events"]


def test_reset_and_scenarios_are_available(tmp_path) -> None:
    api.engine = InvoiceDecisionEngine(tmp_path / "api.sqlite3")
    client = TestClient(api.app)

    scenarios = client.get("/demo/scenarios")
    reset = client.post("/demo/reset")

    assert scenarios.status_code == 200
    assert {item["key"] for item in scenarios.json()} >= {"scanned-review", "split-invoice", "duplicate-reject"}
    assert reset.status_code == 200
