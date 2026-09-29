"""Streamlit operations surface for invoice decisions."""

from __future__ import annotations

import json

import streamlit as st

from src.fixtures import list_scenarios, scenario
from src.models import Decision
from src.service import InvoiceDecisionEngine


st.set_page_config(page_title="Invoice Decision Engine", page_icon="🧾", layout="wide")


@st.cache_resource
def get_engine() -> InvoiceDecisionEngine:
    return InvoiceDecisionEngine()


def show_decision(decision: Decision) -> None:
    colors = {"APPROVE": "green", "APPROVE_WITH_VARIANCE": "orange", "MANUAL_REVIEW": "orange", "REJECT": "red"}
    color = colors.get(decision.status.value, "gray")
    st.markdown(f"## :{color}[{decision.status.value.replace('_', ' ')}]")
    st.write(decision.reason)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Decision ID", decision.id)
    c2.metric("Vendor", decision.vendor.name if decision.vendor else "Unknown")
    c3.metric("PO", decision.purchase_order.po_number if decision.purchase_order else "Unmatched")
    c4.metric("Invoice total", str(decision.extraction.fields.total or "—"))

    tabs = st.tabs(["Extraction", "Rules", "Audit trail", "JSON"])
    with tabs[0]:
        fields = decision.extraction.fields.model_dump(mode="json")
        st.json(fields)
        if decision.extraction.warnings:
            for warning in decision.extraction.warnings:
                st.warning(warning)
    with tabs[1]:
        st.dataframe(
            [
                {"Rule": check.name, "State": check.state.value, "Result": check.message}
                for check in decision.rule_checks
            ],
            use_container_width=True,
            hide_index=True,
        )
    with tabs[2]:
        for event in decision.audit_events:
            st.write(f"**{event.at}** · `{event.name}` · {event.message}")
    with tabs[3]:
        st.code(decision.model_dump_json(indent=2), language="json")


engine = get_engine()
st.title("Invoice Decision Engine")
st.caption("Extract, validate, match, and explain invoice decisions without opaque approval logic.")

with st.sidebar:
    st.header("Demo controls")
    if st.button("Reset demo data", use_container_width=True):
        engine.reset_demo()
        st.session_state.pop("last_decision", None)
        st.success("Seeded data restored.")
    st.divider()
    st.header("Decision history")
    history = engine.list_decisions()
    if history:
        selected_id = st.selectbox(
            "Open a previous decision",
            options=[item.id for item in history],
            format_func=lambda value: next((f"{item.status.value} · {value}" for item in history if item.id == value), value),
        )
left, right = st.columns([1, 1.3])
with left:
    st.subheader("Process an invoice")
    scenarios = list_scenarios()
    scenario_labels = {item.name: item.key for item in scenarios}
    selected_label = st.selectbox("Try a seeded scenario", list(scenario_labels))
    selected = scenario(scenario_labels[selected_label])
    st.caption(selected.description)
    if st.button("Process selected scenario", type="primary", use_container_width=True):
        if selected.filename.lower().endswith(".pdf"):
            st.session_state.last_decision = engine.process_document(
                selected.document_text.encode("utf-8"), filename=selected.filename
            )
        else:
            st.session_state.last_decision = engine.process_text(
                selected.document_text, filename=selected.filename, source="demo"
            )

    uploaded = st.file_uploader("Or upload a PDF, text, or structured JSON invoice", type=["pdf", "txt", "json"])
    if uploaded and st.button("Process upload", use_container_width=True):
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
        payload = st.text_area("Invoice JSON", json.dumps(example, indent=2), height=220)
        if st.button("Process JSON", use_container_width=True):
            try:
                st.session_state.last_decision = engine.process_structured(json.loads(payload), filename="invoice.json")
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                st.error(str(exc))

with right:
    st.subheader("Decision explanation")
    if decision := st.session_state.get("last_decision"):
        show_decision(decision)
    else:
        st.info("Process a seeded scenario or upload an invoice to see the complete decision trace.")
