"""Deterministic PDF/text extraction with optional local OCR."""

from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .models import ExtractionResult, InvoiceFields

_LABELS = {
    "vendor_name": r"vendor|supplier|billed\s+by|from",
    "invoice_number": r"invoice\s+(?:number|no\.?)|invoice\s*#",
    "invoice_date": r"invoice\s+date|date",
    "po_reference": r"purchase\s+order|po(?:\s+number|\s+no\.?|\s*#)?",
    "subtotal": r"subtotal|sub-total",
    "tax": r"tax|vat|sales\s+tax",
    "total": r"grand\s+total|amount\s+due|invoice\s+total|total",
}


def document_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalized_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _label_value(text: str, label_pattern: str) -> str | None:
    pattern = re.compile(rf"^\s*(?:{label_pattern})\s*[:#-]?\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else None

def _receipt_invoice_number(text: str) -> str | None:
    match = re.search(r"\bReceipt\s*\.?\s*(?:No|Number)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _receipt_date(text: str) -> str | None:
    match = re.search(
        r"\bReceipt\s+Date\s*[:#-]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _header_vendor(text: str) -> str | None:
    for line in text.splitlines()[:8]:
        candidate = line.strip().strip("|# ")
        candidate = re.split(r"\s+(?:Beside|GSTN)\b|\s*\(", candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if (
            candidate
            and ":" not in candidate
            and "INVOICE" not in candidate.upper()
            and re.fullmatch(r"[A-Z0-9][A-Z0-9 .&-]{3,}", candidate)
        ):
            return candidate
    return None


def _receipt_total(text: str) -> Decimal | None:
    patterns = (
        r"[₹]\s*([\d,]+(?:\.\d{1,2})?)\s+Total\s+Amount",
        r"(?:Total\s+Amount|Amount\s+Due|Grand\s+Total)\s*[:#-]?\s*[₹$€£]?\s*([\d,]+(?:\.\d{1,2})?)",
        r"Inclusive\s+of\s+GST\s*[₹]?\s*([\d,]+(?:\.\d{1,2})?)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _amount(match.group(1))
    return None


def _amount(value: str | None) -> Decimal | None:
    if not value:
        return None
    matches = re.findall(r"[-+]?\(?\s*\d[\d,]*(?:\.\d{1,2})?\s*\)?", value)
    if not matches:
        return None
    raw = matches[-1].replace(",", "").replace(" ", "")
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()")
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        return None
    return -amount if negative else amount


def _date(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    match = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", cleaned)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    return None


def _currency(text: str) -> str | None:
    upper = text.upper()
    if "EUR" in upper or "€" in text:
        return "EUR"
    if "GBP" in upper or "£" in text:
        return "GBP"
    if "INR" in upper or "₹" in text or re.search(r"\bRs\.?\b", text, re.IGNORECASE):
        return "INR"
    if "USD" in upper or "$" in text:
        return "USD"
    return None


def extract_text(text: str, *, source: str = "text", digest: str | None = None, method: str = "text") -> ExtractionResult:
    """Extract normalized fields from invoice text without an LLM."""
    text = text.replace("\x00", "").strip()
    fields = InvoiceFields(source_text=text[:12000])
    values: dict[str, str | None] = {name: _label_value(text, pattern) for name, pattern in _LABELS.items()}

    fields.vendor_name = values["vendor_name"] or _header_vendor(text)
    fields.invoice_number = values["invoice_number"] or _receipt_invoice_number(text)
    fields.invoice_date = _date(values["invoice_date"]) or _date(_receipt_date(text))
    fields.po_reference = values["po_reference"]
    fields.currency = _currency(text)
    fields.subtotal = _amount(values["subtotal"])
    fields.tax = _amount(values["tax"])
    fields.total = _amount(values["total"]) or _receipt_total(text)

    if fields.po_reference:
        po_match = re.search(r"\bPO[-\s#]*[A-Z0-9-]+\b", fields.po_reference, re.IGNORECASE)
        fields.po_reference = po_match.group(0).replace(" ", "") if po_match else fields.po_reference.strip()
    if fields.invoice_number:
        invoice_match = re.search(r"\b(?:INV|INVOICE)[-\s#]*[A-Z0-9-]+\b", fields.invoice_number, re.IGNORECASE)
        fields.invoice_number = invoice_match.group(0).replace(" ", "") if invoice_match else fields.invoice_number.strip()

    if not fields.currency:
        fields.warnings.append("Currency was not found.")
    if not fields.total:
        fields.warnings.append("Invoice total was not found.")

    for name in ("vendor_name", "invoice_number", "invoice_date", "po_reference", "currency", "subtotal", "tax", "total"):
        value = getattr(fields, name)
        fields.confidence[name] = 0.98 if value is not None else 0.0

    if fields.vendor_name and fields.invoice_number:
        fields.vendor_name = re.sub(r"\s+", " ", fields.vendor_name).strip()
    if fields.total is not None and fields.subtotal is not None and fields.tax is not None:
        difference = abs(fields.subtotal + fields.tax - fields.total)
        if difference > Decimal("0.01"):
            fields.warnings.append(f"Subtotal plus tax differs from total by {difference:.2f}.")

    digest = digest or hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ExtractionResult(
        fields=fields,
        method=method,
        source=source,
        document_hash=digest,
        warnings=list(fields.warnings),
    )
def _pdf_text(data: bytes) -> tuple[str, int]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = len(reader.pages)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return text, pages


def _ocr_pdf(data: bytes) -> str:
    import fitz  # type: ignore[import-not-found]
    import pytesseract  # type: ignore[import-not-found]
    from PIL import Image  # type: ignore[import-not-found]

    document = fitz.open(stream=data, filetype="pdf")
    chunks: list[str] = []
    for page in document:
        renderable_page: Any = page
        pixmap = renderable_page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        chunks.append(pytesseract.image_to_string(image))
    return "\n".join(chunks)


def extract_document(data: bytes, filename: str) -> ExtractionResult:
    suffix = Path(filename).suffix.lower()
    digest = document_hash(data)
    if suffix in {".txt", ".csv"}:
        return extract_text(data.decode("utf-8", errors="replace"), source="upload", digest=digest)
    if suffix == ".json":
        payload: Any = json.loads(data.decode("utf-8"))
        return extract_structured(payload, source="json", digest=digest)
    if suffix != ".pdf":
        return extract_text(data.decode("utf-8", errors="replace"), source="upload", digest=digest, method="plain-text-fallback")

    warnings: list[str] = []
    try:
        text, pages = _pdf_text(data)
    except Exception as exc:  # parser errors are user-facing manual-review evidence
        return ExtractionResult(
            fields=InvoiceFields(source_text="", warnings=[f"PDF text extraction failed: {exc}"], confidence={}),
            method="pdf-error",
            source="upload",
            document_hash=digest,
            warnings=[f"PDF text extraction failed: {exc}"],
        )
    if len(text.strip()) >= 40:
        result = extract_text(text, source="upload", digest=digest, method="pdf-text")
        result.pages = pages
        return result

    warnings.append("PDF contains little or no machine-readable text; OCR was attempted.")
    try:
        ocr_text = _ocr_pdf(data)
    except Exception as exc:
        warnings.append(f"Local OCR unavailable: {exc}")
        return ExtractionResult(
            fields=InvoiceFields(source_text=text[:12000], warnings=warnings, confidence={}),
            method="pdf-image-manual-review",
            source="upload",
            document_hash=digest,
            pages=pages,
            ocr_attempted=True,
            warnings=warnings,
        )
    result = extract_text(ocr_text, source="upload", digest=digest, method="pdf-ocr")
    result.pages = pages
    result.ocr_attempted = True
    result.warnings = warnings + result.warnings
    result.fields.warnings = warnings + result.fields.warnings
    return result


def extract_structured(payload: dict[str, Any], *, source: str = "structured", digest: str | None = None) -> ExtractionResult:
    fields = InvoiceFields.model_validate(payload)
    canonical = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return ExtractionResult(
        fields=fields,
        method="structured-json",
        source=source,
        document_hash=digest or hashlib.sha256(canonical).hexdigest(),
    )


def normalize_name(value: str | None) -> str:
    return _normalized_key(value or "")


def normalize_invoice_number(value: str | None) -> str:
    return _normalized_key(value or "")
