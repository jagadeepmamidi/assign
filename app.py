"""Streamlit bonus UI for TAMs and support agents."""

from __future__ import annotations

import os
import time
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Zycus Support AI", page_icon="🛠️", layout="wide")

# On Streamlit Community Cloud, keys live in st.secrets rather than the process
# environment; mirror them into os.environ before src.config reads it at import.
# Only touch st.secrets when a secrets file exists, otherwise Streamlit paints
# a "No secrets found" banner into the page on local runs.
_secret_files = (
    Path.home() / ".streamlit" / "secrets.toml",
    Path(__file__).resolve().parent / ".streamlit" / "secrets.toml",
)
if any(f.exists() for f in _secret_files):
    for _key, _value in st.secrets.items():
        if isinstance(_value, str) and _key not in os.environ:
            os.environ[_key] = _value

from src.account_brief import build_account_brief
from src.data_loader import load_accounts
from src.retrieval import get_retriever
from src.triage import stream_draft, triage_ticket


@st.cache_resource
def resources():
    return get_retriever(), load_accounts()


retriever, accounts = resources()
tab_triage, tab_brief = st.tabs(["Ticket Triage", "Account Brief"])

with tab_triage:
    st.header("Ticket triage")
    subject = st.text_input("Subject")
    body = st.text_area("Ticket body", height=180)
    if st.button("Triage ticket", type="primary"):
        try:
            result = triage_ticket(subject, body, retriever=retriever)
            c1, c2, c3 = st.columns(3)
            c1.metric("Category", result.category)
            c2.metric("Urgency", result.urgency)
            c3.metric("Team", result.recommended_team)
            if result.matched_kb_doc:
                st.subheader("Knowledge-base match")
                st.caption(f"{result.matched_kb_doc.source_file} · {result.matched_kb_doc.section_heading}")
                st.info(result.matched_kb_doc.excerpt)
            st.subheader("Draft first response")
            hits = retriever.search(f"Subject: {subject}\n\nBody: {body}", k=3)
            st.write_stream(stream_draft(subject, body, result, hits))
        except RuntimeError as exc:
            st.error(str(exc))

with tab_brief:
    st.header("Account health brief")
    labels = {f"{a['company']} ({a['account_id']})": a["account_id"] for a in accounts}
    label = st.selectbox("Account", list(labels))
    if st.button("Build brief"):
        try:
            brief = build_account_brief(labels[label])
            markdown = brief.to_markdown()

            def stream_sections():
                # Brief is precomputed and deterministic; stream its delivery only.
                for line in markdown.splitlines(keepends=True):
                    yield line
                    time.sleep(0.02)

            st.write_stream(stream_sections)
        except RuntimeError as exc:
            st.error(str(exc))
