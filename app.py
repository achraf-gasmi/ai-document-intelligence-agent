import streamlit as st
import sys
import os
import tempfile
import time
from fpdf import FPDF

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.backend import process_document, get_history, get_dashboard_stats, ask_document

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
    .main-header { text-align: center; padding: 20px 0; color: #ffffff; }

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
    .metric-card b { display: block; font-size: 2em; color: #cba6f7; }

    .risk-score-high   { color: #f38ba8; font-size: 2.5em; font-weight: bold; }
    .risk-score-medium { color: #fab387; font-size: 2.5em; font-weight: bold; }
    .risk-score-low    { color: #a6e3a1; font-size: 2.5em; font-weight: bold; }

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

    .qa-message-user {
        background-color: #313244;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #cdd6f4;
        text-align: right;
    }
    .qa-message-ai {
        background-color: #1e1e2e;
        border: 1px solid #cba6f7;
        border-radius: 12px;
        padding: 12px 16px;
        margin: 8px 0;
        color: #cdd6f4;
    }

    .suggestion-btn {
        background-color: #1e1e2e;
        border: 1px solid #cba6f7;
        border-radius: 8px;
        padding: 10px;
        color: #cdd6f4;
        cursor: pointer;
        width: 100%;
        text-align: left;
        margin: 4px 0;
    }

    .pipeline-diagram {
        background-color: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        color: #cdd6f4;
    }

    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e1e2e;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] { color: #cdd6f4; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────
if "result"     not in st.session_state: st.session_state.result     = None
if "qa_history" not in st.session_state: st.session_state.qa_history = []

# ── Header ────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📄 AI Document Intelligence Agent</h1>
    <p style="color: #6c7086;">Multi-agent document analysis powered by LangGraph + Groq</p>
</div>
""", unsafe_allow_html=True)
st.divider()

# ── Agent definitions ─────────────────────────────────────────────────
AGENTS = [
    ("⚙️", "Document Processor", "Extracts text from PDF"),
    ("📝", "Summarizer",          "Generates concise summary"),
    ("🔍", "Key Info Extractor",  "Pulls dates, parties, amounts"),
    ("⚠️", "Risk Flagger",         "Identifies risks and red flags"),
    ("📊", "Report Generator",     "Creates final structured report"),
]

def render_agents(active_idx=None, done_up_to=None):
    for i, (icon, name, desc) in enumerate(AGENTS):
        if done_up_to is not None and i < done_up_to:
            css, badge = "agent-done", "✅"
        elif active_idx is not None and i == active_idx:
            css, badge = "agent-active", "🔄"
        else:
            css, badge = "agent-card", icon
        st.markdown(f"""
        <div class="{css}">
            <strong>{badge} {name}</strong><br>
            <small style="color: #6c7086;">{desc}</small>
        </div>
        """, unsafe_allow_html=True)

def get_risk_color(score):
    if score >= 70: return "risk-score-high",   "🔴 High Risk"
    if score >= 40: return "risk-score-medium",  "🟡 Medium Risk"
    return "risk-score-low", "🟢 Low Risk"

def export_to_pdf(result: dict) -> bytes:
    """Generate a PDF report."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Document Analysis Report", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Document: {result['filename']}", ln=True)
    pdf.cell(0, 8, f"Language: {result['language']}", ln=True)
    pdf.cell(0, 8, f"Risk Score: {result['risk_score']}/100", ln=True)
    pdf.ln(5)

    sections = [
        ("SUMMARY",         result["summary"]),
        ("KEY INFORMATION", result["key_info"]),
        ("RISK ANALYSIS",   result["risks"]),
        ("FULL REPORT",     result["report"]),
    ]
    for title, content in sections:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 10, title, ln=True)
        pdf.set_font("Helvetica", "", 10)
        clean = content.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 6, clean)
        pdf.ln(4)

    return pdf.output()

# ── Tabs ──────────────────────────────────────────────────────────────
tab_analyze, tab_qa, tab_pipeline, tab_history, tab_stats = st.tabs([
    "🔍 Analyze",
    "💬 Q&A",
    "🕸️ Pipeline",
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
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                st.markdown("### 🤖 Agent Pipeline")
                agent_placeholder = st.empty()

                for i in range(len(AGENTS)):
                    with agent_placeholder.container():
                        render_agents(active_idx=i, done_up_to=i)
                    time.sleep(0.3)

                with st.spinner(""):
                    result = process_document(tmp_path, uploaded_file.name)
                    st.session_state.result     = result
                    st.session_state.qa_history = []

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

            col_title, col_score = st.columns([2, 1])
            with col_title:
                st.markdown(f"### 📄 {result['filename']}")
                lang = result.get("language", "English")
                st.markdown(f"🌐 **Language:** {lang}")
                if status == "complete":
                    st.markdown('<span class="status-complete">✅ Analysis Complete</span>',
                               unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-failed">❌ Failed</span>',
                               unsafe_allow_html=True)
                    st.error(result.get("error", ""))

            with col_score:
                if status == "complete":
                    score      = result.get("risk_score", 0)
                    css, label = get_risk_color(score)
                    st.markdown(f"""
                    <div class="metric-card">
                        <small>Risk Score</small>
                        <span class="{css}">{score}</span>
                        <small>/100</small><br>
                        <small>{label}</small>
                    </div>
                    """, unsafe_allow_html=True)

            if status == "complete":
                res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs([
                    "📋 Full Report", "📝 Summary", "🔍 Key Info", "⚠️ Risks"
                ])

                with res_tab1:
                    st.markdown(
                        f'<div class="report-section">{result["report"]}</div>',
                        unsafe_allow_html=True
                    )
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button(
                            label     = "⬇️ Download TXT",
                            data      = result["report"],
                            file_name = f"{result['filename']}_report.txt",
                            mime      = "text/plain"
                        )
                    with col_dl2:
                        pdf_bytes = export_to_pdf(result)
                        st.download_button(
                            label     = "⬇️ Download PDF",
                            data      = bytes(pdf_bytes),
                            file_name = f"{result['filename']}_report.pdf",
                            mime      = "application/pdf"
                        )

                with res_tab2:
                    st.markdown(
                        f'<div class="report-section">{result["summary"]}</div>',
                        unsafe_allow_html=True
                    )

                with res_tab3:
                    st.markdown(
                        f'<div class="report-section">{result["key_info"]}</div>',
                        unsafe_allow_html=True
                    )

                with res_tab4:
                    risks_text = result["risks"]
                    sections = {
                        "HIGH RISK":   ("risk-high",   "🔴 High Risk"),
                        "MEDIUM RISK": ("risk-medium", "🟡 Medium Risk"),
                        "LOW RISK":    ("risk-low",    "🟢 Low Risk"),
                    }
                    for key, (css, label) in sections.items():
                        if key in risks_text:
                            start     = risks_text.find(key) + len(key)
                            next_keys = [k for k in sections if k != key and k in risks_text[start:]]
                            end       = risks_text.find(next_keys[0], start) if next_keys else len(risks_text)
                            content   = risks_text[start:end].strip()
                            st.markdown(f"""
                            <div class="agent-card {css}">
                                <strong>{label}</strong><br><br>{content}
                            </div>
                            """, unsafe_allow_html=True)
                    st.markdown("---")
                    st.markdown(f'<div class="report-section">{risks_text}</div>',
                               unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="agent-card" style="text-align:center; padding:60px;">
                <h3>📤 Upload a PDF to get started</h3>
                <p style="color:#6c7086;">Supports contracts, invoices, agreements, reports</p>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 2 — Q&A
# ══════════════════════════════════════════════════════════════════════
with tab_qa:
    st.markdown("### 💬 Ask Questions About Your Document")

    if not st.session_state.result:
        st.info("📄 Analyze a document first to enable Q&A mode.")
    else:
        result   = st.session_state.result
        language = result.get("language", "English")

        st.markdown(f"**Document:** `{result['filename']}` | **Language:** {language}")
        st.divider()

        # Chat history
        for msg in st.session_state.qa_history:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="qa-message-user">👤 {msg['content']}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="qa-message-ai">🤖 {msg['content']}</div>
                """, unsafe_allow_html=True)

        # ── Dynamic suggested questions from document ─────────────────
        suggestions = result.get("suggested_questions", [])

        if suggestions:
            st.markdown("**💡 Suggested questions based on this document:**")
            # Display as 2-column grid for better readability
            col1, col2 = st.columns(2)
            for i, suggestion in enumerate(suggestions):
                with (col1 if i % 2 == 0 else col2):
                    if st.button(
                        suggestion,
                        key=f"suggestion_{i}",
                        use_container_width=True
                    ):
                        with st.spinner("🤖 Searching document..."):
                            answer = ask_document(
                                suggestion,
                                result["filename"],
                                language
                            )
                        st.session_state.qa_history.append(
                            {"role": "user", "content": suggestion}
                        )
                        st.session_state.qa_history.append(
                            {"role": "assistant", "content": answer}
                        )
                        st.rerun()

        st.divider()

        # ── Manual question input ─────────────────────────────────────
        question = st.text_input(
            "Ask your own question:",
            placeholder="e.g. What are the termination conditions?",
            key="qa_input"
        )
        col_ask, col_clear = st.columns([3, 1])
        with col_ask:
            if st.button("📨 Ask", use_container_width=True) and question:
                with st.spinner("🤖 Searching document..."):
                    answer = ask_document(question, result["filename"], language)
                st.session_state.qa_history.append(
                    {"role": "user", "content": question}
                )
                st.session_state.qa_history.append(
                    {"role": "assistant", "content": answer}
                )
                st.rerun()
        with col_clear:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.qa_history = []
                st.rerun()

# ══════════════════════════════════════════════════════════════════════
# TAB 3 — PIPELINE DIAGRAM
# ══════════════════════════════════════════════════════════════════════
with tab_pipeline:
    st.markdown("### 🕸️ Multi-Agent Pipeline Architecture")
    st.markdown("""
    <div class="pipeline-diagram">
        <div style="margin-bottom: 20px;">
            <div style="background:#313244; border-radius:8px; padding:12px; display:inline-block; min-width:200px;">
                📄 <strong>PDF Document</strong><br>
                <small style="color:#6c7086;">User Upload</small>
            </div>
        </div>
        <div style="font-size:24px; color:#cba6f7;">↓</div>
        <div style="margin: 10px 0;">
            <div style="background:#1e1e2e; border:2px solid #cba6f7; border-radius:8px; padding:12px; display:inline-block; min-width:200px;">
                ⚙️ <strong>Agent 1 — Document Processor</strong><br>
                <small style="color:#6c7086;">Extract text • Detect language • Store in ChromaDB</small>
            </div>
        </div>
        <div style="font-size:24px; color:#cba6f7;">↓</div>
        <div style="color:#fab387; margin:8px 0;"><strong>⚡ Parallel Execution</strong></div>
        <div style="display:flex; justify-content:center; gap:16px; margin:10px 0; flex-wrap:wrap;">
            <div style="background:#1e1e2e; border:2px solid #fab387; border-radius:8px; padding:12px; min-width:160px;">
                📝 <strong>Agent 2</strong><br><strong>Summarizer</strong><br>
                <small style="color:#6c7086;">Concise summary</small>
            </div>
            <div style="background:#1e1e2e; border:2px solid #fab387; border-radius:8px; padding:12px; min-width:160px;">
                🔍 <strong>Agent 3</strong><br><strong>Extractor</strong><br>
                <small style="color:#6c7086;">Key info & dates</small>
            </div>
            <div style="background:#1e1e2e; border:2px solid #fab387; border-radius:8px; padding:12px; min-width:160px;">
                ⚠️ <strong>Agent 4</strong><br><strong>Risk Flagger</strong><br>
                <small style="color:#6c7086;">Risks & red flags</small>
            </div>
        </div>
        <div style="font-size:24px; color:#cba6f7;">↓</div>
        <div style="margin: 10px 0;">
            <div style="background:#1e1e2e; border:2px solid #a6e3a1; border-radius:8px; padding:12px; display:inline-block; min-width:200px;">
                🎯 <strong>Risk Score Calculator</strong><br>
                <small style="color:#6c7086;">0–100 risk scoring</small>
            </div>
        </div>
        <div style="font-size:24px; color:#cba6f7;">↓</div>
        <div style="margin: 10px 0;">
            <div style="background:#1e1e2e; border:2px solid #a6e3a1; border-radius:8px; padding:12px; display:inline-block; min-width:200px;">
                📊 <strong>Agent 5 — Report Generator</strong><br>
                <small style="color:#6c7086;">Final structured report</small>
            </div>
        </div>
        <div style="font-size:24px; color:#cba6f7;">↓</div>
        <div style="margin: 10px 0;">
            <div style="background:#1e1e2e; border:2px solid #cba6f7; border-radius:8px; padding:12px; display:inline-block; min-width:200px;">
                💡 <strong>Questions Generator</strong><br>
                <small style="color:#6c7086;">Document-specific Q&A suggestions</small>
            </div>
        </div>
        <div style="font-size:24px; color:#cba6f7;">↓</div>
        <div style="display:flex; justify-content:center; gap:16px; margin:10px 0; flex-wrap:wrap;">
            <div style="background:#313244; border-radius:8px; padding:10px; min-width:120px;">
                💬 <strong>Q&A Mode</strong><br>
                <small style="color:#6c7086;">ChromaDB search</small>
            </div>
            <div style="background:#313244; border-radius:8px; padding:10px; min-width:120px;">
                ⬇️ <strong>PDF Export</strong><br>
                <small style="color:#6c7086;">Download report</small>
            </div>
            <div style="background:#313244; border-radius:8px; padding:10px; min-width:120px;">
                🗃️ <strong>SQLite Log</strong><br>
                <small style="color:#6c7086;">History tracking</small>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🛠️ Tech Stack")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="agent-card" style="text-align:center;">
            🦜 <strong>LangGraph</strong><br>
            <small>Multi-agent orchestration</small>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="agent-card" style="text-align:center;">
            ⚡ <strong>Groq API</strong><br>
            <small>llama-3.3-70b-versatile</small>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="agent-card" style="text-align:center;">
            🗄️ <strong>ChromaDB</strong><br>
            <small>Vector similarity search</small>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="agent-card" style="text-align:center;">
            🎨 <strong>Streamlit</strong><br>
            <small>Dark theme UI</small>
        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ══════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown("### 📋 Analysis History")
    history = get_history()

    if history:
        for entry in history:
            score      = entry.get("risk_score", 0)
            css, label = get_risk_color(score)
            with st.expander(f"📄 {entry['filename']} — {entry['timestamp']} — Score: {score}/100"):
                col_s, col_l = st.columns(2)
                with col_s:
                    status_class = "status-complete" if entry["status"] == "complete" else "status-failed"
                    st.markdown(f'<span class="{status_class}">{entry["status"].upper()}</span>',
                               unsafe_allow_html=True)
                with col_l:
                    st.markdown(f"🌐 **Language:** {entry.get('language', 'English')}")

                if entry["summary"]:
                    st.markdown("**Summary:**")
                    st.markdown(f'<div class="report-section">{entry["summary"]}</div>',
                               unsafe_allow_html=True)

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
# TAB 5 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════
with tab_stats:
    st.markdown("### 📊 Dashboard")
    stats = get_dashboard_stats()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">📄<b>{stats['total']}</b>Total Analyses</div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">✅<b>{stats['successful']}</b>Successful</div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">❌<b>{stats['failed']}</b>Failed</div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">🎯<b>{stats['avg_risk']}</b>Avg Risk Score</div>
        """, unsafe_allow_html=True)

    if stats["recent"]:
        st.markdown("### 🕓 Recently Analyzed")
        for item in stats["recent"]:
            score      = item.get("risk_score", 0)
            css, label = get_risk_color(score)
            st.markdown(f"""
            <div class="agent-card" style="display:flex; justify-content:space-between; align-items:center;">
                <span>📄 <strong>{item['filename']}</strong> — {item['timestamp']}</span>
                <span class="{css}" style="font-size:1em;">{score}/100 {label}</span>
            </div>
            """, unsafe_allow_html=True)