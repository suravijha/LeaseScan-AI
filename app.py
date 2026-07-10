"""
LeaseScan AI

An AI-powered legal document analyzer that performs retrieval-augmented,
multi-agent analysis of lease agreements: it chunks and embeds the lease,
retrieves the most relevant clauses for five specialist agents (financial,
privacy, termination, maintenance, legal), produces evidence-backed flags
with page references and confidence scores, and lets the user chat with
the lease directly. Results can be exported as a PDF audit report, and
past analyses are logged locally for reference.
"""

import streamlit as st
import google.generativeai as genai

from modules import pdf_processor, chunking, history
from modules.vectorstore import LeaseVectorStore, load_embedding_model
from modules.agents import run_full_analysis, AnalysisResult
from modules.qa_chat import answer_question
from modules.report_generator import build_report
from modules.dashboard import category_radar, severity_breakdown

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

st.set_page_config(page_title="LeaseScan AI", layout="wide", page_icon="🛡️")

api_key = st.secrets.get("GEMINI_KEY")
if not api_key:
    st.error("Missing GEMINI_KEY in Streamlit secrets. Add it to .streamlit/secrets.toml.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

history.init_db()

st.markdown(
    """
    <style>
    .stMetric { background-color: #11161c; padding: 15px; border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.15); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛡️ LeaseScan AI")
st.caption("Retrieval-augmented, multi-agent lease risk analysis")


@st.cache_resource(show_spinner=False)
def get_embedding_model():
    return load_embedding_model()


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------

if "result" not in st.session_state:
    st.session_state.result: AnalysisResult | None = None
if "store" not in st.session_state:
    st.session_state.store: LeaseVectorStore | None = None
if "filename" not in st.session_state:
    st.session_state.filename = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --------------------------------------------------------------------------
# Upload + analyze
# --------------------------------------------------------------------------

uploaded_file = st.file_uploader("Drop your lease PDF here", type="pdf")

if uploaded_file and st.button("Run Audit", type="primary"):
    with st.spinner("Extracting text (with OCR fallback for scanned pages)..."):
        pages = pdf_processor.extract_pages(uploaded_file.read())
        used_ocr = pdf_processor.any_ocr_used(pages)

    if not any(p.text.strip() for p in pages):
        st.error("Couldn't extract any text from this PDF, even with OCR. Try a clearer scan.")
        st.stop()

    with st.spinner("Chunking document and building embeddings index..."):
        chunks = chunking.chunk_pages(pages)
        embed_model = get_embedding_model()
        store = LeaseVectorStore.build(chunks, embed_model)

    with st.spinner("Running multi-agent analysis (financial, privacy, termination, maintenance, legal)..."):
        result = run_full_analysis(model, store, used_ocr=used_ocr)

    history.record_analysis(
        filename=uploaded_file.name,
        overall_score=result.overall_score,
        flag_count=len(result.all_flags),
        summary=result.summary,
    )

    st.session_state.result = result
    st.session_state.store = store
    st.session_state.filename = uploaded_file.name
    st.session_state.chat_history = []

# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

result = st.session_state.result

if result:
    if result.used_ocr:
        st.info("This document contained scanned pages - OCR was used to extract that text.")

    tab_overview, tab_findings, tab_chat, tab_history = st.tabs(
        ["📊 Overview", "🔍 Findings & Evidence", "💬 Ask the Lease", "🕑 History"]
    )

    # ---- Overview tab ----
    with tab_overview:
        col1, col2, col3 = st.columns(3)
        col1.metric("Overall Score", f"{result.overall_score}/100")
        col2.metric("Red Flags Found", len(result.all_flags))
        col3.metric("Status", "Review Required" if result.overall_score < 70 else "Safe")

        st.write(result.summary)
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Category Risk Radar")
            st.plotly_chart(category_radar(result), use_container_width=True)
        with c2:
            st.subheader("Flags by Severity")
            st.plotly_chart(severity_breakdown(result), use_container_width=True)

        st.divider()
        report_bytes = build_report(result, source_filename=st.session_state.filename or "lease.pdf")
        st.download_button(
            "📄 Download Full Audit Report (PDF)",
            data=report_bytes,
            file_name=f"leasescan_report_{(st.session_state.filename or 'lease').rsplit('.', 1)[0]}.pdf",
            mime="application/pdf",
        )

    # ---- Findings tab ----
    with tab_findings:
        for agent in result.agents:
            st.subheader(f"{agent.agent_name}  ·  {agent.category_score}/100")
            if not agent.flags:
                st.success("No significant issues found in this category.")
                continue
            for flag in agent.flags:
                icon = {"HIGH": "🔴", "MED": "🟡", "LOW": "🟢"}.get(flag.level, "⚪")
                with st.expander(f"{icon} {flag.issue} ({flag.level}) · confidence {flag.confidence}%"):
                    st.write(flag.risk)
                    if flag.evidence_quote:
                        st.markdown(f"**Evidence (Page {flag.evidence_page}):** _{flag.evidence_quote}_")
                    if flag.recommendation:
                        st.markdown(f"**Recommendation:** {flag.recommendation}")
            st.divider()

    # ---- Chat tab ----
    with tab_chat:
        st.write("Ask anything about this lease - answers are grounded in the actual document text.")

        for role, msg in st.session_state.chat_history:
            with st.chat_message(role):
                st.write(msg)

        question = st.chat_input("e.g. Can my landlord increase rent mid-lease?")
        if question:
            st.session_state.chat_history.append(("user", question))
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                with st.spinner("Searching the lease..."):
                    answer = answer_question(model, st.session_state.store, question)
                st.write(answer)
            st.session_state.chat_history.append(("assistant", answer))

    # ---- History tab ----
    with tab_history:
        past = history.get_history()
        if not past:
            st.write("No past analyses yet.")
        else:
            st.dataframe(past, use_container_width=True, hide_index=True)

else:
    st.info("Upload a lease PDF and click **Run Audit** to get started.")
