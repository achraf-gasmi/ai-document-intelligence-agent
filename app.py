import streamlit as st
import sys
import os
import tempfile

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.backend import process_document, get_history, get_dashboard_stats

# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Document Intelligence",
    page_icon="📄",
    layout="wide"
)

# ── Custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f1117; }

    .main-header {
        text-align: center;
        padding: 20px 0;
        color: #ffffff;
    }

    .agent-card {
        background-color: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        color: #cdd6f4;
    }

    .risk-high   { border-left: 4px solid #f38ba8; }
    .risk-medium { border-left: 4px solid #fab387; }
    .risk-low    { border-left: 4px solid #a6e3a1; }

    .metric-card {
        background-color: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        color: #cdd6f4;
    }
    .metric-card b {
        display: block;
        font-size: 2em;
        color: #cba6f7;
    }

    .status-complete { color: #a6e3a1; font-weight: bold; }
    .status-failed   { color: #f38ba8; font-weight: bold; }

    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e1e2e;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] { color: #cdd6f4; }
</style>
""", unsafe_allow_html=True)

# ── Initialize session state ──────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None
if "processing" not in st.session_state:
    st.session_state.processing = False

# ── Header ────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📄 AI Document Intelligence Agent</h1>
    <p style="color: #6c7086;">Multi-agent document analysis powered by LangGraph + Groq</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────
tab_analyze, tab_history, tab_stats = st.tabs([
    "🔍 Analyze Document",
    "📋 History",
    "📊 Dashboard"
])

# ══════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYZE
# ══════════════════════════════════════════════════════════════════════
with tab_analyze:
    col_upload, col_result = st.columns([1, 2])

    with col_upload:
        st.markdown("### 📤 Upload Document")
        uploaded_file = st.file_uploader(
            "Upload a PDF document",
            type=["pdf"],
            help="Supports contracts, invoices, reports, agreements"
        )

        if uploaded_file:
            st.success(f"✅ {uploaded_file.name} uploaded")
            st.markdown(f"**Size:** {uploaded_file.size / 1024:.1f} KB")

            if st.button("🚀 Analyze Document", use_container_width=True):
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".pdf",
                    prefix=uploaded_file.name.replace(".pdf", "_")
                ) as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                with st.spinner("🤖 Multi-agent pipeline running..."):
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.info("⚙️ Processing")
                    col2.info("📝 Summarizing")
                    col3.info("🔍 Extracting")
                    col4.info("⚠️ Risk Analysis")
                    col5.info("📊 Reporting")

                    result = process_document(tmp_path)
                    result["filename"] = uploaded_file.name
                    st.session_state.result = result

                os.unlink(tmp_path)
                st.rerun()

        st.markdown("---")
        st.markdown("### 🤖 Agent Pipeline")
        agents = [
            ("⚙️ Agent 1", "Document Processor", "Extracts text from PDF"),
            ("📝 Agent 2", "Summarizer",          "Generates concise summary"),
            ("🔍 Agent 3", "Key Info Extractor",  "Pulls dates, parties, amounts"),
            ("⚠️ Agent 4", "Risk Flagger",         "Identifies risks and red flags"),
            ("📊 Agent 5", "Report Generator",     "Creates final structured report"),
        ]
        for icon, name, desc in agents:
            st.markdown(f"""
            <div class="agent-card">
                <strong>{icon} {name}</strong><br>
                <small style="color: #6c7086;">{desc}</small>
            </div>
            """, unsafe_allow_html=True)

    with col_result:
        if st.session_state.result:
            result = st.session_state.result
            status = result["status"]

            st.markdown(f"### 📄 {result['filename']}")
            if status == "complete":
                st.markdown('<span class="status-complete">✅ Analysis Complete</span>',
                           unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-failed">❌ Analysis Failed</span>',
                           unsafe_allow_html=True)
                st.error(result.get("error", "Unknown error"))

            if status == "complete":
                res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs([
                    "📋 Full Report",
                    "📝 Summary",
                    "🔍 Key Info",
                    "⚠️ Risks"
                ])

                with res_tab1:
                    st.markdown(result["report"])
                    st.download_button(
                        label     = "⬇️ Download Report",
                        data      = result["report"],
                        file_name = f"{result['filename']}_report.txt",
                        mime      = "text/plain"
                    )

                with res_tab2:
                    st.markdown(f"""
                    <div class="agent-card">
                        {result['summary']}
                    </div>
                    """, unsafe_allow_html=True)

                with res_tab3:
                    st.markdown(result["key_info"])

                with res_tab4:
                    risks_text = result["risks"]
                    # Color code risk sections
                    if "HIGH RISK" in risks_text:
                        high = risks_text.split("HIGH RISK")[1].split("MEDIUM")[0] if "MEDIUM" in risks_text else ""
                        st.markdown(f"""
                        <div class="agent-card risk-high">
                            <strong>🔴 High Risk</strong><br>{high}
                        </div>
                        """, unsafe_allow_html=True)
                    if "MEDIUM RISK" in risks_text:
                        medium = risks_text.split("MEDIUM RISK")[1].split("LOW")[0] if "LOW" in risks_text else ""
                        st.markdown(f"""
                        <div class="agent-card risk-medium">
                            <strong>🟡 Medium Risk</strong><br>{medium}
                        </div>
                        """, unsafe_allow_html=True)
                    if "LOW RISK" in risks_text:
                        low = risks_text.split("LOW RISK")[1].split("MISSING")[0] if "MISSING" in risks_text else ""
                        st.markdown(f"""
                        <div class="agent-card risk-low">
                            <strong>🟢 Low Risk</strong><br>{low}
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("**Full Risk Analysis:**")
                    st.markdown(risks_text)
        else:
            st.markdown("""
            <div class="agent-card" style="text-align: center; padding: 60px;">
                <h3>📤 Upload a PDF to get started</h3>
                <p style="color: #6c7086;">
                    Supports contracts, invoices, service agreements, reports and more.
                </p>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 2 — HISTORY
# ══════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown("### 📋 Analysis History")
    history = get_history()

    if history:
        for entry in history:
            with st.expander(f"📄 {entry['filename']} — {entry['timestamp']}"):
                status_class = "status-complete" if entry["status"] == "complete" else "status-failed"
                st.markdown(f'<span class="{status_class}">{entry["status"].upper()}</span>',
                           unsafe_allow_html=True)

                if entry["summary"]:
                    st.markdown("**Summary:**")
                    st.markdown(entry["summary"])

                if entry["report"]:
                    st.download_button(
                        label     = "⬇️ Download Report",
                        data      = entry["report"],
                        file_name = f"{entry['filename']}_report.txt",
                        mime      = "text/plain",
                        key       = f"dl_{entry['id']}"
                    )
    else:
        st.info("💡 No analyses yet — upload a document to get started!")

# ══════════════════════════════════════════════════════════════════════
# TAB 3 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════
with tab_stats:
    st.markdown("### 📊 Dashboard")
    stats = get_dashboard_stats()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            📄<b>{stats['total']}</b>Total Analyses
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            ✅<b>{stats['successful']}</b>Successful
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            ❌<b>{stats['failed']}</b>Failed
        </div>""", unsafe_allow_html=True)

    if stats["recent"]:
        st.markdown("### 🕓 Recently Analyzed")
        for filename in stats["recent"]:
            st.markdown(f"- 📄 `{filename}`")