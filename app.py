import streamlit as st
import sys
import os
import tempfile
import time
from fpdf import FPDF
from src.agents import improve_document, resume_improvement

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.backend import process_document, get_history, get_dashboard_stats, ask_document

st.set_page_config(page_title="AI Document Intelligence", page_icon="📄", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0f1117; }
    .main-header { text-align: center; padding: 20px 0; color: #ffffff; }
    .agent-card {
        background-color: #1e1e2e; border: 1px solid #313244;
        border-radius: 12px; padding: 16px; margin: 8px 0; color: #cdd6f4;
    }
    .agent-active {
        background-color: #1e1e2e; border: 1px solid #cba6f7;
        border-radius: 12px; padding: 16px; margin: 8px 0; color: #cdd6f4;
    }
    .agent-done {
        background-color: #1e1e2e; border: 1px solid #a6e3a1;
        border-radius: 12px; padding: 16px; margin: 8px 0; color: #cdd6f4;
    }
    .risk-high   { border-left: 4px solid #f38ba8; }
    .risk-medium { border-left: 4px solid #fab387; }
    .risk-low    { border-left: 4px solid #a6e3a1; }
    .metric-card {
        background-color: #1e1e2e; border: 1px solid #313244;
        border-radius: 12px; padding: 16px; text-align: center; color: #cdd6f4;
    }
    .metric-card b { display: block; font-size: 2em; color: #cba6f7; }
    .risk-score-high   { color: #f38ba8; font-size: 2.5em; font-weight: bold; }
    .risk-score-medium { color: #fab387; font-size: 2.5em; font-weight: bold; }
    .risk-score-low    { color: #a6e3a1; font-size: 2.5em; font-weight: bold; }
    .status-complete { color: #a6e3a1; font-weight: bold; }
    .status-failed   { color: #f38ba8; font-weight: bold; }
    .report-section {
        background-color: #1e1e2e; border: 1px solid #313244;
        border-radius: 12px; padding: 24px; color: #cdd6f4; line-height: 1.7;
    }
    .qa-message-user {
        background-color: #313244; border-radius: 12px;
        padding: 12px 16px; margin: 8px 0; color: #cdd6f4; text-align: right;
    }
    .qa-message-ai {
        background-color: #1e1e2e; border: 1px solid #cba6f7;
        border-radius: 12px; padding: 12px 16px; margin: 8px 0; color: #cdd6f4;
    }
    .pipeline-diagram {
        background-color: #1e1e2e; border: 1px solid #313244;
        border-radius: 12px; padding: 24px; text-align: center; color: #cdd6f4;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #1e1e2e; border-radius: 12px; }
    .stTabs [data-baseweb="tab"] { color: #cdd6f4; }

    /* Improve tab */
    .improve-score-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border: 2px solid #cba6f7; border-radius: 16px; padding: 20px; text-align: center; color: #cdd6f4;
    }
    .improve-score-card .big-score { font-size: 3em; font-weight: bold; display: block; }
    .improve-score-card.low .big-score  { color: #f38ba8; }
    .improve-score-card.mid .big-score  { color: #fab387; }
    .improve-score-card.high .big-score { color: #a6e3a1; }
    .score-step { display: inline-flex; align-items: center; gap: 6px; }
    .score-dot {
        width: 40px; height: 40px; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        font-weight: bold; font-size: 0.85em; color: #1e1e2e;
    }
    .score-arrow { color: #6c7086; font-size: 1.2em; }
    .diff-added   { color: #a6e3a1; background: #1e2e1e; padding: 2px 4px; border-radius: 3px; }
    .diff-removed { color: #f38ba8; background: #2e1e1e; padding: 2px 4px; border-radius: 3px; text-decoration: line-through; }
    .improve-agent-card {
        background-color: #1e1e2e; border: 1px solid #313244;
        border-radius: 10px; padding: 12px 16px; margin: 6px 0; color: #cdd6f4; font-size: 0.9em;
    }
    .improve-agent-active {
        background-color: #1e1e2e; border: 1px solid #cba6f7;
        border-radius: 10px; padding: 12px 16px; margin: 6px 0; color: #cdd6f4; font-size: 0.9em;
    }
    .improve-agent-done {
        background-color: #1e1e2e; border: 1px solid #a6e3a1;
        border-radius: 10px; padding: 12px 16px; margin: 6px 0; color: #cdd6f4; font-size: 0.9em;
    }
    .doc-type-badge {
        display: inline-block; padding: 4px 14px; border-radius: 20px;
        font-size: 0.85em; font-weight: bold; margin-left: 8px;
    }
    .doc-type-resume  { background:#2a3a4a; color:#89dceb; border:1px solid #89dceb; }
    .doc-type-legal   { background:#3a2a2a; color:#f38ba8; border:1px solid #f38ba8; }
    .doc-type-report  { background:#2a3a2a; color:#a6e3a1; border:1px solid #a6e3a1; }
    .doc-type-cert    { background:#3a3a2a; color:#f9e2af; border:1px solid #f9e2af; }
    .loop-indicator {
        background-color: #1e1e2e; border: 1px dashed #cba6f7; border-radius: 10px;
        padding: 10px 16px; color: #cba6f7; text-align: center; font-size: 0.85em; margin: 6px 0;
    }
    .checkpoint-badge {
        background: #2a2a3e; border: 1px solid #cba6f7; border-radius: 8px;
        padding: 6px 12px; font-size: 0.8em; color: #cba6f7; display: inline-block; margin-top: 6px;
    }
    .cycle-diagram {
        background-color: #1e1e2e; border: 1px solid #313244;
        border-radius: 12px; padding: 32px 24px; color: #cdd6f4;
    }
    .cycle-arrow-down { font-size: 20px; color: #cba6f7; line-height: 1.4; }
    .cycle-loop-box {
        border: 2px dashed #cba6f7; border-radius: 16px; padding: 20px 24px;
        margin: 12px auto; max-width: 520px; position: relative;
    }
    .cycle-loop-label {
        position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
        background: #0f1117; padding: 0 10px; color: #cba6f7;
        font-size: 0.8em; font-weight: bold; white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────
for key, default in [
    ("result",          None),
    ("qa_history",      []),
    ("improve_result",  None),
    ("last_raw_text",   None),
    ("improve_file",    None),
    ("improve_thread_id", None),   # CHECKPOINTING: stored per run for resume
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Header ────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>📄 AI Document Intelligence Agent</h1>
    <p style="color: #6c7086;">Multi-agent document analysis powered by LangGraph + Groq</p>
</div>
""", unsafe_allow_html=True)
st.divider()

# ── Helpers ───────────────────────────────────────────────────────────
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
    ("✅", "Verifier Agent",     "Adversarial quality scoring (t=0)"),
]

def render_agents(active_idx=None, done_up_to=None):
    for i, (icon, name, desc) in enumerate(AGENTS):
        if done_up_to is not None and i < done_up_to: css, badge = "agent-done", "✅"
        elif active_idx is not None and i == active_idx: css, badge = "agent-active", "🔄"
        else: css, badge = "agent-card", icon
        st.markdown(f'<div class="{css}"><strong>{badge} {name}</strong><br><small style="color:#6c7086;">{desc}</small></div>', unsafe_allow_html=True)

def render_improve_agents(active_idx=None, done_up_to=None):
    for i, (icon, name, desc) in enumerate(IMPROVE_AGENTS):
        if done_up_to is not None and i < done_up_to: css, badge = "improve-agent-done", "✅"
        elif active_idx is not None and i == active_idx: css, badge = "improve-agent-active", "🔄"
        else: css, badge = "improve-agent-card", icon
        st.markdown(f'<div class="{css}"><strong>{badge} {name}</strong><small style="color:#6c7086;margin-left:8px;">{desc}</small></div>', unsafe_allow_html=True)

def get_risk_color(score):
    if score <= 20: return "risk-score-low",    "🟢 Low Risk"
    if score <= 50: return "risk-score-medium", "🟡 Medium Risk"
    if score <= 80: return "risk-score-high",   "🔴 High Risk"
    return "risk-score-high", "⛔ Critical Risk"

def get_quality_class(score):
    if score >= 85: return "high", "🟢 Excellent"
    if score >= 61: return "mid",  "🟡 Acceptable"
    return "low", "🔴 Needs Work"

def get_doc_type_badge(doc_type):
    badges = {
        "Resume/CV":      ("doc-type-resume", "📄 Resume/CV"),
        "Legal Contract": ("doc-type-legal",  "⚖️ Legal Contract"),
        "Report":         ("doc-type-report", "📊 Report"),
        "Certificate":    ("doc-type-cert",   "📜 Certificate"),
    }
    css, label = badges.get(doc_type, ("doc-type-report", f"📄 {doc_type}"))
    return f'<span class="doc-type-badge {css}">{label}</span>'

def export_to_pdf(result):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Document Analysis Report", ln=True, align="C"); pdf.ln(5)
    pdf.set_font("Helvetica", "", 11)
    for label, val in [("Document", result["filename"]), ("Language", result["language"]), ("Risk Score", f"{result['risk_score']}/100")]:
        pdf.cell(0, 8, f"{label}: {val}", ln=True)
    pdf.ln(5)
    for title, content in [("SUMMARY", result["summary"]), ("KEY INFORMATION", result["key_info"]), ("RISK ANALYSIS", result["risks"]), ("FULL REPORT", result["report"])]:
        pdf.set_font("Helvetica", "B", 13); pdf.cell(0, 10, title, ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, content.encode("latin-1", "replace").decode("latin-1")); pdf.ln(4)
    return pdf.output()

def export_improved_pdf(result):
    pdf = FPDF(); pdf.add_page()
    pdf.set_font("Helvetica", "B", 16); pdf.cell(0, 10, "Improved Document", ln=True, align="C"); pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)
    for label, val in [("Original file", result["filename"]), ("Document type", result["doc_type"]), ("Quality score", f"{result['improvement_score']}/100"), ("Iterations", str(result["total_iterations"]))]:
        pdf.cell(0, 7, f"{label}: {val}", ln=True)
    pdf.ln(5); pdf.set_font("Helvetica", "B", 13); pdf.cell(0, 10, "IMPROVED CONTENT", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, result["final_text"].encode("latin-1", "replace").decode("latin-1"))
    return pdf.output()

def render_score_progression(history):
    parts = []
    for i, h in enumerate(history):
        q_class, _ = get_quality_class(h["score"])
        color = {"high": "#a6e3a1", "mid": "#fab387", "low": "#f38ba8"}[q_class]
        parts.append(f'<span class="score-dot" style="background:{color};">{h["score"]}</span>')
        if i < len(history) - 1: parts.append('<span class="score-arrow">→</span>')
    return f'<div class="score-step">{"".join(parts)}</div>'

def render_diff_html(diff_text):
    out = []
    for line in diff_text.split("\n"):
        if line.startswith("[ADDED]"):    out.append(f'<div class="diff-added">+ {line.replace("[ADDED]","").strip()}</div>')
        elif line.startswith("[REMOVED]"): out.append(f'<div class="diff-removed">- {line.replace("[REMOVED]","").strip()}</div>')
        elif "--- Section ---" in line:   out.append('<hr style="border-color:#313244;margin:6px 0;">')
        elif line.strip():                out.append(f'<div style="color:#6c7086;font-size:0.85em;">{line}</div>')
    return "\n".join(out)


# ── Tabs ──────────────────────────────────────────────────────────────
tab_analyze, tab_qa, tab_improve, tab_pipeline, tab_history, tab_stats = st.tabs([
    "🔍 Analyze", "💬 Q&A", "🔧 Improve", "🕸️ Pipeline", "📋 History", "📊 Dashboard"
])

# ══════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYZE
# ══════════════════════════════════════════════════════════════════════
with tab_analyze:
    col_upload, col_result = st.columns([1, 2])
    with col_upload:
        st.markdown("### 📤 Upload Document")
        uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"],
            help="Supports contracts, invoices, reports, agreements", key="analyze_uploader")

        if uploaded_file:
            st.success(f"✅ {uploaded_file.name} uploaded")
            st.markdown(f"**Size:** {uploaded_file.size / 1024:.1f} KB")

            if st.button("🚀 Analyze Document", use_container_width=True):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name

                agent_placeholder = st.empty()
                for i in range(len(AGENTS)):
                    with agent_placeholder.container(): render_agents(active_idx=i, done_up_to=i)
                    time.sleep(0.3)

                with st.spinner(""):
                    result = process_document(tmp_path, uploaded_file.name)
                    st.session_state.result       = result
                    st.session_state.qa_history   = []
                    st.session_state.last_raw_text = result.get("raw_text", "")
                    st.session_state.improve_file  = tmp_path  # not unlinked — kept for improve tab

                with agent_placeholder.container(): render_agents(done_up_to=len(AGENTS))
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
                st.markdown(f"🌐 **Language:** {result.get('language','English')}")
                if status == "complete":
                    st.markdown('<span class="status-complete">✅ Analysis Complete</span>', unsafe_allow_html=True)
                    st.markdown('💡 <small style="color:#6c7086;">Go to <strong>🔧 Improve</strong> to run the self-correcting loop.</small>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-failed">❌ Failed</span>', unsafe_allow_html=True)
                    st.error(result.get("error", ""))
            with col_score:
                if status == "complete":
                    score = result.get("risk_score", 0)
                    css, label = get_risk_color(score)
                    st.markdown(f"""<div class="metric-card"><small>Risk Score</small>
                        <span class="{css}">{score}</span><small>/100</small><br>
                        <small>{label}</small><br>
                        <small style="color:#6c7086;font-size:0.75em;">{result.get('risk_reasoning','')}</small>
                    </div>""", unsafe_allow_html=True)

            if status == "complete":
                r1, r2, r3, r4 = st.tabs(["📋 Full Report", "📝 Summary", "🔍 Key Info", "⚠️ Risks"])
                with r1:
                    st.markdown(f'<div class="report-section">{result["report"]}</div>', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    with c1: st.download_button("⬇️ TXT", result["report"], f"{result['filename']}_report.txt", "text/plain")
                    with c2: st.download_button("⬇️ PDF", bytes(export_to_pdf(result)), f"{result['filename']}_report.pdf", "application/pdf")
                with r2: st.markdown(f'<div class="report-section">{result["summary"]}</div>', unsafe_allow_html=True)
                with r3: st.markdown(f'<div class="report-section">{result["key_info"]}</div>', unsafe_allow_html=True)
                with r4:
                    risks_text = result["risks"]
                    for key, (css, label) in {"HIGH RISK": ("risk-high","🔴 High Risk"), "MEDIUM RISK": ("risk-medium","🟡 Medium Risk"), "LOW RISK": ("risk-low","🟢 Low Risk")}.items():
                        if key in risks_text:
                            start = risks_text.find(key) + len(key)
                            next_keys = [k for k in ["HIGH RISK","MEDIUM RISK","LOW RISK"] if k != key and k in risks_text[start:]]
                            end = risks_text.find(next_keys[0], start) if next_keys else len(risks_text)
                            st.markdown(f'<div class="agent-card {css}"><strong>{label}</strong><br><br>{risks_text[start:end].strip()}</div>', unsafe_allow_html=True)
                    st.markdown("---")
                    st.markdown(f'<div class="report-section">{risks_text}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="agent-card" style="text-align:center;padding:60px;"><h3>📤 Upload a PDF to get started</h3><p style="color:#6c7086;">Supports contracts, invoices, agreements, reports</p></div>', unsafe_allow_html=True)

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
            css = "qa-message-user" if msg["role"] == "user" else "qa-message-ai"
            icon = "👤" if msg["role"] == "user" else "🤖"
            st.markdown(f'<div class="{css}">{icon} {msg["content"]}</div>', unsafe_allow_html=True)

        suggestions = result.get("suggested_questions", [])
        if suggestions:
            st.markdown("**💡 Suggested questions:**")
            col1, col2 = st.columns(2)
            for i, s in enumerate(suggestions):
                with (col1 if i % 2 == 0 else col2):
                    if st.button(s, key=f"sug_{i}", use_container_width=True):
                        with st.spinner("🤖 Searching..."): answer = ask_document(s, result["filename"], language)
                        st.session_state.qa_history += [{"role":"user","content":s},{"role":"assistant","content":answer}]
                        st.rerun()

        st.divider()
        question = st.text_input("Ask your own question:", placeholder="e.g. What are the termination conditions?", key="qa_input")
        c1, c2 = st.columns([3, 1])
        with c1:
            if st.button("📨 Ask", use_container_width=True) and question:
                with st.spinner("🤖 Searching..."): answer = ask_document(question, result["filename"], language)
                st.session_state.qa_history += [{"role":"user","content":question},{"role":"assistant","content":answer}]
                st.rerun()
        with c2:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.qa_history = []; st.rerun()

# ══════════════════════════════════════════════════════════════════════
# TAB 3 — IMPROVE
# ══════════════════════════════════════════════════════════════════════
with tab_improve:
    st.markdown("### 🔧 Document Improvement Loop")
    st.markdown('<p style="color:#6c7086;">Self-correcting AI — critiques, rewrites, and adversarially verifies up to 3 iterations until quality ≥ 85.</p>', unsafe_allow_html=True)

    col_imp_left, col_imp_right = st.columns([1, 2])

    with col_imp_left:
        st.markdown("#### 📤 Document Source")

        use_existing = (
            st.session_state.result is not None
            and st.session_state.result.get("status") == "complete"
            and bool(st.session_state.last_raw_text)
        )

        if use_existing:
            st.markdown(f"""<div class="agent-card" style="border-color:#a6e3a1;">
                ✅ <strong>Document already analyzed</strong><br>
                <small style="color:#6c7086;">{st.session_state.result['filename']}</small><br>
                <small style="color:#a6e3a1;">Will skip re-analysis.</small>
            </div>""", unsafe_allow_html=True)
        else:
            st.info("💡 Analyze a document in 🔍 Analyze to skip re-analysis here.")

        improve_upload = st.file_uploader(
            "Or upload a different PDF" if use_existing else "Upload a PDF to improve",
            type=["pdf"], key="improve_uploader"
        )

        # CHECKPOINTING: show resume option if a previous run exists
        if st.session_state.improve_thread_id:
            tid = st.session_state.improve_thread_id
            st.markdown(f"""<div class="checkpoint-badge">
                🔖 Checkpoint saved<br>
                <small style="color:#6c7086;">thread: {tid[:8]}...</small>
            </div>""", unsafe_allow_html=True)
            if st.button("⏭️ Resume Last Run", use_container_width=True):
                with st.spinner("⏭️ Resuming from checkpoint..."):
                    try:
                        improve_res = resume_improvement(tid)
                        st.session_state.improve_result = improve_res
                        st.rerun()
                    except Exception as e:
                        st.error(f"Resume failed: {e}")

        st.markdown("""<div class="agent-card" style="margin-top:12px;font-size:0.85em;">
            <strong>🔄 Improvement Loop</strong><br><br>
            <div style="text-align:center;line-height:2.2;">
                🧐 Critique Agent<br><span style="color:#cba6f7;">↓</span><br>
                ✍️ Improvement Agent<br><span style="color:#cba6f7;">↓</span><br>
                ✅ Verifier <em style="color:#6c7086;">(adversarial, t=0)</em><br>
                <span style="color:#cba6f7;">↓</span><br>
                <span style="color:#a6e3a1;">Score ≥ 85?</span><br>
                <span style="color:#6c7086;font-size:0.9em;">YES → Done &nbsp;|&nbsp; NO → Loop (max 3×)</span>
            </div>
        </div>""", unsafe_allow_html=True)

        can_run = use_existing or (improve_upload is not None)
        if can_run:
            if st.button("🚀 Start Improvement Loop", use_container_width=True, type="primary"):
                if improve_upload:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(improve_upload.read())
                        imp_path = tmp.name
                    existing_analysis = None
                else:
                    imp_path          = st.session_state.improve_file or ""
                    existing_analysis = st.session_state.result
                    if existing_analysis and not existing_analysis.get("raw_text"):
                        existing_analysis = {**existing_analysis, "raw_text": st.session_state.last_raw_text or ""}

                imp_placeholder = st.empty()
                for i in range(len(IMPROVE_AGENTS)):
                    with imp_placeholder.container():
                        render_improve_agents(active_idx=i, done_up_to=i)
                        if i >= 1: st.markdown('<div class="loop-indicator">🔄 Self-correcting loop in progress...</div>', unsafe_allow_html=True)
                    time.sleep(0.4)

                with st.spinner("🧠 Running improvement loop (30–60s)..."):
                    improve_res = improve_document(
                        file_path=imp_path,
                        existing_analysis=existing_analysis
                    )
                    st.session_state.improve_result   = improve_res
                    # CHECKPOINTING: store thread_id for potential resume
                    st.session_state.improve_thread_id = improve_res.get("thread_id")

                with imp_placeholder.container(): render_improve_agents(done_up_to=len(IMPROVE_AGENTS))
                st.rerun()

    with col_imp_right:
        if st.session_state.improve_result:
            imp = st.session_state.improve_result

            if imp.get("improvement_status") == "failed" or imp.get("error"):
                st.error(f"❌ Improvement failed: {imp.get('error','Unknown error')}")
                if st.session_state.improve_thread_id:
                    st.info("💡 A checkpoint was saved. Use **Resume Last Run** on the left to continue from where it stopped.")
            else:
                history   = imp.get("improvement_history", [])
                fin_score = imp.get("improvement_score", 0)
                q_class, q_label = get_quality_class(fin_score)

                col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                with col_h1:
                    st.markdown(f"### 📄 {imp['filename']} {get_doc_type_badge(imp['doc_type'])}", unsafe_allow_html=True)
                    st.markdown(f"🌐 **Language:** {imp.get('language','English')}")
                    if imp.get("thread_id"):
                        st.markdown(f'<div class="checkpoint-badge">🔖 thread: {imp["thread_id"][:8]}...</div>', unsafe_allow_html=True)
                with col_h2:
                    st.markdown(f"""<div class="improve-score-card {q_class}">
                        <small>Quality Score</small>
                        <span class="big-score">{fin_score}</span>
                        <small>/100</small><br><small>{q_label}</small>
                    </div>""", unsafe_allow_html=True)
                with col_h3:
                    iters = imp.get("total_iterations", 0)
                    st.markdown(f"""<div class="improve-score-card mid" style="border-color:#fab387;">
                        <small>Iterations</small>
                        <span class="big-score" style="color:#fab387;">{iters}</span>
                        <small>/ 3</small><br>
                        <small>{"✅ Target reached" if fin_score >= 85 else "⚠️ Max reached"}</small>
                    </div>""", unsafe_allow_html=True)

                if history:
                    st.markdown("**📈 Score Progression:**")
                    st.markdown(render_score_progression(history), unsafe_allow_html=True)

                st.markdown("---")
                it1, it2, it3, it4 = st.tabs(["📝 Side-by-Side", "🔀 Track Changes", "🔄 Iteration History", "⬇️ Export"])

                with it1:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**📄 Original**")
                        st.markdown(f'<div class="report-section" style="height:500px;overflow-y:auto;white-space:pre-wrap;font-size:0.85em;">{imp.get("original_text","")}</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown("**✨ Improved**")
                        st.markdown(f'<div class="report-section" style="height:500px;overflow-y:auto;white-space:pre-wrap;font-size:0.85em;border-color:#a6e3a1;">{imp.get("final_text","")}</div>', unsafe_allow_html=True)

                with it2:
                    st.markdown("**Green** = added · **Red** = removed")
                    diff_text = imp.get("diff_markers", "")
                    if diff_text and diff_text != "No structural changes detected.":
                        st.markdown(f'<div class="report-section" style="font-family:monospace;font-size:0.82em;line-height:1.8;">{render_diff_html(diff_text)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="report-section">Structure preserved — content-level improvements only.</div>', unsafe_allow_html=True)

                with it3:
                    for h in history:
                        score = h["score"]; q_c, q_l = get_quality_class(score)
                        color = {"high":"#a6e3a1","mid":"#fab387","low":"#f38ba8"}[q_c]
                        with st.expander(f"Round {h['iteration']}  ·  {score}/100  ·  {q_l}", expanded=(h["iteration"]==history[-1]["iteration"])):
                            cv1, cv2 = st.columns([2, 1])
                            with cv1:
                                st.markdown("**🧐 Critique:**")
                                st.markdown(f'<div class="report-section" style="font-size:0.85em;max-height:200px;overflow-y:auto;">{h["critique"]}</div>', unsafe_allow_html=True)
                                if h.get("remaining"): st.markdown(f"**Remaining:** {h['remaining']}")
                            with cv2:
                                st.markdown(f"""<div class="improve-score-card {q_c}">
                                    <small>Round {h['iteration']}</small>
                                    <span class="big-score" style="color:{color};">{score}</span>
                                    <small>/100</small>
                                </div>""", unsafe_allow_html=True)
                                if h.get("verdict"): st.markdown(f'<div class="agent-card" style="font-size:0.82em;margin-top:8px;">{h["verdict"]}</div>', unsafe_allow_html=True)
                            if h.get("diff_markers"):
                                with st.expander("🔀 Changes this round"):
                                    st.markdown(f'<div class="report-section" style="font-family:monospace;font-size:0.8em;">{render_diff_html(h["diff_markers"])}</div>', unsafe_allow_html=True)

                with it4:
                    st.markdown("#### ⬇️ Download")
                    ce1, ce2 = st.columns(2)
                    with ce1: st.download_button("⬇️ TXT", imp.get("final_text",""), f"{imp['filename']}_improved.txt", "text/plain", use_container_width=True)
                    with ce2: st.download_button("⬇️ PDF", bytes(export_improved_pdf(imp)), f"{imp['filename']}_improved.pdf", "application/pdf", use_container_width=True)
                    st.markdown("---")
                    st.markdown(f'<div class="report-section" style="white-space:pre-wrap;">{imp.get("final_text","")}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""<div class="agent-card" style="text-align:center;padding:60px;">
                <h3>🔧 Run the Improvement Loop</h3>
                <p style="color:#6c7086;">Upload a document or use one already analyzed.</p>
                <div style="display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin-top:16px;">
                    <span style="background:#2a3a4a;color:#89dceb;border:1px solid #89dceb;border-radius:20px;padding:4px 14px;font-size:0.85em;">📄 Resume/CV</span>
                    <span style="background:#3a2a2a;color:#f38ba8;border:1px solid #f38ba8;border-radius:20px;padding:4px 14px;font-size:0.85em;">⚖️ Legal Contract</span>
                    <span style="background:#2a3a2a;color:#a6e3a1;border:1px solid #a6e3a1;border-radius:20px;padding:4px 14px;font-size:0.85em;">📊 Report</span>
                    <span style="background:#3a3a2a;color:#f9e2af;border:1px solid #f9e2af;border-radius:20px;padding:4px 14px;font-size:0.85em;">📜 Certificate</span>
                </div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 4 — PIPELINE DIAGRAM
# ══════════════════════════════════════════════════════════════════════
with tab_pipeline:
    st.markdown("### 🕸️ Multi-Agent Pipeline Architecture")
    st.markdown("""<div class="pipeline-diagram">
      <div style="margin-bottom:8px;"><div style="background:#313244;border-radius:8px;padding:12px;display:inline-block;min-width:200px;">
        📄 <strong>PDF Document</strong><br><small style="color:#6c7086;">User Upload</small>
      </div></div>
      <div class="cycle-arrow-down">↓</div>
      <div style="margin:8px 0;"><div style="background:#1e1e2e;border:2px solid #cba6f7;border-radius:8px;padding:12px;display:inline-block;min-width:220px;">
        ⚙️ <strong>Agent 1 — Document Processor</strong><br><small style="color:#6c7086;">Extract · Language detect · ChromaDB store</small>
      </div></div>
      <div class="cycle-arrow-down">↓</div>
      <div style="color:#fab387;margin:6px 0;"><strong>⚡ Async Parallel (asyncio.gather)</strong></div>
      <div style="display:flex;justify-content:center;gap:14px;margin:8px 0;flex-wrap:wrap;">
        <div style="background:#1e1e2e;border:2px solid #fab387;border-radius:8px;padding:12px;min-width:150px;">📝 <strong>Agent 2</strong><br>Summarizer</div>
        <div style="background:#1e1e2e;border:2px solid #fab387;border-radius:8px;padding:12px;min-width:150px;">🔍 <strong>Agent 3</strong><br>Extractor</div>
        <div style="background:#1e1e2e;border:2px solid #fab387;border-radius:8px;padding:12px;min-width:150px;">⚠️ <strong>Agent 4</strong><br>Risk Flagger</div>
      </div>
      <div class="cycle-arrow-down">↓</div>
      <div style="margin:8px 0;"><div style="background:#1e1e2e;border:2px solid #a6e3a1;border-radius:8px;padding:12px;display:inline-block;min-width:200px;">
        🎯 <strong>Risk Score Calculator</strong><br><small style="color:#6c7086;">Context-aware 0–100</small>
      </div></div>
      <div class="cycle-arrow-down">↓</div>
      <div style="margin:8px 0;"><div style="background:#1e1e2e;border:2px solid #a6e3a1;border-radius:8px;padding:12px;display:inline-block;min-width:200px;">
        📊 <strong>Agent 5 — Report Generator</strong>
      </div></div>
      <div class="cycle-arrow-down">↓</div>
      <div style="margin:8px 0;"><div style="background:#1e1e2e;border:2px solid #cba6f7;border-radius:8px;padding:12px;display:inline-block;min-width:200px;">
        💡 <strong>Agent 6 — Questions Generator</strong>
      </div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🔧 Improvement Loop — Agentic Cycle")
    st.markdown("""<div class="cycle-diagram" style="text-align:center;">
      <div style="margin-bottom:6px;"><div style="background:#313244;border-radius:8px;padding:10px;display:inline-block;min-width:200px;">
        📄 <strong>Document</strong> <span style="color:#6c7086;font-size:0.8em;">(from session or fresh upload)</span>
      </div></div>
      <div class="cycle-arrow-down">↓</div>
      <div style="margin-bottom:6px;"><div style="background:#1e1e2e;border:2px solid #89dceb;border-radius:8px;padding:10px;display:inline-block;min-width:200px;">
        🔎 <strong>Doc Type Detector</strong><br><small style="color:#6c7086;">Resume · Contract · Report · Certificate</small>
      </div></div>
      <div class="cycle-arrow-down">↓</div>
      <div class="cycle-loop-box">
        <span class="cycle-loop-label">🔄 AGENTIC SELF-CORRECTION LOOP (max 3 iterations)</span>
        <div style="margin:10px 0 6px 0;"><div style="background:#1e1e2e;border:2px solid #cba6f7;border-radius:8px;padding:10px;display:inline-block;min-width:200px;">
          🧐 <strong>Critique Agent</strong><br><small style="color:#6c7086;">Section · Problem · Severity · Fix instruction</small>
        </div></div>
        <div class="cycle-arrow-down">↓</div>
        <div style="margin:6px 0;"><div style="background:#1e1e2e;border:2px solid #cba6f7;border-radius:8px;padding:10px;display:inline-block;min-width:200px;">
          ✍️ <strong>Improvement Agent</strong><br><small style="color:#6c7086;">Rewrites · Fixes Critical & Major issues</small>
        </div></div>
        <div class="cycle-arrow-down">↓</div>
        <div style="margin:6px 0;"><div style="background:#1e1e2e;border:2px solid #f9e2af;border-radius:8px;padding:10px;display:inline-block;min-width:200px;">
          ✅ <strong>Verifier Agent</strong><br><small style="color:#f9e2af;">Adversarial · temperature=0 · Independent LLM</small>
        </div></div>
        <div class="cycle-arrow-down">↓</div>
        <div style="margin:8px 0;"><div style="background:#2a2a1e;border:2px solid #f9e2af;border-radius:8px;padding:10px 20px;display:inline-block;">
          ◆ <strong style="color:#f9e2af;">Score ≥ 85?</strong>
        </div></div>
        <div style="display:flex;justify-content:center;gap:60px;margin:6px 0;">
          <div style="text-align:center;"><div style="color:#f38ba8;font-weight:bold;">❌ NO</div><div style="color:#6c7086;font-size:0.75em;">iteration &lt; 3</div></div>
          <div style="text-align:center;"><div style="color:#a6e3a1;font-weight:bold;">✅ YES</div><div style="color:#6c7086;font-size:0.75em;">or iteration = 3</div></div>
        </div>
        <div style="display:flex;justify-content:center;gap:60px;margin:4px 0;">
          <div style="text-align:center;color:#cba6f7;font-size:1.4em;">↑<br><span style="font-size:0.6em;color:#6c7086;">loops to Critique</span></div>
          <div style="color:#a6e3a1;font-size:1.4em;">↓</div>
        </div>
      </div>
      <div class="cycle-arrow-down">↓</div>
      <div style="margin:8px 0;"><div style="background:#1e1e2e;border:2px solid #a6e3a1;border-radius:8px;padding:10px;display:inline-block;min-width:200px;">
        🏁 <strong>Finalizer</strong><br><small style="color:#6c7086;">Picks best-scoring iteration</small>
      </div></div>
      <div class="cycle-arrow-down">↓</div>
      <div style="display:flex;justify-content:center;gap:14px;flex-wrap:wrap;margin-top:8px;">
        <div style="background:#313244;border-radius:8px;padding:10px;min-width:120px;">📝 Side-by-side</div>
        <div style="background:#313244;border-radius:8px;padding:10px;min-width:120px;">🔀 Track changes</div>
        <div style="background:#313244;border-radius:8px;padding:10px;min-width:120px;">🔖 Checkpoint</div>
        <div style="background:#313244;border-radius:8px;padding:10px;min-width:120px;">⬇️ PDF export</div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🛠️ Tech Stack")
    cols = st.columns(4)
    for col, icon, name, desc in zip(cols, ["🦜","⚡","🗄️","🎨"], ["LangGraph","Groq API","ChromaDB","Streamlit"], ["Agentic cycles + checkpointing","llama-3.3-70b-versatile","Vector search","Dark theme UI"]):
        with col: st.markdown(f'<div class="agent-card" style="text-align:center;">{icon} <strong>{name}</strong><br><small>{desc}</small></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════
# TAB 5 — HISTORY
# ══════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown("### 📋 Analysis History")
    history = get_history()
    if history:
        for entry in history:
            score = entry.get("risk_score", 0); css, label = get_risk_color(score)
            with st.expander(f"📄 {entry['filename']} — {entry['timestamp']} — {score}/100"):
                c1, c2 = st.columns(2)
                with c1:
                    sc = "status-complete" if entry["status"] == "complete" else "status-failed"
                    st.markdown(f'<span class="{sc}">{entry["status"].upper()}</span>', unsafe_allow_html=True)
                with c2: st.markdown(f"🌐 **Language:** {entry.get('language','English')}")
                if entry["summary"]: st.markdown(f'<div class="report-section">{entry["summary"]}</div>', unsafe_allow_html=True)
                if entry["report"]: st.download_button("⬇️ Download", entry["report"], f"{entry['filename']}_report.txt", "text/plain", key=f"dl_{entry['id']}")
    else:
        st.info("💡 No analyses yet.")

# ══════════════════════════════════════════════════════════════════════
# TAB 6 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════
with tab_stats:
    st.markdown("### 📊 Dashboard")
    stats = get_dashboard_stats()
    cols  = st.columns(4)
    for col, icon, val, label in zip(cols, ["📄","✅","❌","🎯"], [stats["total"],stats["successful"],stats["failed"],stats["avg_risk"]], ["Total Analyses","Successful","Failed","Avg Risk Score"]):
        with col: st.markdown(f'<div class="metric-card">{icon}<b>{val}</b>{label}</div>', unsafe_allow_html=True)
    if stats["recent"]:
        st.markdown("### 🕓 Recently Analyzed")
        for item in stats["recent"]:
            score = item.get("risk_score", 0); css, label = get_risk_color(score)
            st.markdown(f'<div class="agent-card" style="display:flex;justify-content:space-between;align-items:center;"><span>📄 <strong>{item["filename"]}</strong> — {item["timestamp"]}</span><span class="{css}" style="font-size:1em;">{score}/100 {label}</span></div>', unsafe_allow_html=True)