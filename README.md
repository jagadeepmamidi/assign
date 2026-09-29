# Invoice Decision Engine

A deterministic invoice-processing workflow that turns PDF/text/structured invoice input into an explainable payment decision.

## What it does

1. Extracts vendor, invoice identity, date, PO reference, currency, subtotal, tax, total, and optional line-item evidence.
2. Records field confidence and extraction warnings. PDFs use machine-readable text first and attempt local OCR for image-only pages when the workstation supports it.
3. Validates required identity fields, approved vendors, currency, tax arithmetic, and PO matching.
4. Detects exact duplicates using vendor + normalized invoice number and document hash.
5. Tracks cumulative approved amounts against a PO, including split invoices.
6. Applies a tolerance of the greater of 1% of the PO amount or $10.
7. Returns `APPROVE`, `APPROVE_WITH_VARIANCE`, `MANUAL_REVIEW`, or `REJECT` with rule evidence and an ordered audit trail.

The deterministic path requires no API key or external service. OCR is an optional local capability; no LLM is required or consulted for financial decisions. Unreadable documents are explicitly routed to manual review.

## Decision policy

- Required fields: invoice number, invoice date, vendor, currency, and total. Required-field confidence below `0.75` blocks automatic approval.
- An explicit PO is preferred. If it is missing, vendor/currency/amount fallback matching is allowed only when exactly one safe candidate remains.
- Unknown or unapproved vendors, ambiguous PO matches, currency mismatches, and unreliable extraction go to manual review.
- A provable exact duplicate is rejected. Partial duplicate evidence goes to manual review.
- Split invoices consume the PO's remaining approved balance. Amounts over the remaining balance but within tolerance are approved with variance; larger overages are rejected.
- Separate or embedded tax is accepted. When subtotal and tax are present, they must reconcile to the total within the configured tolerance.
- Raw uploads are processed without storing PDF binaries by default. The decision stores a SHA-256 hash and normalized evidence.

## Run locally

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt

uvicorn src.api:app --reload
# in a second terminal
streamlit run app.py
```

Open Streamlit at `http://localhost:8501`. The API is at `http://localhost:8000`.

## API

### Process text or structured fallback

```bash
curl -X POST http://localhost:8000/invoices/process \\
  -H "Content-Type: application/json" \\
  -d '{"document_text":"Vendor: Acme Industrial Supplies\\nInvoice Number: INV-1001\\nInvoice Date: 2026-09-12\\nPO Number: PO-1001\\nCurrency: USD\\nSubtotal: 925.00\\nTax: 75.00\\nTotal: 1000.00"}'
```

`POST /invoices/upload` accepts a PDF, text, or JSON file. `GET /decisions/{id}` retrieves one result. `GET /decisions` lists history. `GET /demo/scenarios` lists reproducible examples. `POST /demo/reset` restores seeded vendors, POs, split-invoice history, and duplicate history.

## Showcase scenarios

- Clean machine-readable invoice → approve.
- Image-only/scanned invoice → OCR attempt and manual review when local OCR is unavailable or fields remain unreliable.
- Missing invoice number → manual review.
- Split invoice against a PO with an existing approved partial → approve against remaining balance.
- Exact duplicate → reject with the previous decision ID.
- Out-of-tolerance amount → reject.

## Test

```bash
pytest -q
```

The tests exercise the shared processing service and FastAPI interface, not private implementation details.
