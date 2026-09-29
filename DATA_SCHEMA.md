# Invoice data contract

## Normalized invoice

`InvoiceFields` contains:

- `vendor_name`, `invoice_number`, `invoice_date`, `po_reference`
- `currency`, `subtotal`, `tax`, `total`
- optional `line_items`
- field-level `confidence`, extraction `warnings`, and bounded `source_text`

Amounts are decimal values. Dates are normalized to ISO `YYYY-MM-DD` when parsing succeeds. Required automatic-decision fields are invoice number, invoice date, vendor, currency, and total.

## Procurement records

SQLite stores approved/unapproved vendors, purchase orders, and decision history. The seeded data includes an existing approved partial invoice for `PO-2001` and an existing invoice for `INV-3001` so split and duplicate behavior are reproducible after reset.

## Decision

Each decision contains the normalized extraction, matched vendor/PO, status, reason, tolerance and remaining-balance calculations, each rule result, duplicate reference when applicable, and ordered audit events.
