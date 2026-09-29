# Design notes

## Seams

`InvoiceDecisionEngine` is the single processing seam shared by the Streamlit UI, FastAPI routes, and tests. `ProcurementRepository` is the SQLite adapter behind that seam. Extraction is deterministic and returns evidence rather than hiding uncertainty.

## Failure modes

- Unreadable or image-only PDF: local OCR is attempted when available; unavailable OCR becomes an explicit manual-review warning.
- Missing required identity: manual review, never automatic approval.
- Unknown vendor or ambiguous PO fallback: manual review.
- Exact duplicate: rejection with the previous decision ID.
- PO overage beyond tolerance: rejection. Overage within tolerance: approval with variance.
- Partial PO billing: approved decisions reduce the remaining balance; a later invoice is checked against that remainder.
- Currency mismatch: manual review; no live exchange-rate dependency.

## Data handling

The default adapter stores normalized decision evidence, not raw PDF binaries. Document hashes support duplicate detection. The upload size limit defaults to 10 MiB and can be changed with `INVOICE_MAX_UPLOAD_BYTES`. The SQLite path can be changed with `INVOICE_DB_PATH`.
