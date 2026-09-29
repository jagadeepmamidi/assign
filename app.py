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
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    .stApp { background: #f7f6f3; color: #202522; font-family: Aptos, system-ui, sans-serif; border: 0 !important; }
    [data-testid="stAppViewContainer"] { background: #f7f6f3; border: 0 !important; }
    [data-testid="stHeader"] { background: rgba(247, 246, 243, 0.94); border: 0 !important; }
    [data-testid="stSidebar"] { background: #efeee9; border-right: 1px solid #dfddd7; }
    [data-testid="stSidebarContent"] { padding: 1.4rem 1.1rem; }
    .block-container { max-width: 1220px; padding: 2.5rem 2.2rem 4.5rem; }
    h1, h2, h3 { color: #202522; letter-spacing: -0.025em; }
    h1 { font-size: clamp(2rem, 4vw, 3.15rem) !important; line-height: 1.02 !important; margin: 0 0 0.55rem !important; }
    h2 { font-size: 1.5rem !important; }
    h3 { font-size: 1.05rem !important; }
    p, label, [data-testid="stCaptionContainer"] { color: #59615d; }
    .workflow-label { color: #8a4d32; font-size: 0.72rem; font-weight: 800; letter-spacing: 0.13em; text-transform: uppercase; margin-bottom: 0.55rem; }
    .subtitle { max-width: 680px; color: #59615d; font-size: 1rem; line-height: 1.6; margin: 0 0 1.65rem; }
    .section-copy { color: #69716c; font-size: 0.9rem; line-height: 1.5; max-width: 65ch; }
    [data-testid="stVerticalBlockBorderWrapper"] { background: transparent; border: 0 !important; box-shadow: none !important; border-radius: 0; }
    [data-testid="stMetric"] { background: #fff; border: 0 !important; border-radius: 0; box-shadow: inset 0 -1px 0 #dfddd7; padding: 0.85rem 1rem; min-height: 92px; }
    [data-testid="stMetricLabel"] { color: #69716c; }
    [data-testid="stMetricValue"] { color: #202522; font-variant-numeric: tabular-nums; }
    [data-testid="stFileUploader"] { background: #faf9f7; border: 1px dashed #b9b6ae; border-radius: 8px; padding: 0.3rem; }
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] {
        min-height: 2.65rem; border-radius: 6px; font-weight: 700; font-size: 0.92rem;
        transition: background-color 160ms ease, border-color 160ms ease, transform 160ms ease;
    }
    [data-testid="stBaseButton-primary"] { background: #202522; border-color: #202522; color: #fff; }
    [data-testid="stBaseButton-primary"]:hover { background: #343b37; border-color: #343b37; transform: translateY(-1px); }
    [data-testid="stBaseButton-primary"]:disabled,
    [data-testid="stBaseButton-secondary"]:disabled {
        background: #e6e4de; border-color: #d0cdc4; color: #6f746f; opacity: 1; cursor: not-allowed;
    }
    [data-testid="stBaseButton-secondary"] { background: #fff; border-color: #c4c1b9; color: #202522; }
    [data-testid="stBaseButton-secondary"]:hover { background: #f0efeb; border-color: #202522; transform: translateY(-1px); }
    button:focus-visible, input:focus-visible, textarea:focus-visible, [tabindex="0"]:focus-visible {
        outline: 2px solid #8a4d32 !important; outline-offset: 2px !important;
    }
    [data-baseweb="select"] > div {
        background: #fff !important; border: 1px solid #c4c1b9 !important; border-radius: 6px !important;
        color: #202522 !important; box-shadow: none !important;
    }
    [data-baseweb="select"] input, [data-baseweb="select"] [data-testid="stMarkdownContainer"],
    [data-baseweb="select"] span { color: #202522 !important; }
    [data-baseweb="input"] > div, textarea {
        background: #fff !important; border: 1px solid #c4c1b9 !important; border-radius: 6px !important;
        box-shadow: none !important;
    }
    .status-panel { border-radius: 8px; padding: 1.05rem 1.15rem; margin: 0.1rem 0 1.1rem; border: 1px solid; }
    .status-panel h2 { margin: 0.2rem 0 0.35rem; font-size: 1.45rem !important; }
    .status-panel p { margin: 0; line-height: 1.5; }
    .status-panel.approve { background: #edf3ec; border-color: #9eb89e; }
    .status-panel.variance { background: #fbf3db; border-color: #d4bc73; }
    .status-panel.review { background: #fff4e5; border-color: #d6a468; }
    .status-panel.reject { background: #fdebec; border-color: #d69ca2; }
    .status-label { color: #59615d; font-size: 0.7rem; font-weight: 800; letter-spacing: 0.11em; text-transform: uppercase; }
    .field-card { background: #faf9f7; border: 1px solid #e5e3de; border-radius: 6px; padding: 0.65rem 0.75rem; min-height: 70px; margin-bottom: 0.55rem; }
    .field-label { color: #69716c; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; }
    .field-value { color: #202522; font-size: 0.95rem; font-weight: 650; margin-top: 0.25rem; overflow-wrap: anywhere; }
    .timeline { border-left: 2px solid #d9d7d0; padding-left: 0.95rem; margin: 0.4rem 0 0.75rem 0.4rem; }
    .timeline-event { position: relative; padding: 0 0 0.9rem 0.2rem; }
    .timeline-event::before { content: ""; position: absolute; width: 7px; height: 7px; border-radius: 50%; background: #8a4d32; left: -1.3rem; top: 0.33rem; }
    .timeline-name { color: #202522; font-weight: 700; }
    .timeline-time { color: #7c837f; font-size: 0.75rem; margin-left: 0.45rem; }
    .timeline-message { color: #59615d; margin-top: 0.2rem; line-height: 1.45; }
    .utility-note { color: #69716c; font-size: 0.82rem; line-height: 1.45; }
    @media (prefers-reduced-motion: reduce) {
        [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] { transition: none; }
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
        DecisionStatus.APPROVE: ("Approved", "approve", "Payment controls passed."),
        DecisionStatus.APPROVE_WITH_VARIANCE: ("Approved with variance", "variance", "Payment controls passed with a documented variance."),
        DecisionStatus.MANUAL_REVIEW: ("Manual review", "review", "A person must resolve the blocking evidence before payment."),
        DecisionStatus.REJECT: ("Rejected", "reject", "The invoice failed a hard payment control."),
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
    for warning in warnings:
        st.warning(warning, icon="!")


def show_decision(decision: Decision) -> None:
    label, panel_class, summary = _status_meta(decision.status)
    st.markdown(
        f'<div class="status-panel {panel_class}" role="status" aria-live="polite">'
        f'<div class="status-label">{summary}</div><h2>{label}</h2><p>{decision.reason}</p></div>',
        unsafe_allow_html=True,
    )
    fields = decision.extraction.fields
    metrics = st.columns(3)
    metrics[0].metric("Vendor", _display(decision.vendor.name if decision.vendor else None))
    metrics[1].metric("PO match", _display(decision.purchase_order.po_number if decision.purchase_order else None))
    metrics[2].metric("Invoice total", _display(fields.total))
    st.caption(f"Decision {decision.id} · {decision.created_at}")

    extraction_tab, rules_tab, audit_tab, json_tab = st.tabs(["Fields", "Rules", "Audit", "JSON"])
    with extraction_tab:
        st.subheader("Normalized fields")
        _render_field_grid(fields)
        st.caption(
            f"Extraction method: {decision.extraction.method} · Source: {decision.extraction.source} · "
            f"Pages: {decision.extraction.pages} · OCR attempted: {'yes' if decision.extraction.ocr_attempted else 'no'}"
        )
        confidence_rows = [
            {"Field": name.replace("_", " ").title(), "Value": _display(getattr(fields, name)), "Confidence": f"{confidence:.0%}"}
            for name, confidence in fields.confidence.items()
        ]
        if confidence_rows:
            st.subheader("Field confidence")
            st.dataframe(confidence_rows, use_container_width=True, hide_index=True)
        _render_warnings(decision.extraction.warnings)
    with rules_tab:
        st.dataframe(
            [{"Rule": check.name, "State": check.state.value, "Result": check.message} for check in decision.rule_checks],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rule": st.column_config.TextColumn("Rule", width="medium"),
                "State": st.column_config.TextColumn("State", width="small"),
            },
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
    st.markdown("**Invoice Decision Engine**")
    st.markdown('<p class="utility-note">Utilities are kept here so the main workflow stays focused.</p>', unsafe_allow_html=True)
    with st.expander("Demo reset"):
        st.caption("Restore seeded vendors, POs, split-invoice history, and duplicate history.")
        if st.button("Reset seeded data", use_container_width=True):
            engine.reset_demo()
            st.session_state.pop("last_decision", None)
            st.rerun()
    st.caption(f"{len(history)} saved decision(s)")

st.markdown('<div class="workflow-label">Accounts payable workflow</div>', unsafe_allow_html=True)
st.title("Invoice Decision Engine")
st.markdown(
    '<p class="subtitle">Turn an invoice document into a reasoned payment decision. Review the evidence, then act on the result.</p>',
    unsafe_allow_html=True,
)

summary = st.columns(3)
summary[0].metric("Saved decisions", len(history))
summary[1].metric("Needs review", sum(item.status == DecisionStatus.MANUAL_REVIEW for item in history))
summary[2].metric("Latest result", history[0].status.value.replace("_", " ") if history else "No activity")

st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
with st.container():
    st.subheader("Process an invoice")
    st.markdown('<p class="section-copy">Choose one action. Demo data is reproducible; uploaded files use the same decision engine.</p>', unsafe_allow_html=True)
    demo_column, upload_column = st.columns(2, gap="large")

    with demo_column:
        st.markdown("#### Try a seeded scenario")
        scenarios = list_scenarios()
        scenario_labels = {item.name: item.key for item in scenarios}
        selected_label = st.selectbox("Demo scenario", list(scenario_labels))
        selected = scenario(scenario_labels[selected_label])
        st.caption(selected.description)
        if st.button("Run selected scenario", type="primary", use_container_width=True):
            if selected.filename.lower().endswith(".pdf"):
                st.session_state.last_decision = engine.process_document(selected.document_text.encode("utf-8"), filename=selected.filename)
            else:
                st.session_state.last_decision = engine.process_text(selected.document_text, filename=selected.filename, source="demo")

    with upload_column:
        st.markdown("#### Upload an invoice")
        uploaded = st.file_uploader("Invoice document", type=["pdf", "txt", "json"], help="PDF, text, or structured JSON")
        if uploaded:
            st.caption(f"Selected: {uploaded.name} · {uploaded.size / 1024:.1f} KB")
        if st.button("Review uploaded invoice", use_container_width=True, disabled=uploaded is None):
            if uploaded:
                st.session_state.last_decision = engine.process_document(uploaded.getvalue(), filename=uploaded.name)

with st.expander("Use structured JSON instead"):
    st.caption("Use this only when a source system already provides normalized invoice fields.")
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
    payload = st.text_area("Invoice JSON", json.dumps(example, indent=2), height=220)
    if st.button("Review JSON invoice", use_container_width=True):
        try:
            st.session_state.last_decision = engine.process_structured(json.loads(payload), filename="invoice.json")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            st.error(f"Could not process JSON: {exc}")

st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
with st.container():
    st.subheader("Decision explanation")
    decision = st.session_state.get("last_decision")
    if decision:
        show_decision(decision)
    else:
        st.markdown('<p class="section-copy">The result appears here after you run one of the actions above. Nothing is hidden behind a separate page.</p>', unsafe_allow_html=True)
        st.info("No invoice processed yet.", icon="ℹ️")

if history:
    with st.expander(f"Recent decisions ({len(history)})"):
        st.dataframe(
            [
                {"Status": item.status.value.replace("_", " "), "Decision": item.id, "Vendor": _display(item.vendor.name if item.vendor else None), "PO": _display(item.purchase_order.po_number if item.purchase_order else None), "Reason": item.reason}
                for item in history
            ],
            use_container_width=True,
            hide_index=True,
        )
