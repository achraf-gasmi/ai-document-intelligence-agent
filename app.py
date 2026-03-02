import streamlit as st
import sys
import os
import tempfile
import time
from fpdf import FPDF
from src.agents import improve_document

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

    /* ── Improve Tab Styles ─────────────────────────────────────── */
    .improve-score-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border: 2px solid #cba6f7;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        color: #cdd6f4;
    }
    .improve-score-card .big-score {
        font-size: 3em;
        font-weight: bold;
        color: #a6e3a1;
        display: block;
    }
    .improve-score-card.low .big-score  { color: #f38ba8; }
    .improve-score-card.mid .big-score  { color: #fab387; }
    .improve-score-card.high .big-score { color: #a6e3a1; }

    .iteration-badge {
        display: inline-block;
        background-color: #313244;
        border: 1px solid #cba6f7;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.85em;
        color: #cba6f7;
        margin: 4px;
    }
    .iteration-badge.active {
        background-color: #cba6f7;
        color: #1e1e2e;
        font-weight: bold;
    }

    .score-step {
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .score-dot {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 0.85em;
        color: #1e1e2e;
    }
    .score-arrow { color: #6c7086; font-size: 1.2em; }

    .diff-added   { color: #a6e3a1; background: #1e2e1e; padding: 2px 4px; border-radius: 3px; }
    .diff-removed { color: #f38ba8; background: #2e1e1e; padding: 2px 4px; border-radius: 3px; text-decoration: line-through; }

    .improve-agent-card {
        background-color: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #cdd6f4;
        font-size: 0.9em;
    }
    .improve-agent-active {
        background-color: #1e1e2e;
        border: 1px solid #cba6f7;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #cdd6f4;
        font-size: 0.9em;
        animation: pulse-border 1.5s infinite;
    }
    .improve-agent-done {
        background-color: #1e1e2e;
        border: 1px solid #a6e3a1;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #cdd6f4;
        font-size: 0.9em;
    }

    .doc-type-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: bold;
        margin-left: 8px;
    }
    .doc-type-resume   { background:#2a3a4a; color:#89dceb; border:1px solid #89dceb; }
    .doc-type-legal    { background:#3a2a2a; color:#f38ba8; border:1px solid #f38ba8; }
    .doc-type-report   { background:#2a3a2a; color:#a6e3a1; border:1px solid #a6e3a1; }
    .doc-type-cert     { background:#3a3a2a; color:#f9e2af; border:1px solid #f9e2af; }

    .loop-indicator {
        background-color: #1e1e2e;
        border: 1px dashed #cba6f7;
        border-radius: 10px;
        padding: 10px 16px;
        color: #cba6f7;
        text-align: center;
        font-size: 0.85em;
        margin: 6px 0;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────
if "result"          not in st.session_state: st.session_state.result          = None
if "qa_history"      not in st.session_state: st.session_state.qa_history      = []
if "improve_result"  not in st.session_state: st.session_state.improve_result  = None
if "improve_file"    not in st.session_state: st.session_state.improve_file    = None

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

IMPROVE_AGENTS = [
    ("🔎", "Doc Type Detector",  "Classifies document type"),
    ("🧐", "Critique Agent",     "Finds issues and what to fix"),
    ("✍️", "Improvement Agent",  "Rewrites and fixes sections"),
    ("✅", "Verifier Agent",     "Scores the improved version"),
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

def render_improve_agents(active_idx=None, done_up_to=None):
    for i, (icon, name, desc) in enumerate(IMPROVE_AGENTS):
        if done_up_to is not None and i < done_up_to:
            css, badge = "improve-agent-done", "✅"
        elif active_idx is not None and i == active_idx:
            css, badge = "improve-agent-active", "🔄"
        else:
            css, badge = "improve-agent-card", icon
        st.markdown(f"""
        <div class="{css}">
            <strong>{badge} {name}</strong>
            <small style="color: #6c7086; margin-left:8px;">{desc}</small>
        </div>
        """, unsafe_allow_html=True)

def get_risk_color(score):
    if score <= 20:  return "risk-score-low",    "🟢 Low Risk"
    if score <= 50:  return "risk-score-medium",  "🟡 Medium Risk"
    if score <= 80:  return "risk-score-high",    "🔴 High Risk"
    return "risk-score-high", "⛔ Critical Risk"

def get_quality_class(score):
    """For improvement score (higher = better)."""
    if score >= 85: return "high", "🟢 Excellent"
    if score >= 61: return "mid",  "🟡 Acceptable"
    return "low", "🔴 Needs Work"

def get_doc_type_badge(doc_type):
    badges = {
        "Resume/CV":       ("doc-type-resume", "📄 Resume/CV"),
        "Legal Contract":  ("doc-type-legal",  "⚖️ Legal Contract"),
        "Report":          ("doc-type-report", "📊 Report"),
        "Certificate":     ("doc-type-cert",   "📜 Certificate"),
    }
    css, label = badges.get(doc_type, ("doc-type-report", f"📄 {doc_type}"))
    return f'<span class="doc-type-badge {css}">{label}</span>'

def export_to_pdf(result: dict) -> bytes:
    """Generate a PDF report from analysis result."""
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

def export_improved_pdf(result: dict) -> bytes:
    """Generate a PDF of the improved document."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Improved Document", ln=True, align="C")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Original file: {result['filename']}", ln=True)
    pdf.cell(0, 7, f"Document type: {result['doc_type']}", ln=True)
    pdf.cell(0, 7, f"Quality score: {result['improvement_score']}/100", ln=True)
    pdf.cell(0, 7, f"Iterations: {result['total_iterations']}", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "IMPROVED CONTENT", ln=True)
    pdf.set_font("Helvetica", "", 10)
    clean = result["final_text"].encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 6, clean)
    return pdf.output()

def render_score_progression(history: list):
    """Render score progression as inline HTML badges with arrows."""
    if not history:
        return ""
    parts = []
    for i, h in enumerate(history):
        score = h["score"]
        q_class, _ = get_quality_class(score)
        color_map = {"high": "#a6e3a1", "mid": "#fab387", "low": "#f38ba8"}
        color = color_map[q_class]
        parts.append(
            f'<span class="score-dot" style="background:{color};">{score}</span>'
        )
        if i < len(history) - 1:
            parts.append('<span class="score-arrow">→</span>')
    return f'<div class="score-step">{"".join(parts)}</div>'

def render_diff_html(diff_text: str) -> str:
    """Convert diff markers to styled HTML."""
    lines = diff_text.split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("[ADDED]"):
            content = line.replace("[ADDED]", "").strip()
            html_lines.append(f'<div class="diff-added">+ {content}</div>')
        elif line.startswith("[REMOVED]"):
            content = line.replace("[REMOVED]", "").strip()
            html_lines.append(f'<div class="diff-removed">- {content}</div>')
        elif line.startswith("--- Section ---") or line.startswith("---"):
            html_lines.append('<hr style="border-color:#313244; margin:6px 0;">')
        elif line.strip():
            html_lines.append(f'<div style="color:#6c7086; font-size:0.85em;">{line}</div>')
    return "\n".join(html_lines)


# ── Tabs ──────────────────────────────────────────────────────────────
tab_analyze, tab_qa, tab_improve, tab_pipeline, tab_history, tab_stats = st.tabs([
    "🔍 Analyze",
    "💬 Q&A",
    "🔧 Improve",
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
            help="Supports contracts, invoices, reports, agreements",
            key="analyze_uploader"
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
                    # Store file path for Improve tab smart reuse
                    st.session_state.improve_file = tmp_path

                with agent_placeholder.container():
                    render_agents(done_up_to=len(AGENTS))

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
                    st.markdown(
                        '💡 <small style="color:#6c7086;">Go to the <strong>🔧 Improve</strong> tab to run the self-correcting improvement loop on this document.</small>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown('<span class="status-failed">❌ Failed</span>',
                               unsafe_allow_html=True)
                    st.error(result.get("error", ""))

            with col_score:
                if status == "complete":
                    score         = result.get("risk_score", 0)
                    reasoning     = result.get("risk_reasoning", "")
                    css, label    = get_risk_color(score)
                    st.markdown(f"""
                    <div class="metric-card">
                        <small>Risk Score</small>
                        <span class="{css}">{score}</span>
                        <small>/100</small><br>
                        <small>{label}</small><br>
                        <small style="color:#6c7086; font-size:0.75em;">{reasoning}</small>
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

        for msg in st.session_state.qa_history:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="qa-message-user">👤 {msg['content']}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="qa-message-ai">🤖 {msg['content']}</div>
                """, unsafe_allow_html=True)

        suggestions = result.get("suggested_questions", [])
        if suggestions:
            st.markdown("**💡 Suggested questions based on this document:**")
            col1, col2 = st.columns(2)
            for i, suggestion in enumerate(suggestions):
                with (col1 if i % 2 == 0 else col2):
                    if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                        with st.spinner("🤖 Searching document..."):
                            answer = ask_document(suggestion, result["filename"], language)
                        st.session_state.qa_history.append({"role": "user", "content": suggestion})
                        st.session_state.qa_history.append({"role": "assistant", "content": answer})
                        st.rerun()

        st.divider()
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
                st.session_state.qa_history.append({"role": "user", "content": question})
                st.session_state.qa_history.append({"role": "assistant", "content": answer})
                st.rerun()
        with col_clear:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.qa_history = []
                st.rerun()

# ══════════════════════════════════════════════════════════════════════
# TAB 3 — IMPROVE  (NEW)
# ══════════════════════════════════════════════════════════════════════
with tab_improve:
    st.markdown("### 🔧 Document Improvement Loop")
    st.markdown(
        '<p style="color:#6c7086;">Self-correcting AI that critiques, rewrites, and verifies your document up to 3 iterations until quality score ≥ 85.</p>',
        unsafe_allow_html=True
    )

    # ── Upload section ────────────────────────────────────────────────
    col_imp_left, col_imp_right = st.columns([1, 2])

    with col_imp_left:
        st.markdown("#### 📤 Document Source")

        # Smart reuse banner
        if st.session_state.result and st.session_state.result.get("status") == "complete":
            existing = st.session_state.result
            st.markdown(f"""
            <div class="agent-card" style="border-color:#a6e3a1;">
                ✅ <strong>Document already analyzed</strong><br>
                <small style="color:#6c7086;">{existing['filename']}</small><br>
                <small style="color:#a6e3a1;">Will skip re-analysis and go straight to improvement.</small>
            </div>
            """, unsafe_allow_html=True)
            use_existing = True
        else:
            use_existing = False
            st.info("💡 Tip: Analyze a document first in the 🔍 Analyze tab to skip re-analysis here.")

        improve_upload = st.file_uploader(
            "Upload a PDF to improve" if not use_existing else "Or upload a different PDF",
            type=["pdf"],
            key="improve_uploader",
            help="Resume, contract, report, or certificate"
        )

        # Supported types info
        st.markdown("""
        <div class="agent-card" style="margin-top:12px;">
            <strong>🎯 Supported Document Types</strong><br><br>
            <small>
            📄 <strong>Resume/CV</strong> — Fix weak bullets, add keywords<br>
            ⚖️ <strong>Legal Contract</strong> — Add missing clauses<br>
            📊 <strong>Report</strong> — Improve structure & data<br>
            📜 <strong>Certificate</strong> — Verify authenticity markers
            </small>
        </div>
        """, unsafe_allow_html=True)

        # Improvement pipeline diagram (mini)
        st.markdown("""
        <div class="agent-card" style="margin-top:12px; font-size:0.85em;">
            <strong>🔄 Improvement Loop</strong><br><br>
            <div style="text-align:center; line-height:2.2;">
                🧐 Critique Agent<br>
                <span style="color:#cba6f7;">↓</span><br>
                ✍️ Improvement Agent<br>
                <span style="color:#cba6f7;">↓</span><br>
                ✅ Verifier Agent<br>
                <span style="color:#cba6f7;">↓</span><br>
                <span style="color:#a6e3a1;">Score ≥ 85?</span><br>
                <span style="color:#6c7086; font-size:0.9em;">YES → Done &nbsp;|&nbsp; NO → Loop (max 3×)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Determine which file to use
        can_run = use_existing or (improve_upload is not None)

        if can_run:
            if st.button("🚀 Start Improvement Loop", use_container_width=True, type="primary"):
                # Save uploaded file to temp if a new file was provided
                if improve_upload:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(improve_upload.read())
                        imp_path = tmp.name
                    existing_analysis = None  # fresh file, run full pipeline
                else:
                    # Reuse the file from Analyze tab
                    imp_path = st.session_state.improve_file
                    existing_analysis = st.session_state.result

                # Animate improvement agents
                st.markdown("#### 🤖 Improvement Agents")
                imp_placeholder = st.empty()

                for i in range(len(IMPROVE_AGENTS)):
                    with imp_placeholder.container():
                        render_improve_agents(active_idx=i, done_up_to=i)
                        if i >= 1:  # show loop hint during critique+
                            st.markdown(
                                '<div class="loop-indicator">🔄 Self-correcting loop in progress...</div>',
                                unsafe_allow_html=True
                            )
                    time.sleep(0.4)

                with st.spinner("🧠 Running improvement loop (this may take 30–60 seconds)..."):
                    improve_res = improve_document(
                        file_path         = imp_path,
                        existing_analysis = existing_analysis
                    )
                    st.session_state.improve_result = improve_res

                with imp_placeholder.container():
                    render_improve_agents(done_up_to=len(IMPROVE_AGENTS))

                st.rerun()

    # ── Results Panel ─────────────────────────────────────────────────
    with col_imp_right:
        if st.session_state.improve_result:
            imp = st.session_state.improve_result

            if imp.get("improvement_status") == "failed" or imp.get("error"):
                st.error(f"❌ Improvement failed: {imp.get('error', 'Unknown error')}")
            else:
                history   = imp.get("improvement_history", [])
                fin_score = imp.get("improvement_score", 0)
                q_class, q_label = get_quality_class(fin_score)

                # ── Header row ────────────────────────────────────────
                col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                with col_h1:
                    st.markdown(
                        f"### 📄 {imp['filename']} {get_doc_type_badge(imp['doc_type'])}",
                        unsafe_allow_html=True
                    )
                    st.markdown(f"🌐 **Language:** {imp.get('language', 'English')}")
                with col_h2:
                    st.markdown(f"""
                    <div class="improve-score-card {q_class}">
                        <small>Quality Score</small>
                        <span class="big-score">{fin_score}</span>
                        <small>/100</small><br>
                        <small>{q_label}</small>
                    </div>
                    """, unsafe_allow_html=True)
                with col_h3:
                    iters = imp.get("total_iterations", 0)
                    st.markdown(f"""
                    <div class="improve-score-card mid" style="border-color:#fab387;">
                        <small>Iterations</small>
                        <span class="big-score" style="color:#fab387;">{iters}</span>
                        <small>/ 3</small><br>
                        <small>{"✅ Target reached" if fin_score >= 85 else "⚠️ Max reached"}</small>
                    </div>
                    """, unsafe_allow_html=True)

                # ── Score progression ─────────────────────────────────
                if history:
                    st.markdown("**📈 Score Progression:**")
                    progression_html = render_score_progression(history)
                    st.markdown(progression_html, unsafe_allow_html=True)

                st.markdown("---")

                # ── Main result tabs ──────────────────────────────────
                imp_tab1, imp_tab2, imp_tab3, imp_tab4 = st.tabs([
                    "📝 Side-by-Side",
                    "🔀 Track Changes",
                    "🔄 Iteration History",
                    "⬇️ Export"
                ])

                # ── TAB: Side by side ─────────────────────────────────
                with imp_tab1:
                    st.markdown("Compare the original document with the final improved version.")
                    col_orig, col_new = st.columns(2)
                    with col_orig:
                        st.markdown("**📄 Original**")
                        original_text = imp.get("original_text", "")
                        st.markdown(
                            f'<div class="report-section" style="height:500px; overflow-y:auto; white-space:pre-wrap; font-size:0.85em;">{original_text}</div>',
                            unsafe_allow_html=True
                        )
                    with col_new:
                        st.markdown("**✨ Improved**")
                        final_text = imp.get("final_text", "")
                        st.markdown(
                            f'<div class="report-section" style="height:500px; overflow-y:auto; white-space:pre-wrap; font-size:0.85em; border-color:#a6e3a1;">{final_text}</div>',
                            unsafe_allow_html=True
                        )

                # ── TAB: Track changes ────────────────────────────────
                with imp_tab2:
                    st.markdown("Lines highlighted in **green** were added. Lines in **red** were removed.")
                    diff_text = imp.get("diff_markers", "")
                    if diff_text and diff_text != "No structural changes detected.":
                        diff_html = render_diff_html(diff_text)
                        st.markdown(
                            f'<div class="report-section" style="font-family:monospace; font-size:0.82em; line-height:1.8;">{diff_html}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            '<div class="report-section">No structural diff detected. The document was improved in content but structure was preserved.</div>',
                            unsafe_allow_html=True
                        )

                # ── TAB: Iteration history ────────────────────────────
                with imp_tab3:
                    if not history:
                        st.info("No iteration history available.")
                    else:
                        for h in history:
                            score    = h["score"]
                            q_c, q_l = get_quality_class(score)
                            color_map = {"high": "#a6e3a1", "mid": "#fab387", "low": "#f38ba8"}
                            score_color = color_map[q_c]
                            with st.expander(
                                f"Round {h['iteration']}  ·  Score: {score}/100  ·  {q_l}",
                                expanded=(h["iteration"] == history[-1]["iteration"])
                            ):
                                col_v1, col_v2 = st.columns([2, 1])
                                with col_v1:
                                    st.markdown("**🧐 What was critiqued:**")
                                    st.markdown(
                                        f'<div class="report-section" style="font-size:0.85em; max-height:200px; overflow-y:auto;">{h["critique"]}</div>',
                                        unsafe_allow_html=True
                                    )
                                    if h.get("remaining"):
                                        st.markdown(f"**Remaining issues:** {h['remaining']}")
                                with col_v2:
                                    st.markdown(f"""
                                    <div class="improve-score-card {q_c}">
                                        <small>Round {h['iteration']} Score</small>
                                        <span class="big-score" style="color:{score_color};">{score}</span>
                                        <small>/100</small>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    if h.get("verdict"):
                                        st.markdown(
                                            f'<div class="agent-card" style="font-size:0.82em; margin-top:8px;">{h["verdict"]}</div>',
                                            unsafe_allow_html=True
                                        )

                                if h.get("diff_markers"):
                                    with st.expander("🔀 Show changes this round"):
                                        diff_html = render_diff_html(h["diff_markers"])
                                        st.markdown(
                                            f'<div class="report-section" style="font-family:monospace; font-size:0.8em;">{diff_html}</div>',
                                            unsafe_allow_html=True
                                        )

                # ── TAB: Export ───────────────────────────────────────
                with imp_tab4:
                    st.markdown("#### ⬇️ Download Improved Document")
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        st.download_button(
                            label     = "⬇️ Download Improved TXT",
                            data      = imp.get("final_text", ""),
                            file_name = f"{imp['filename']}_improved.txt",
                            mime      = "text/plain",
                            use_container_width=True
                        )
                    with col_e2:
                        imp_pdf = export_improved_pdf(imp)
                        st.download_button(
                            label     = "⬇️ Download Improved PDF",
                            data      = bytes(imp_pdf),
                            file_name = f"{imp['filename']}_improved.pdf",
                            mime      = "application/pdf",
                            use_container_width=True
                        )

                    st.markdown("---")
                    st.markdown("#### 📋 Full Improved Text")
                    st.markdown(
                        f'<div class="report-section" style="white-space:pre-wrap;">{imp.get("final_text", "")}</div>',
                        unsafe_allow_html=True
                    )

        else:
            # Empty state
            st.markdown("""
            <div class="agent-card" style="text-align:center; padding:60px;">
                <h3>🔧 Run the Improvement Loop</h3>
                <p style="color:#6c7086; margin-bottom:16px;">
                    Upload a document on the left (or use one already analyzed)<br>
                    to start the self-correcting improvement cycle.
                </p>
                <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap; margin-top:16px;">
                    <span style="background:#2a3a4a; color:#89dceb; border:1px solid #89dceb; border-radius:20px; padding:4px 14px; font-size:0.85em;">📄 Resume/CV</span>
                    <span style="background:#3a2a2a; color:#f38ba8; border:1px solid #f38ba8; border-radius:20px; padding:4px 14px; font-size:0.85em;">⚖️ Legal Contract</span>
                    <span style="background:#2a3a2a; color:#a6e3a1; border:1px solid #a6e3a1; border-radius:20px; padding:4px 14px; font-size:0.85em;">📊 Report</span>
                    <span style="background:#3a3a2a; color:#f9e2af; border:1px solid #f9e2af; border-radius:20px; padding:4px 14px; font-size:0.85em;">📜 Certificate</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 4 — PIPELINE DIAGRAM
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
        <div style="font-size:24px; color:#cba6f7; margin-top:16px;">↓</div>
        <div style="color:#cba6f7; margin:8px 0;"><strong>🔧 Improvement Loop (New)</strong></div>
        <div style="display:flex; justify-content:center; gap:16px; margin:10px 0; flex-wrap:wrap;">
            <div style="background:#1e1e2e; border:2px solid #cba6f7; border-radius:8px; padding:12px; min-width:160px;">
                🧐 <strong>Critique Agent</strong><br>
                <small style="color:#6c7086;">Doc-type-aware issues</small>
            </div>
            <div style="background:#1e1e2e; border:2px solid #cba6f7; border-radius:8px; padding:12px; min-width:160px;">
                ✍️ <strong>Improvement Agent</strong><br>
                <small style="color:#6c7086;">Rewrites & fixes</small>
            </div>
            <div style="background:#1e1e2e; border:2px solid #cba6f7; border-radius:8px; padding:12px; min-width:160px;">
                ✅ <strong>Verifier Agent</strong><br>
                <small style="color:#6c7086;">Scores → loops if &lt;85</small>
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
# TAB 5 — HISTORY
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
# TAB 6 — DASHBOARD
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