import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import difflib
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from src.tools import (
    extract_text_from_pdf,
    store_document,
    summarize_text,
    extract_key_info,
    flag_risks,
    generate_report,
    search_document
)

load_dotenv()

# ── LLM ───────────────────────────────────────────────────────────────
llm = ChatGroq(
    model=os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile"),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)


# ══════════════════════════════════════════════════════════════════════
# ANALYSIS PIPELINE
# ══════════════════════════════════════════════════════════════════════

# ── State ─────────────────────────────────────────────────────────────
class DocumentState(TypedDict):
    file_path:           str
    filename:            str
    raw_text:            str
    summary:             str
    key_info:            str
    risks:               str
    risk_score:          int
    risk_reasoning:      str
    report:              str
    language:            str
    suggested_questions: list
    status:              str
    error:               str


# ── Language Detection ────────────────────────────────────────────────
def detect_language(text: str) -> str:
    """Detect document language using LLM."""
    try:
        prompt = f"""Detect the language of this text.
Return ONLY the language name in English (e.g. English, French, Arabic, Spanish).

Text: {text[:500]}

Language:"""
        response = llm.invoke(prompt)
        language = response.content.strip()
        print(f"[Language] Detected: {language}")
        return language
    except Exception:
        return "English"


# ── Agent 1: Document Processor ───────────────────────────────────────
def document_processor(state: DocumentState) -> DocumentState:
    """Extracts, stores document text and detects language."""
    print(f"\n[Agent 1] Processing document: {state['filename']}")
    try:
        raw_text = extract_text_from_pdf.invoke({"file_path": state["file_path"]})

        if raw_text.startswith("Error"):
            return {**state, "error": raw_text, "status": "failed"}

        store_result = store_document.invoke({
            "file_path": state["file_path"],
            "content":   raw_text
        })
        print(f"[Agent 1] {store_result}")

        language = detect_language(raw_text)

        return {
            **state,
            "raw_text": raw_text,
            "language": language,
            "status":   "processed"
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


# ── Agents 2, 3, 4: Parallel Execution ───────────────────────────────
def parallel_analysis(state: DocumentState) -> DocumentState:
    """Run summarizer, extractor, and risk agents in parallel."""
    print(f"\n[Parallel] Running Agents 2, 3, 4 simultaneously...")
    raw_text = state["raw_text"]
    language = state.get("language", "English")

    def run_summarizer():
        print("[Agent 2] Summarizing...")
        result = summarize_text.invoke({"text": raw_text, "language": language})
        print(f"[Agent 2] Done ({len(result)} chars)")
        return result

    def run_extractor():
        print("[Agent 3] Extracting key info...")
        result = extract_key_info.invoke({"text": raw_text, "language": language})
        print(f"[Agent 3] Done ({len(result)} chars)")
        return result

    def run_risk():
        print("[Agent 4] Analyzing risks...")
        result = flag_risks.invoke({"text": raw_text, "language": language})
        print(f"[Agent 4] Done ({len(result)} chars)")
        return result

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_summary  = executor.submit(run_summarizer)
        future_key_info = executor.submit(run_extractor)
        future_risks    = executor.submit(run_risk)

        summary  = future_summary.result()
        key_info = future_key_info.result()
        risks    = future_risks.result()

    print("[Parallel] All 3 agents complete!")

    return {
        **state,
        "summary":  summary,
        "key_info": key_info,
        "risks":    risks,
        "status":   "analyzed"
    }


# ── Risk Score Calculator (Smart) ─────────────────────────────────────
def calculate_risk_score(state: DocumentState) -> DocumentState:
    """Smart context-aware risk scoring using LLM."""
    print(f"\n[Risk Score] Calculating smart score...")
    try:
        prompt = f"""You are a document risk assessment expert.
Analyze this document and assign a RISK score from 0 to 100.

IMPORTANT RULES:
- The score represents DANGER level — higher score = MORE dangerous/risky
- Consider the DOCUMENT TYPE first:
  * Certificate, award, informational document → score 0-10 (very low risk)
  * Well-structured resume/CV → score 10-25 (low risk)
  * Complete contract with minor issues → score 25-45 (moderate risk)
  * Contract with several missing clauses → score 45-65 (high risk)
  * Contract with critical missing sections → score 65-85 (very high risk)
  * Dangerous or critically incomplete legal document → score 85-100 (extreme risk)

SCORING GUIDE:
- 0-20:   🟢 Low Risk — safe document, no legal obligations
- 21-50:  🟡 Medium Risk — some concerns worth reviewing
- 51-80:  🔴 High Risk — significant issues need attention
- 81-100: ⛔ Critical Risk — immediate action required

Document Type Context:
- Filename: {state['filename']}
- Summary: {state['summary'][:500]}
- Risk Analysis: {state['risks'][:1000]}

Return ONLY a JSON object like this:
{{"score": 8, "reasoning": "This is a certificate with no legal obligations or risks."}}

JSON:"""

        response = llm.invoke(prompt)
        content  = response.content.strip()

        match = re.search(r'\{.*?\}', content, re.DOTALL)
        if match:
            data      = json.loads(match.group())
            score     = int(data.get("score", 50))
            reasoning = data.get("reasoning", "")
            score     = max(0, min(100, score))
            print(f"[Risk Score] Score: {score}/100 — {reasoning}")
            return {**state, "risk_score": score, "risk_reasoning": reasoning}

        return {**state, "risk_score": 50, "risk_reasoning": "Could not calculate score"}

    except Exception as e:
        print(f"[Risk Score] Error: {e}")
        return {**state, "risk_score": 50, "risk_reasoning": "Error calculating score"}


# ── Agent 5: Report Generator ─────────────────────────────────────────
def report_agent(state: DocumentState) -> DocumentState:
    """Combines all analysis into a final report."""
    print(f"\n[Agent 5] Generating final report...")
    language = state.get("language", "English")
    try:
        lang_note = f"\nIMPORTANT: Write the entire report in {language}." if language != "English" else ""
        prompt = f"""Create a professional document analysis report based on the following:

SUMMARY:
{state['summary']}

KEY INFORMATION:
{state['key_info']}

RISK ANALYSIS:
{state['risks']}

RISK SCORE: {state['risk_score']}/100

Format as a clean, professional report with clear sections.
Document: {state['filename']}
{lang_note}

Report:"""
        response = llm.invoke(prompt)
        report   = response.content.strip()
        print(f"[Agent 5] Report generated ({len(report)} chars)")
        return {**state, "report": report, "status": "complete"}
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


# ── Suggested Questions Generator ────────────────────────────────────
def generate_suggested_questions(text: str, language: str = "English") -> list:
    """Generate document-specific suggested questions."""
    try:
        lang_note = f"Generate questions in {language}." if language != "English" else ""
        prompt = f"""Based on this document, generate exactly 5 specific and relevant questions
a user might want to ask about it. {lang_note}
Return ONLY a JSON array of 5 strings, nothing else.
Example: ["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]

Document:
{text[:3000]}

Questions:"""
        response = llm.invoke(prompt)
        content  = response.content.strip()
        match    = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            questions = json.loads(match.group())
            return questions[:5]
        return []
    except Exception as e:
        print(f"[Questions] Error: {e}")
        return []


# ── Agent 6: Questions Generator ─────────────────────────────────────
def questions_agent(state: DocumentState) -> DocumentState:
    """Generate document-specific suggested questions."""
    print(f"\n[Questions] Generating suggested questions...")
    questions = generate_suggested_questions(
        state["raw_text"],
        state.get("language", "English")
    )
    print(f"[Questions] Generated {len(questions)} questions")
    return {**state, "suggested_questions": questions}


# ── Router ────────────────────────────────────────────────────────────
def should_continue(state: DocumentState) -> str:
    """Route to next agent or end on failure."""
    if state.get("status") == "failed":
        print(f"[Router] Pipeline failed: {state.get('error')}")
        return END
    return "continue"


# ── Build LangGraph ───────────────────────────────────────────────────
def build_pipeline():
    graph = StateGraph(DocumentState)

    graph.add_node("document_processor", document_processor)
    graph.add_node("parallel_analysis",  parallel_analysis)
    graph.add_node("risk_score",         calculate_risk_score)
    graph.add_node("report_generator",   report_agent)
    graph.add_node("questions_agent",    questions_agent)

    graph.set_entry_point("document_processor")

    graph.add_conditional_edges("document_processor", should_continue,
        {"continue": "parallel_analysis", END: END})
    graph.add_conditional_edges("parallel_analysis", should_continue,
        {"continue": "risk_score", END: END})
    graph.add_conditional_edges("risk_score", should_continue,
        {"continue": "report_generator", END: END})
    graph.add_conditional_edges("report_generator", should_continue,
        {"continue": "questions_agent", END: END})
    graph.add_edge("questions_agent", END)

    return graph.compile()


# ── Pipeline instance ─────────────────────────────────────────────────
pipeline = build_pipeline()


# ── Q&A Mode ─────────────────────────────────────────────────────────
def answer_question(question: str, filename: str, language: str = "English") -> str:
    """Answer a question about an already-analyzed document."""
    print(f"\n[Q&A] Question: {question}")
    try:
        context = search_document.invoke({
            "query":    question,
            "filename": ""
        })

        lang_note = f"Answer in {language}." if language != "English" else ""
        prompt    = f"""You are a document analysis assistant.
Answer the question based ONLY on the document content provided.
If the answer is not explicitly stated but can be inferred, provide that inference clearly.
Be specific and direct. {lang_note}

Document: {filename}
Question: {question}

Relevant document sections:
{context}

Answer:"""
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"Error answering question: {e}"


# ── Main entry point ──────────────────────────────────────────────────
def analyze_document(file_path: str) -> dict:
    """Run the full multi-agent pipeline on a document."""
    filename = os.path.basename(file_path)
    print(f"\n{'='*50}")
    print(f"Starting analysis: {filename}")
    print(f"{'='*50}")

    initial_state = DocumentState(
        file_path           = file_path,
        filename            = filename,
        raw_text            = "",
        summary             = "",
        key_info            = "",
        risks               = "",
        risk_score          = 0,
        risk_reasoning      = "",
        report              = "",
        language            = "English",
        suggested_questions = [],
        status              = "starting",
        error               = ""
    )

    result = pipeline.invoke(initial_state)

    return {
        "filename":            result["filename"],
        "raw_text":            result["raw_text"],        # ← required by improve_document()
        "summary":             result["summary"],
        "key_info":            result["key_info"],
        "risks":               result["risks"],
        "risk_score":          result.get("risk_score", 0),
        "risk_reasoning":      result.get("risk_reasoning", ""),
        "report":              result["report"],
        "language":            result.get("language", "English"),
        "suggested_questions": result.get("suggested_questions", []),
        "status":              result["status"],
        "error":               result.get("error", "")
    }


# ══════════════════════════════════════════════════════════════════════
# IMPROVEMENT PIPELINE
# ══════════════════════════════════════════════════════════════════════

# ── Improvement State ─────────────────────────────────────────────────
class ImprovementState(TypedDict):
    # ── Carried over from analysis ──
    file_path:            str
    filename:             str
    raw_text:             str
    summary:              str
    key_info:             str
    risks:                str
    risk_score:           int
    risk_reasoning:       str
    report:               str
    language:             str
    suggested_questions:  list
    status:               str
    error:                str

    # ── Improvement-specific ──
    doc_type:             str   # Resume/CV | Legal Contract | Report | Certificate
    critique:             str   # structured critique from Critique Agent
    improved_text:        str   # full rewritten document (updated each iteration)
    diff_markers:         str   # [ADDED]/[REMOVED] annotated diff
    iteration:            int   # current loop count (1–3)
    improvement_score:    int   # verifier score (0–100, higher = better quality)
    improvement_history:  list  # list of dicts, one per completed iteration
    final_text:           str   # best accepted version
    improvement_status:   str   # "improving" | "done" | "failed"


# ── Doc Type Detector ─────────────────────────────────────────────────
def detect_document_type(state: ImprovementState) -> ImprovementState:
    """Classify document type to guide all downstream improvement agents."""
    print(f"\n[DocType] Detecting document type for: {state['filename']}")
    try:
        prompt = f"""Classify this document into exactly ONE of these types:
- Resume/CV
- Legal Contract
- Report
- Certificate

Consider the filename and content carefully.
Return ONLY the type name, nothing else.

Filename: {state['filename']}
Content preview:
{state['raw_text'][:1000]}

Type:"""
        response = llm.invoke(prompt)
        doc_type = response.content.strip()

        known    = ["Resume/CV", "Legal Contract", "Report", "Certificate"]
        doc_type = next((t for t in known if t.lower() in doc_type.lower()), "Report")

        print(f"[DocType] Detected: {doc_type}")
        return {**state, "doc_type": doc_type, "improvement_status": "improving"}
    except Exception as e:
        return {**state, "doc_type": "Report", "error": str(e)}


# ── Critique Agent ────────────────────────────────────────────────────
DOC_TYPE_CRITIQUE_RULES = {
    "Resume/CV": """
- Missing or weak sections (Summary, Skills, Experience, Education, Achievements)
- Vague bullet points without metrics or impact (e.g. "helped team" → "led team of 5, increased X by 30%")
- Missing ATS keywords for the target industry
- Poor formatting or missing dates
- Spelling/grammar issues
""",
    "Legal Contract": """
- Missing essential clauses (payment terms, termination, liability, dispute resolution, governing law)
- Ambiguous or undefined terms
- One-sided or unbalanced obligations
- Missing party details or signatures section
- Unclear deliverables or deadlines
""",
    "Report": """
- Missing executive summary or conclusion
- Unsupported claims without data or citations
- Poor logical flow between sections
- Missing recommendations or action items
- Vague or undefined scope
""",
    "Certificate": """
- Missing authenticity markers (issuer details, date, signature fields)
- Incomplete recipient information
- Unclear achievement or scope of certification
- Missing validity period or expiry
- Unprofessional language or formatting
"""
}

def critique_agent(state: ImprovementState) -> ImprovementState:
    """Produce structured, doc-type-aware critique. Critiques improved_text on iterations > 1."""
    iteration = state.get("iteration", 0) + 1
    print(f"\n[Critique Agent] Round {iteration} — doc type: {state['doc_type']}")

    text_to_critique = state.get("improved_text") or state["raw_text"]
    rules = DOC_TYPE_CRITIQUE_RULES.get(state["doc_type"], DOC_TYPE_CRITIQUE_RULES["Report"])

    try:
        prompt = f"""You are an expert {state['doc_type']} reviewer.
Perform a detailed, structured critique of this document.

Document Type: {state['doc_type']}
Iteration: {iteration}/3

Focus specifically on these issues for this document type:
{rules}

For EACH problem found, provide:
1. SECTION: Which section/part has the issue
2. PROBLEM: What exactly is wrong (be specific)
3. SEVERITY: Critical / Major / Minor
4. FIX: Exact instruction for how to fix it

Format your response as a numbered list of issues.
Be specific — reference actual text from the document.
If the document is already excellent, say "NO ISSUES FOUND" and explain why.

Document:
{text_to_critique[:4000]}

Critique:"""

        response = llm.invoke(prompt)
        critique = response.content.strip()
        print(f"[Critique Agent] Done ({len(critique)} chars)")
        return {**state, "critique": critique, "iteration": iteration}
    except Exception as e:
        return {**state, "error": str(e), "improvement_status": "failed"}


# ── Improvement Agent ─────────────────────────────────────────────────
DOC_TYPE_IMPROVE_RULES = {
    "Resume/CV":      "Strengthen bullet points with metrics, add missing sections, improve ATS keywords, ensure professional tone.",
    "Legal Contract": "Add missing clauses, clarify ambiguous terms, balance obligations, ensure all parties and dates are defined.",
    "Report":         "Add executive summary/conclusion if missing, support claims with data placeholders, improve logical flow, add recommendations.",
    "Certificate":    "Add issuer details, recipient info, validity period, professional language, and authenticity markers."
}

def improvement_agent(state: ImprovementState) -> ImprovementState:
    """Rewrite and fix the document based on the critique. Updates improved_text each round."""
    print(f"\n[Improvement Agent] Round {state['iteration']} — applying fixes...")

    text_to_improve = state.get("improved_text") or state["raw_text"]
    improve_rules   = DOC_TYPE_IMPROVE_RULES.get(state["doc_type"], DOC_TYPE_IMPROVE_RULES["Report"])

    try:
        prompt = f"""You are an expert {state['doc_type']} writer and editor.
Your task: Rewrite and improve this document based on the critique below.

Document Type: {state['doc_type']}
Improvement Rules: {improve_rules}

CRITIQUE TO ADDRESS:
{state['critique']}

INSTRUCTIONS:
1. Fix ALL Critical and Major issues identified in the critique
2. Preserve the original structure where it is already good
3. Keep the same language ({state.get('language', 'English')})
4. Mark every section you changed with [IMPROVED] at the start of that section
5. Output the COMPLETE improved document — not just the changed parts

Original Document:
{text_to_improve[:4000]}

Improved Document:"""

        response      = llm.invoke(prompt)
        improved_text = response.content.strip()
        diff_markers  = generate_diff_markers(text_to_improve, improved_text)

        print(f"[Improvement Agent] Done ({len(improved_text)} chars)")
        return {**state, "improved_text": improved_text, "diff_markers": diff_markers}
    except Exception as e:
        return {**state, "error": str(e), "improvement_status": "failed"}


# ── Diff Generator ────────────────────────────────────────────────────
def generate_diff_markers(original: str, improved: str) -> str:
    """Generate a human-readable [ADDED]/[REMOVED] diff between two texts."""
    original_lines = original.splitlines(keepends=True)
    improved_lines = improved.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        improved_lines,
        fromfile="Original",
        tofile="Improved",
        lineterm=""
    )

    diff_output = []
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            diff_output.append(line)
        elif line.startswith("+"):
            diff_output.append(f"[ADDED]    {line[1:].strip()}")
        elif line.startswith("-"):
            diff_output.append(f"[REMOVED]  {line[1:].strip()}")
        elif line.startswith("@@"):
            diff_output.append("\n--- Section ---")

    return "\n".join(diff_output) if diff_output else "No structural changes detected."


# ── Verifier Agent ────────────────────────────────────────────────────
def verifier_agent(state: ImprovementState) -> ImprovementState:
    """Score the improved document quality (0–100). Appends result to improvement_history."""
    print(f"\n[Verifier] Round {state['iteration']} — scoring improved document...")
    try:
        prompt = f"""You are a strict document quality assessor.
Score this {state['doc_type']} on how GOOD and COMPLETE it is (0–100).

SCORING GUIDE (higher = better quality):
- 0–30:   Poor — major sections missing, many critical issues
- 31–60:  Below average — several significant problems remain
- 61–84:  Acceptable — minor issues, could still be improved
- 85–100: Excellent — professional quality, ready to use

Document Type: {state['doc_type']}
Previous Risk Score: {state.get('risk_score', 50)}/100 (lower was better before)
Critique that was addressed: {state['critique'][:500]}

Evaluate the improved document now:
{state['improved_text'][:3000]}

Return ONLY JSON like:
{{"score": 87, "verdict": "Document is now professional quality. All critical issues resolved.", "remaining_issues": "Minor: could add more metrics to bullet point 3."}}

JSON:"""

        response = llm.invoke(prompt)
        content  = response.content.strip()

        match = re.search(r'\{.*?\}', content, re.DOTALL)
        if match:
            data      = json.loads(match.group())
            score     = max(0, min(100, int(data.get("score", 50))))
            verdict   = data.get("verdict", "")
            remaining = data.get("remaining_issues", "")

            print(f"[Verifier] Score: {score}/100 — {verdict}")

            history = state.get("improvement_history", [])
            history.append({
                "iteration":     state["iteration"],
                "score":         score,
                "critique":      state["critique"],
                "improved_text": state["improved_text"],
                "diff_markers":  state.get("diff_markers", ""),
                "verdict":       verdict,
                "remaining":     remaining
            })

            return {
                **state,
                "improvement_score":   score,
                "improvement_history": history
            }

        return {**state, "improvement_score": 50}

    except Exception as e:
        print(f"[Verifier] Error: {e}")
        return {**state, "improvement_score": 50, "error": str(e)}


# ── Finalizer ─────────────────────────────────────────────────────────
def finalizer(state: ImprovementState) -> ImprovementState:
    """Select the best-scoring version from history as the final output."""
    print(f"\n[Finalizer] Wrapping up after {state['iteration']} iteration(s)...")

    history = state.get("improvement_history", [])
    if history:
        best        = max(history, key=lambda x: x["score"])
        final_text  = best["improved_text"]
        final_score = best["score"]
    else:
        final_text  = state.get("improved_text", state["raw_text"])
        final_score = state.get("improvement_score", 0)

    print(f"[Finalizer] Best score achieved: {final_score}/100")
    return {**state, "final_text": final_text, "improvement_status": "done"}


# ── Loop Router ───────────────────────────────────────────────────────
def should_loop(state: ImprovementState) -> str:
    """
    Route decision after each verifier pass:
      - score >= 85      → finalize (target reached)
      - iteration >= 3   → finalize (max iterations)
      - otherwise        → loop back to critique_agent
    """
    score     = state.get("improvement_score", 0)
    iteration = state.get("iteration", 0)
    status    = state.get("improvement_status", "improving")

    if status == "failed":
        print(f"[Router] Pipeline failed — finalizing.")
        return "finalize"

    if score >= 85:
        print(f"[Router] ✅ Score {score}/100 — target reached! Finalizing.")
        return "finalize"

    if iteration >= 3:
        print(f"[Router] ⚠️ Max iterations (3) reached with score {score}/100. Finalizing best version.")
        return "finalize"

    print(f"[Router] 🔄 Score {score}/100 < 85, iteration {iteration}/3 — looping back.")
    return "loop"


# ── Build Improvement Pipeline ────────────────────────────────────────
def build_improvement_pipeline():
    graph = StateGraph(ImprovementState)

    graph.add_node("detect_doc_type",   detect_document_type)
    graph.add_node("critique_agent",    critique_agent)
    graph.add_node("improvement_agent", improvement_agent)
    graph.add_node("verifier_agent",    verifier_agent)
    graph.add_node("finalizer",         finalizer)

    graph.set_entry_point("detect_doc_type")

    graph.add_edge("detect_doc_type",   "critique_agent")
    graph.add_edge("critique_agent",    "improvement_agent")
    graph.add_edge("improvement_agent", "verifier_agent")

    graph.add_conditional_edges(
        "verifier_agent",
        should_loop,
        {
            "loop":     "critique_agent",  # back to critique with updated improved_text
            "finalize": "finalizer"
        }
    )

    graph.add_edge("finalizer", END)

    return graph.compile()


# ── Pipeline Instance ─────────────────────────────────────────────────
improvement_pipeline = build_improvement_pipeline()


# ── Public Entry Point ────────────────────────────────────────────────
def improve_document(file_path: str, existing_analysis: dict = None) -> dict:
    """
    Run the self-correcting improvement loop on a document.

    Smart reuse logic:
      - If existing_analysis is passed (from Analyze tab session state) and contains
        raw_text, skips the full analysis pipeline and goes straight to improvement.
      - If existing_analysis is None or missing raw_text, runs analyze_document() first.

    Args:
        file_path:         Path to the PDF file.
        existing_analysis: Result dict from analyze_document() (optional).

    Returns:
        Dict with final improved text, diff, score, per-iteration history, and metadata.
    """
    filename = os.path.basename(file_path)
    print(f"\n{'='*50}")
    print(f"Starting improvement loop: {filename}")
    print(f"{'='*50}")

    if existing_analysis and existing_analysis.get("raw_text"):
        print("[Improve] Reusing existing analysis from session — skipping re-analysis.")
        base = existing_analysis
    else:
        print("[Improve] No prior analysis found — running full pipeline first.")
        base = analyze_document(file_path)
        if base.get("status") == "failed":
            return {"error": base.get("error", "Analysis failed"), "status": "failed"}

    initial_state = ImprovementState(
        # Carried over from analysis
        file_path            = file_path,
        filename             = filename,
        raw_text             = base.get("raw_text", base.get("report", "")),
        summary              = base.get("summary", ""),
        key_info             = base.get("key_info", ""),
        risks                = base.get("risks", ""),
        risk_score           = base.get("risk_score", 50),
        risk_reasoning       = base.get("risk_reasoning", ""),
        report               = base.get("report", ""),
        language             = base.get("language", "English"),
        suggested_questions  = base.get("suggested_questions", []),
        status               = base.get("status", "complete"),
        error                = "",
        # Improvement-specific
        doc_type             = "",
        critique             = "",
        improved_text        = "",
        diff_markers         = "",
        iteration            = 0,
        improvement_score    = 0,
        improvement_history  = [],
        final_text           = "",
        improvement_status   = "improving"
    )

    result = improvement_pipeline.invoke(initial_state)

    return {
        "filename":            result["filename"],
        "doc_type":            result["doc_type"],
        "language":            result["language"],
        "original_text":       result["raw_text"],
        "final_text":          result["final_text"],
        "diff_markers":        result.get("diff_markers", ""),
        "improvement_score":   result["improvement_score"],
        "total_iterations":    result["iteration"],
        "improvement_history": result.get("improvement_history", []),
        "improvement_status":  result["improvement_status"],
        "error":               result.get("error", "")
    }


# ══════════════════════════════════════════════════════════════════════
# CLI TEST
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = analyze_document(sys.argv[1])
        print(f"\n{'='*50}")
        print("FINAL REPORT:")
        print(f"{'='*50}")
        print(result["report"])
        print(f"\nStatus:              {result['status']}")
        print(f"Language:            {result['language']}")
        print(f"Risk Score:          {result['risk_score']}/100")
        print(f"Suggested Questions: {result['suggested_questions']}")
    else:
        print("Usage: python src/agents.py <path_to_pdf>")