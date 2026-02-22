import streamlit as st
import sys
import os
import tempfile
import time

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

    .agent-active {
        background-color: #1e1e2e;
        border: 1px solid #cba6f7;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        color: #cdd6f4;
    }

    .agent-done {
        background-color: #1e1e2e;
        border: 1px solid #a6e3a1;
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

    .report-section {
        background-color: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 24px;
        color: #cdd6f4;
        line-height: 1.7;
    }

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
if "agent_states" not in st.session_state:
    st.session_state.agent_states = {}

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

# ── Agent definitions ─────────────────────────────────────────────────
AGENTS = [
    ("⚙️", "Agent 1", "Document Processor", "Extracts text from PDF"),
    ("📝", "Agent 2", "Summarizer",          "Generates concise summary"),
    ("🔍", "Agent 3", "Key Info Extractor",  "Pulls dates, parties, amounts"),
    ("⚠️", "Agent 4", "Risk Flagger",         "Identifies risks and red flags"),
    ("📊", "Agent 5", "Report Generator",     "Creates final structured report"),
]

def render_agents(active_idx=None, done_up_to=None):
    """Render agent pipeline with live status indicators."""
    for i, (icon, tag, name, desc) in enumerate(AGENTS):
        if done_up_to is not None and i < done_up_to:
            css   = "agent-done"
            badge = "✅"
        elif active_idx is not None and i == active_idx:
            css   = "agent-active"
            badge = "🔄"
        else:
            css   = "agent-card"
            badge = icon

        st.markdown(f"""
        <div class="{css}">
            <strong>{badge} {name}</strong><br>
            <small style="color: #6c7086;">{desc}</small>
        </div>
        """, unsafe_allow_html=True)

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
                # Save to temp file keeping original name
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".pdf"
                ) as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                st.markdown("### 🤖 Agent Pipeline")
                agent_placeholder = st.empty()

                # Simulate live agent progress
                for i in range(len(AGENTS)):
                    with agent_placeholder.container():
                        render_agents(active_idx=i, done_up_to=i)
                    if i < len(AGENTS) - 1:
                        time.sleep(0.3)

                # Run the actual pipeline
                with st.spinner(""):
                    result = process_document(tmp_path, uploaded_file.name)
                    st.session_state.result = result

                # Show all done
                with agent_placeholder.container():
                    render_agents(done_up_to=len(AGENTS))

                os.unlink(tmp_path)
                st.rerun()

        st.markdown("---")
        st.markdown("### 🤖 Agent Pipeline")
        render_agents()

    with col_result:
        if st.session_state.result:
            result = st.session_state.result
            status = result["status"]

            st.markdown(f"### 📄 {result['filename']}")
            if status == "complete":
                st.markdown(
                    '<span class="status-complete">✅ Analysis Complete</span>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<span class="status-failed">❌ Analysis Failed</span>',
                    unsafe_allow_html=True
                )
                st.error(result.get("error", "Unknown error"))

            if status == "complete":
                res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs([
                    "📋 Full Report",
                    "📝 Summary",
                    "🔍 Key Info",
                    "⚠️ Risks"
                ])

                with res_tab1:
                    st.markdown(
                        f'<div class="report-section">{result["report"]}</div>',
                        unsafe_allow_html=True
                    )
                    st.download_button(
                        label     = "⬇️ Download Report",
                        data      = result["report"],
                        file_name = f"{result['filename']}_report.txt",
                        mime      = "text/plain"
                    )

                with res_tab2:
                    st.markdown(f"""
                    <div class="report-section">
                        {result['summary']}
                    </div>
                    """, unsafe_allow_html=True)

                with res_tab3:
                    st.markdown(
                        f'<div class="report-section">{result["key_info"]}</div>',
                        unsafe_allow_html=True
                    )

                with res_tab4:
                    risks_text = result["risks"]

                    # Parse and color code risk sections
                    sections = {
                        "HIGH RISK":   ("risk-high",   "🔴 High Risk"),
                        "MEDIUM RISK": ("risk-medium", "🟡 Medium Risk"),
                        "LOW RISK":    ("risk-low",    "🟢 Low Risk"),
                    }

                    for key, (css, label) in sections.items():
                        if key in risks_text:
                            start = risks_text.find(key) + len(key)
                            next_keys = [k for k in sections if k != key and k in risks_text[start:]]
                            if next_keys:
                                end = risks_text.find(next_keys[0], start)
                                content = risks_text[start:end].strip()
                            else:
                                content = risks_text[start:].strip()

                            st.markdown(f"""
                            <div class="agent-card {css}">
                                <strong>{label}</strong><br><br>
                                {content}
                            </div>
                            """, unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown("**Full Risk Analysis:**")
                    st.markdown(
                        f'<div class="report-section">{risks_text}</div>',
                        unsafe_allow_html=True
                    )
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
                st.markdown(
                    f'<span class="{status_class}">{entry["status"].upper()}</span>',
                    unsafe_allow_html=True
                )
                if entry["summary"]:
                    st.markdown("**Summary:**")
                    st.markdown(f"""
                    <div class="report-section">
                        {entry['summary']}
                    </div>
                    """, unsafe_allow_html=True)

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