"""SQLite adapter for vendors, purchase orders, decisions, and invoice history."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from .extraction import normalize_invoice_number, normalize_name
from .models import Decision, PurchaseOrder, Vendor


SEED_VENDORS = (
    ("V-001", "Acme Industrial Supplies", "acmeindustrialsupplies", 1),
    ("V-002", "Northstar Facilities", "northstarfacilities", 1),
    ("V-003", "Orbit Office Goods", "orbitofficegoods", 0),
)

SEED_POS = (
    ("PO-1001", "V-001", "USD", "1000.00", "2026-09-01", "OPEN"),
    ("PO-2001", "V-002", "USD", "5000.00", "2026-09-05", "OPEN"),
    ("PO-3001", "V-001", "USD", "250.00", "2026-09-08", "OPEN"),
    ("PO-4001", "V-003", "USD", "800.00", "2026-09-10", "OPEN"),
)


class ProcurementRepository:
    """Deep persistence interface used by the decision engine."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS vendors (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL UNIQUE,
                    approved INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS purchase_orders (
                    po_number TEXT PRIMARY KEY,
                    vendor_id TEXT NOT NULL REFERENCES vendors(id),
                    currency TEXT NOT NULL,
                    total_amount NUMERIC NOT NULL,
                    order_date TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    document_hash TEXT NOT NULL,
                    vendor_id TEXT,
                    normalized_invoice_number TEXT,
                    po_number TEXT,
                    total_amount NUMERIC,
                    status TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_decisions_duplicate
                    ON decisions(vendor_id, normalized_invoice_number, document_hash);
                CREATE INDEX IF NOT EXISTS idx_decisions_po ON decisions(po_number, status);
                """
            )
            if db.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] == 0:
                self._seed_locked(db)

    def _seed_locked(self, db: sqlite3.Connection) -> None:
        db.executemany("INSERT INTO vendors VALUES (?, ?, ?, ?)", SEED_VENDORS)
        db.executemany("INSERT INTO purchase_orders VALUES (?, ?, ?, ?, ?, ?)", SEED_POS)
        # A prior approved partial invoice demonstrates cumulative PO balance and a duplicate signal.
        db.execute(
            """INSERT INTO decisions
               (id, document_hash, vendor_id, normalized_invoice_number, po_number,
                total_amount, status, decision_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "seed-split-001",
                "seed-split-hash",
                "V-002",
                "splita001",
                "PO-2001",
                "3000.00",
                "APPROVE",
                json.dumps({"id": "seed-split-001", "status": "APPROVE", "reason": "Seeded prior split invoice"}),
                "2026-09-10T00:00:00+00:00",
            ),
        )
        db.execute(
            """INSERT INTO decisions
               (id, document_hash, vendor_id, normalized_invoice_number, po_number,
                total_amount, status, decision_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "seed-duplicate-001",
                "seed-duplicate-hash",
                "V-001",
                "inv3001",
                "PO-3001",
                "250.00",
                "APPROVE",
                json.dumps({"id": "seed-duplicate-001", "status": "APPROVE", "reason": "Seeded prior invoice"}),
                "2026-09-10T00:00:00+00:00",
            ),
        )

    def reset(self) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM decisions")
            db.execute("DELETE FROM purchase_orders")
            db.execute("DELETE FROM vendors")
            self._seed_locked(db)

    def vendor(self, name: str | None) -> Vendor | None:
        if not name:
            return None
        with self._connect() as db:
            row = db.execute("SELECT * FROM vendors WHERE normalized_name = ?", (normalize_name(name),)).fetchone()
        if not row:
            return None
        return Vendor(id=row["id"], name=row["name"], approved=bool(row["approved"]))

    def purchase_order(self, po_number: str | None) -> PurchaseOrder | None:
        if not po_number:
            return None
        with self._connect() as db:
            row = db.execute(
                """SELECT p.*, v.name AS vendor_name FROM purchase_orders p
                   JOIN vendors v ON v.id = p.vendor_id WHERE p.po_number = ?""",
                (po_number.upper(),),
            ).fetchone()
        return self._po_model(row) if row else None

    def candidates(self, vendor: Vendor | None, currency: str | None, total: Decimal | None) -> list[PurchaseOrder]:
        if not vendor or not currency or total is None:
            return []
        with self._connect() as db:
            rows = db.execute(
                """SELECT p.*, v.name AS vendor_name FROM purchase_orders p
                   JOIN vendors v ON v.id = p.vendor_id
                   WHERE p.vendor_id = ? AND p.currency = ? AND p.status = 'OPEN'""",
                (vendor.id, currency.upper()),
            ).fetchall()
        # Candidate matching is intentionally conservative: the invoice must fit the original PO plus tolerance.
        return [po for row in rows if (po := self._po_model(row)) and total <= po.total_amount + self._tolerance(po.total_amount)]

    def duplicate(self, vendor: Vendor | None, invoice_number: str | None, digest: str) -> tuple[str, str] | None:
        if not vendor:
            return None
        normalized = normalize_invoice_number(invoice_number)
        with self._connect() as db:
            row = db.execute(
                """SELECT id, status FROM decisions
                   WHERE vendor_id = ? AND document_hash = ?
                   ORDER BY created_at LIMIT 1""",
                (vendor.id, digest),
            ).fetchone()
            if row:
                return row["id"], "identical document hash"
            if not normalized:
                return None
            row = db.execute(
                """SELECT id, status FROM decisions
                   WHERE vendor_id = ? AND normalized_invoice_number = ?
                   ORDER BY created_at LIMIT 1""",
                (vendor.id, normalized),
            ).fetchone()
        return (row["id"], "vendor and invoice number") if row else None

    def approved_total(self, po_number: str) -> Decimal:
        with self._connect() as db:
            row = db.execute(
                """SELECT COALESCE(SUM(total_amount), 0) AS amount FROM decisions
                   WHERE po_number = ? AND status IN ('APPROVE', 'APPROVE_WITH_VARIANCE')""",
                (po_number,),
            ).fetchone()
        return Decimal(str(row["amount"]))

    def save_decision(self, decision: Decision, vendor: Vendor | None) -> None:
        fields = decision.extraction.fields
        with self._connect() as db:
            db.execute(
                """INSERT INTO decisions
                   (id, document_hash, vendor_id, normalized_invoice_number, po_number,
                    total_amount, status, decision_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision.id,
                    decision.document_hash,
                    vendor.id if vendor else None,
                    normalize_invoice_number(fields.invoice_number),
                    decision.purchase_order.po_number if decision.purchase_order else None,
                    str(fields.total) if fields.total is not None else None,
                    decision.status.value,
                    decision.model_dump_json(),
                    decision.created_at,
                ),
            )

    def get_decision(self, decision_id: str) -> Decision | None:
        with self._connect() as db:
            row = db.execute("SELECT decision_json FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        return Decision.model_validate_json(row["decision_json"]) if row else None

    def list_decisions(self, limit: int = 50) -> list[Decision]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT decision_json FROM decisions ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
        decisions: list[Decision] = []
        for row in rows:
            try:
                decisions.append(Decision.model_validate_json(row["decision_json"]))
            except ValueError:
                # Seed balance/duplicate rows are intentionally internal history anchors.
                continue
        return decisions

    @staticmethod
    def _po_model(row: sqlite3.Row) -> PurchaseOrder:
        return PurchaseOrder(
            po_number=row["po_number"],
            vendor_name=row["vendor_name"],
            currency=row["currency"],
            total_amount=Decimal(str(row["total_amount"])),
            order_date=row["order_date"],
            status=row["status"],
        )

    @staticmethod
    def _tolerance(amount: Decimal) -> Decimal:
        return max(amount * Decimal("0.01"), Decimal("10.00"))
