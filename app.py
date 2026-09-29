"""Streamlit operations surface for invoice decisions."""

from __future__ import annotations

import json
from collections.abc import Iterable

import streamlit as st

from src.fixtures import list_scenarios, scenario
from src.models import Decision, DecisionStatus
from src.service import InvoiceDecisionEngine


st.set_page_config(
    page_title="Invoice Decision Engine",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    .stApp { background: #0b0f17; }
    [data-testid="stAppViewContainer"] { background: #0b0f17; }
    [data-testid="stHeader"] { background: rgba(11, 15, 23, 0.9); }
    [data-testid="stSidebar"] { background: #101622; border-right: 1px solid #263044; }
    [data-testid="stSidebarContent"] { padding: 1.5rem 1.1rem; }
    .block-container { max-width: 1440px; padding: 2.5rem 3rem 4rem; }
    h1, h2, h3 { letter-spacing: -0.02em; }
    h1 { font-size: 2.25rem !important; margin-bottom: 0.35rem !important; }
    h2 { font-size: 1.4rem !important; }
    h3 { font-size: 1.05rem !important; }
    [data-testid="stMetric"] {
        background: #131a27; border: 1px solid #263044; border-radius: 12px;
        padding: 1rem 1.1rem; min-height: 108px;
    }
    [data-testid="stMetricLabel"] { color: #93a0b5; }
    [data-testid="stMetricValue"] { color: #f3f6fb; font-variant-numeric: tabular-nums; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #263044; border-radius: 16px; background: #101622;
    }
    [data-testid="stFileUploader"] {
        background: #131a27; border: 1px dashed #4a5a76; border-radius: 12px; padding: 0.35rem;
    }
    [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] {
        min-height: 2.7rem; border-radius: 9px; font-weight: 650;
        transition: background-color 160ms ease, border-color 160ms ease, transform 160ms ease;
    }
    [data-testid="stBaseButton-primary"] { background: #5b5ce2; border-color: #7778f0; }
    [data-testid="stBaseButton-primary"]:hover { background: #7273ef; border-color: #9a9bf8; transform: translateY(-1px); }
    [data-testid="stBaseButton-secondary"]:hover { border-color: #818cf8; background: #1a2335; transform: translateY(-1px); }
    button:focus-visible, input:focus-visible, textarea:focus-visible, [tabindex="0"]:focus-visible {
        outline: 2px solid #a5b4fc !important; outline-offset: 2px !important;
    }
    .eyebrow { color: #8b93ff; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 0.4rem; }
    .subtitle { color: #aab5c8; max-width: 760px; font-size: 1.02rem; line-height: 1.55; }
    .brand-mark { color: #a5b4fc; font-weight: 800; letter-spacing: 0.06em; font-size: 0.85rem; text-transform: uppercase; }
    .brand-note { color: #8190aa; font-size: 0.77rem; line-height: 1.4; margin-top: 0.35rem; }
    .status-panel { border-radius: 14px; padding: 1.15rem 1.25rem; margin: 0.25rem 0 1rem; border: 1px solid; }
    .status-panel h2 { margin: 0.2rem 0 0.35rem; font-size: 1.55rem !important; }
    .status-panel p { color: #c9d2e2; margin: 0; line-height: 1.5; }
    .status-panel.approve { background: #10271f; border-color: #2b8a67; }
    .status-panel.variance { background: #2c2412; border-color: #b58a32; }
    .status-panel.review { background: #2a2113; border-color: #b8792f; }
    .status-panel.reject { background: #2d171d; border-color: #b65363; }
    .status-label { color: #d7deeb; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.13em; text-transform: uppercase; }
    .field-card { background: #131a27; border: 1px solid #263044; border-radius: 10px; padding: 0.7rem 0.8rem; min-height: 76px; margin-bottom: 0.6rem; }
    .field-label { color: #8997ae; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.07em; }
    .field-value { color: #f3f6fb; font-size: 0.98rem; font-weight: 650; margin-top: 0.28rem; overflow-wrap: anywhere; }
    .timeline { border-left: 2px solid #35415a; padding-left: 1rem; margin: 0.4rem 0 0.75rem 0.45rem; }
    .timeline-event { position: relative; padding: 0 0 1rem 0.2rem; }
    .timeline-event::before { content: ""; position: absolute; width: 8px; height: 8px; border-radius: 50%; background: #818cf8; left: -1.36rem; top: 0.32rem; }
    .timeline-name { color: #e5e9f2; font-weight: 700; }
    .timeline-time { color: #8190aa; font-size: 0.76rem; margin-left: 0.45rem; }
    .timeline-message { color: #aab5c8; margin-top: 0.2rem; line-height: 1.45; }
    .section-help { color: #8997ae; font-size: 0.83rem; line-height: 1.45; }
    @media (prefers-reduced-motion: reduce) {
        [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] { transition: none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_engine() -> InvoiceDecisionEngine:
    return InvoiceDecisionEngine()


def _display(value: object | None) -> str:
    return "—" if value is None or value == "" else str(value)


def _status_meta(status: DecisionStatus) -> tuple[str, str, str]:
    metadata = {
        DecisionStatus.APPROVE: ("APPROVED", "approve", "Payment controls passed."),
        DecisionStatus.APPROVE_WITH_VARIANCE: ("APPROVED WITH VARIANCE", "variance", "Payment controls passed with a documented variance."),
        DecisionStatus.MANUAL_REVIEW: ("MANUAL REVIEW", "review", "A person must resolve the blocking evidence before payment."),
        DecisionStatus.REJECT: ("REJECTED", "reject", "The invoice failed a hard payment control."),
    }
    return metadata[status]


def _field_card(label: str, value: object | None) -> str:
    return f'<div class="field-card"><div class="field-label">{label}</div><div class="field-value">{_display(value)}</div></div>'


def _render_field_grid(fields) -> None:
    values = [
        ("Vendor", fields.vendor_name),
        ("Invoice number", fields.invoice_number),
        ("Invoice date", fields.invoice_date),
        ("PO reference", fields.po_reference),
        ("Currency", fields.currency),
        ("Subtotal", fields.subtotal),
        ("Tax", fields.tax),
        ("Total", fields.total),
    ]
    columns = st.columns(2)
    for index, (label, value) in enumerate(values):
        with columns[index % 2]:
            st.markdown(_field_card(label, value), unsafe_allow_html=True)


def _render_warnings(warnings: Iterable[str]) -> None:
    warning_list = list(warnings)
    if not warning_list:
        return
    st.markdown("#### Extraction notes")
    for warning in warning_list:
        st.warning(warning, icon="!")


def show_decision(decision: Decision) -> None:
    label, panel_class, summary = _status_meta(decision.status)
    st.markdown(
        f'<div class="status-panel {panel_class}" role="status" aria-live="polite">'
        f'<div class="status-label">{summary}</div><h2>{label}</h2><p>{decision.reason}</p></div>',
        unsafe_allow_html=True,
    )

    fields = decision.extraction.fields
    metrics = st.columns(4)
    metrics[0].metric("Decision ID", decision.id)
    metrics[1].metric("Vendor", _display(decision.vendor.name if decision.vendor else None))
    metrics[2].metric("PO match", _display(decision.purchase_order.po_number if decision.purchase_order else None))
    metrics[3].metric("Invoice total", _display(fields.total))

    st.markdown('<div class="eyebrow" style="margin-top:1.4rem">Evidence & trace</div>', unsafe_allow_html=True)
    extraction_tab, rules_tab, audit_tab, json_tab = st.tabs(["Extraction", "Rule checks", "Audit trail", "Raw JSON"])
    with extraction_tab:
        st.markdown("#### Normalized fields")
        _render_field_grid(fields)
        meta = st.columns(4)
        meta[0].metric("Method", decision.extraction.method)
        meta[1].metric("Source", decision.extraction.source)
        meta[2].metric("Pages", decision.extraction.pages)
        meta[3].metric("OCR attempted", "Yes" if decision.extraction.ocr_attempted else "No")
        confidence_rows = [
            {"Field": name.replace("_", " ").title(), "Value": _display(getattr(fields, name)), "Confidence": f"{confidence:.0%}"}
            for name, confidence in fields.confidence.items()
        ]
        if confidence_rows:
            st.markdown("#### Field confidence")
            st.dataframe(confidence_rows, use_container_width=True, hide_index=True)
        _render_warnings(decision.extraction.warnings)
    with rules_tab:
        st.dataframe(
            [{"Rule": check.name, "State": check.state.value, "Result": check.message} for check in decision.rule_checks],
            use_container_width=True,
            hide_index=True,
            column_config={"Rule": st.column_config.TextColumn("Rule", width="medium"), "State": st.column_config.TextColumn("State", width="small")},
        )
    with audit_tab:
        st.markdown('<div class="timeline">', unsafe_allow_html=True)
        for event in decision.audit_events:
            st.markdown(
                f'<div class="timeline-event"><span class="timeline-name">{event.name}</span>'
                f'<span class="timeline-time">{event.at}</span><div class="timeline-message">{event.message}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    with json_tab:
        st.code(decision.model_dump_json(indent=2), language="json")


engine = get_engine()
history = engine.list_decisions()

with st.sidebar:
    st.markdown('<div class="brand-mark">Invoice Decision Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-note">A transparent invoice-to-decision workspace for AP review.</div>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="eyebrow">Workspace</div>', unsafe_allow_html=True)
    st.caption(f"{len(history)} saved decision(s)")
    if st.button("Reset demo data", use_container_width=True, help="Restore seeded vendors, POs, and demonstration history"):
        engine.reset_demo()
        st.session_state.pop("last_decision", None)
        st.rerun()
    if history:
        history_options = {item.id: item for item in history}
        selected_id = st.selectbox(
            "Open a previous decision",
            options=list(history_options),
            format_func=lambda value: f"{history_options[value].status.value.replace('_', ' ')} · {value}",
        )
        if st.button("Open selected decision", use_container_width=True):
            st.session_state.last_decision = history_options[selected_id]

st.markdown('<div class="eyebrow">Accounts payable operations</div>', unsafe_allow_html=True)
st.title("Invoice Decision Engine")
st.markdown(
    '<p class="subtitle">Turn an invoice document into a reasoned payment decision. Every extracted field, rule result, and review event stays visible.</p>',
    unsafe_allow_html=True,
)

summary = st.columns(3)
summary[0].metric("Saved decisions", len(history))
summary[1].metric("Needs review", sum(item.status == DecisionStatus.MANUAL_REVIEW for item in history))
summary[2].metric("Latest result", history[0].status.value.replace("_", " ") if history else "No activity")

st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
input_column, output_column = st.columns([0.9, 1.35], gap="large")

with input_column:
    with st.container(border=True):
        st.markdown('<div class="eyebrow">1 · Start processing</div>', unsafe_allow_html=True)
        st.subheader("Choose a demo or upload an invoice")
        st.markdown('<p class="section-help">Use a seeded scenario to explore the rules, or upload a PDF, text invoice, or structured JSON document.</p>', unsafe_allow_html=True)

        scenarios = list_scenarios()
        scenario_labels = {item.name: item.key for item in scenarios}
        selected_label = st.selectbox("Demo scenario", list(scenario_labels), label_visibility="visible")
        selected = scenario(scenario_labels[selected_label])
        st.caption(selected.description)
        if st.button("Process demo scenario", type="primary", use_container_width=True):
            if selected.filename.lower().endswith(".pdf"):
                st.session_state.last_decision = engine.process_document(selected.document_text.encode("utf-8"), filename=selected.filename)
            else:
                st.session_state.last_decision = engine.process_text(selected.document_text, filename=selected.filename, source="demo")

        st.markdown("<div style='height: 0.35rem'></div>", unsafe_allow_html=True)
        uploaded = st.file_uploader("Invoice document", type=["pdf", "txt", "json"], help="PDF, text, or structured JSON")
        if uploaded:
            st.caption(f"Selected: {uploaded.name} · {uploaded.size / 1024:.1f} KB")
        if st.button("Process uploaded invoice", use_container_width=True, disabled=uploaded is None):
            if uploaded:
                st.session_state.last_decision = engine.process_document(uploaded.getvalue(), filename=uploaded.name)

        with st.expander("Structured JSON fallback"):
            example = {
                "vendor_name": "Acme Industrial Supplies",
                "invoice_number": "INV-JSON-001",
                "invoice_date": "2026-09-20",
                "po_reference": "PO-1001",
                "currency": "USD",
                "subtotal": "9.25",
                "tax": "0.75",
                "total": "10.00",
                "confidence": {"vendor_name": 0.99, "invoice_number": 0.99, "invoice_date": 0.99, "currency": 0.99, "total": 0.99},
            }
            payload = st.text_area("Invoice JSON", json.dumps(example, indent=2), height=220, label_visibility="visible")
            if st.button("Process JSON", use_container_width=True):
                try:
                    st.session_state.last_decision = engine.process_structured(json.loads(payload), filename="invoice.json")
                except (ValueError, TypeError, json.JSONDecodeError) as exc:
                    st.error(f"Could not process JSON: {exc}")

with output_column:
    with st.container(border=True):
        st.markdown('<div class="eyebrow">2 · Review decision</div>', unsafe_allow_html=True)
        decision = st.session_state.get("last_decision")
        if decision:
            show_decision(decision)
        else:
            st.subheader("Your decision will appear here")
            st.markdown(
                '<p class="section-help">Run a scenario or upload an invoice to see the status, matching evidence, rule checks, and full audit trail.</p>',
                unsafe_allow_html=True,
            )
            st.info("No invoice processed yet.", icon="ℹ️")
