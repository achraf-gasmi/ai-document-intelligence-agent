import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import time
import uuid
import asyncio
import difflib
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
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

# ── Checkpointing DB path ─────────────────────────────────────────────
# Kept separate from interactions.db (app data) intentionally.
# This is LangGraph infrastructure state — different lifecycle.
CHECKPOINT_DB = "logs/checkpoints.db"
os.makedirs("logs", exist_ok=True)


# ── LLM instances ─────────────────────────────────────────────────────
llm = ChatGroq(
    model=os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile"),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

# VERIFIER FIX: separate LLM instance with temperature=0 (deterministic)
# and an adversarial system prompt so it grades independently of the
# improvement agent rather than rubber-stamping its own outputs.
verifier_llm = ChatGroq(
    model=os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile"),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)
VERIFIER_SYSTEM_PROMPT = """You are a harsh, skeptical document quality assessor.
Your job is to find what is STILL WRONG with a document after it has been edited.
Do NOT give credit for cosmetic changes. Do NOT be generous.
Score conservatively — if in doubt, score lower.
A score of 85+ means the document is genuinely publication-ready with no meaningful issues."""


# ══════════════════════════════════════════════════════════════════════
# RETRY WITH BACKOFF
# ══════════════════════════════════════════════════════════════════════
def retry_with_backoff(fn, *args, max_retries: int = 3, base_delay: float = 2.0, **kwargs):
    """Exponential backoff on 429/5xx. Fails immediately on other errors."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "502" in err_str or "503" in err_str:
                delay = base_delay * (2 ** attempt)
                print(f"[Retry] Attempt {attempt + 1}/{max_retries} — retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise
    raise last_error


async def async_retry_with_backoff(fn, *args, max_retries: int = 3, base_delay: float = 2.0, **kwargs):
    """Async version of retry_with_backoff using asyncio.sleep."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str or "502" in err_str or "503" in err_str:
                delay = base_delay * (2 ** attempt)
                print(f"[Async Retry] Attempt {attempt + 1}/{max_retries} — retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise
    raise last_error


# ══════════════════════════════════════════════════════════════════════
# SMART CHUNKING FOR LONG DOCUMENTS
# ══════════════════════════════════════════════════════════════════════
def extract_relevant_chunks(text: str, focus_hint: str = "", max_chars: int = 4000) -> str:
    """
    Short docs (<= max_chars): return as-is.
    Long docs: return intro chunk + highest keyword-overlap chunks
    based on focus_hint (e.g. the critique text).
    """
    if len(text) <= max_chars:
        return text

    chunk_size = 1000
    overlap    = 100
    chunks     = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)

    if not focus_hint or not chunks:
        head     = chunks[0] if chunks else ""
        tail     = chunks[-1] if len(chunks) > 1 else ""
        return (head + "\n\n[...]\n\n" + tail)[:max_chars]

    hint_words = set(re.findall(r'\b\w{4,}\b', focus_hint.lower()))
    scored     = []
    for i, chunk in enumerate(chunks):
        chunk_words   = set(re.findall(r'\b\w{4,}\b', chunk.lower()))
        overlap_score = len(hint_words & chunk_words)
        scored.append((overlap_score, i, chunk))

    selected = [chunks[0]]
    scored.sort(key=lambda x: (-x[0], x[1]))
    seen = {0}
    for score, idx, chunk in scored:
        if idx not in seen and len("\n\n".join(selected)) + len(chunk) < max_chars:
            selected.append(chunk)
            seen.add(idx)

    return "\n\n[...]\n\n".join(selected)


# ══════════════════════════════════════════════════════════════════════
# ANALYSIS PIPELINE — STATE
# ══════════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════════
# ANALYSIS PIPELINE — SYNC AGENTS
# ══════════════════════════════════════════════════════════════════════
def detect_language(text: str) -> str:
    try:
        prompt   = f"Detect the language of this text.\nReturn ONLY the language name in English.\n\nText: {text[:500]}\n\nLanguage:"
        response = retry_with_backoff(llm.invoke, prompt)
        return response.content.strip()
    except Exception:
        return "English"


def document_processor(state: DocumentState) -> DocumentState:
    print(f"\n[Agent 1] Processing: {state['filename']}")
    try:
        raw_text = extract_text_from_pdf.invoke({"file_path": state["file_path"]})
        if raw_text.startswith("Error"):
            return {**state, "error": raw_text, "status": "failed"}

        store_result = store_document.invoke({"file_path": state["file_path"], "content": raw_text})
        print(f"[Agent 1] {store_result}")

        language = detect_language(raw_text)
        return {**state, "raw_text": raw_text, "language": language, "status": "processed"}
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


def parallel_analysis(state: DocumentState) -> DocumentState:
    """
    ASYNC UPGRADE: delegates to async_parallel_analysis via asyncio.run()
    so all three LLM calls run concurrently with true async I/O.
    Falls back to sync ThreadPoolExecutor if an event loop is already running.
    """
    print(f"\n[Parallel] Running Agents 2, 3, 4 (async)...")
    raw_text = state["raw_text"]
    language = state.get("language", "English")

    try:
        # Use async implementation for true concurrent I/O
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in an async context (e.g. tests) — fall back to threads
            raise RuntimeError("event loop already running")
        result = asyncio.run(_async_parallel_analysis(raw_text, language))
    except RuntimeError:
        # Fallback: thread-based parallelism
        result = _sync_parallel_analysis(raw_text, language)

    if result.get("error"):
        return {**state, "error": result["error"], "status": "failed"}

    print("[Parallel] All 3 agents complete!")
    return {**state, **result, "status": "analyzed"}


async def _async_parallel_analysis(raw_text: str, language: str) -> dict:
    """
    True async parallel execution of summarizer, extractor, and risk agents.
    Uses ainvoke (async LangChain) with asyncio.gather for concurrent I/O.
    ~60% faster than sequential, no thread overhead.
    """
    async def run_summarizer():
        print("[Agent 2] Summarizing (async)...")
        result = await async_retry_with_backoff(
            summarize_text.ainvoke, {"text": raw_text, "language": language}
        )
        if isinstance(result, str) and result.startswith("Error"):
            raise RuntimeError(f"Summarizer: {result}")
        print(f"[Agent 2] Done ({len(result)} chars)")
        return result

    async def run_extractor():
        print("[Agent 3] Extracting key info (async)...")
        result = await async_retry_with_backoff(
            extract_key_info.ainvoke, {"text": raw_text, "language": language}
        )
        if isinstance(result, str) and result.startswith("Error"):
            raise RuntimeError(f"Extractor: {result}")
        print(f"[Agent 3] Done ({len(result)} chars)")
        return result

    async def run_risk():
        print("[Agent 4] Analyzing risks (async)...")
        result = await async_retry_with_backoff(
            flag_risks.ainvoke, {"text": raw_text, "language": language}
        )
        if isinstance(result, str) and result.startswith("Error"):
            raise RuntimeError(f"Risk flagger: {result}")
        print(f"[Agent 4] Done ({len(result)} chars)")
        return result

    try:
        summary, key_info, risks = await asyncio.gather(
            run_summarizer(),
            run_extractor(),
            run_risk()
        )
        return {"summary": summary, "key_info": key_info, "risks": risks}
    except Exception as e:
        return {"error": str(e)}


def _sync_parallel_analysis(raw_text: str, language: str) -> dict:
    """Fallback sync implementation using ThreadPoolExecutor."""
    def run_summarizer():
        result = retry_with_backoff(summarize_text.invoke, {"text": raw_text, "language": language})
        if isinstance(result, str) and result.startswith("Error"):
            raise RuntimeError(f"Summarizer: {result}")
        return result

    def run_extractor():
        result = retry_with_backoff(extract_key_info.invoke, {"text": raw_text, "language": language})
        if isinstance(result, str) and result.startswith("Error"):
            raise RuntimeError(f"Extractor: {result}")
        return result

    def run_risk():
        result = retry_with_backoff(flag_risks.invoke, {"text": raw_text, "language": language})
        if isinstance(result, str) and result.startswith("Error"):
            raise RuntimeError(f"Risk flagger: {result}")
        return result

    with ThreadPoolExecutor(max_workers=3) as executor:
        fs = executor.submit(run_summarizer), executor.submit(run_extractor), executor.submit(run_risk)
        try:
            summary, key_info, risks = fs[0].result(), fs[1].result(), fs[2].result()
            return {"summary": summary, "key_info": key_info, "risks": risks}
        except Exception as e:
            return {"error": str(e)}


def calculate_risk_score(state: DocumentState) -> DocumentState:
    print(f"\n[Risk Score] Calculating...")
    try:
        prompt = f"""You are a document risk assessment expert.
Analyze this document and assign a RISK score from 0 to 100.

IMPORTANT RULES:
- The score represents DANGER level — higher score = MORE dangerous/risky
- Consider the DOCUMENT TYPE first:
  * Certificate, award, informational document → score 0-10
  * Well-structured resume/CV → score 10-25
  * Complete contract with minor issues → score 25-45
  * Contract with several missing clauses → score 45-65
  * Contract with critical missing sections → score 65-85
  * Dangerous or critically incomplete legal document → score 85-100

SCORING GUIDE:
- 0-20:   🟢 Low Risk
- 21-50:  🟡 Medium Risk
- 51-80:  🔴 High Risk
- 81-100: ⛔ Critical Risk

Filename: {state['filename']}
Summary: {state['summary'][:500]}
Risk Analysis: {state['risks'][:1000]}

Return ONLY JSON: {{"score": 8, "reasoning": "..."}}

JSON:"""
        response = retry_with_backoff(llm.invoke, prompt)
        match    = re.search(r'\{.*?\}', response.content.strip(), re.DOTALL)
        if match:
            data      = json.loads(match.group())
            score     = max(0, min(100, int(data.get("score", 50))))
            reasoning = data.get("reasoning", "")
            print(f"[Risk Score] {score}/100 — {reasoning}")
            return {**state, "risk_score": score, "risk_reasoning": reasoning}
        return {**state, "risk_score": 50, "risk_reasoning": "Could not calculate score"}
    except Exception as e:
        return {**state, "risk_score": 50, "risk_reasoning": f"Error: {e}"}


def report_agent(state: DocumentState) -> DocumentState:
    print(f"\n[Agent 5] Generating report...")
    language  = state.get("language", "English")
    lang_note = f"\nIMPORTANT: Write the entire report in {language}." if language != "English" else ""
    try:
        prompt = f"""Create a professional document analysis report.

SUMMARY:\n{state['summary']}
KEY INFORMATION:\n{state['key_info']}
RISK ANALYSIS:\n{state['risks']}
RISK SCORE: {state['risk_score']}/100

Document: {state['filename']}{lang_note}

Report:"""
        response = retry_with_backoff(llm.invoke, prompt)
        report   = response.content.strip()
        print(f"[Agent 5] Done ({len(report)} chars)")
        return {**state, "report": report, "status": "complete"}
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


def generate_suggested_questions(text: str, language: str = "English") -> list:
    try:
        lang_note = f"Generate questions in {language}." if language != "English" else ""
        prompt    = f"""Generate exactly 5 specific questions a user might ask about this document. {lang_note}
Return ONLY a JSON array of 5 strings.

Document:\n{text[:3000]}

Questions:"""
        response = retry_with_backoff(llm.invoke, prompt)
        match    = re.search(r'\[.*?\]', response.content.strip(), re.DOTALL)
        if match:
            return json.loads(match.group())[:5]
        return []
    except Exception as e:
        print(f"[Questions] Error: {e}")
        return []


def questions_agent(state: DocumentState) -> DocumentState:
    print(f"\n[Questions] Generating suggestions...")
    questions = generate_suggested_questions(state["raw_text"], state.get("language", "English"))
    print(f"[Questions] Generated {len(questions)} questions")
    return {**state, "suggested_questions": questions}


def should_continue(state: DocumentState) -> str:
    if state.get("status") == "failed":
        print(f"[Router] Failed: {state.get('error')}")
        return END
    return "continue"


def build_pipeline():
    graph = StateGraph(DocumentState)
    graph.add_node("document_processor", document_processor)
    graph.add_node("parallel_analysis",  parallel_analysis)
    graph.add_node("risk_score",         calculate_risk_score)
    graph.add_node("report_generator",   report_agent)
    graph.add_node("questions_agent",    questions_agent)

    graph.set_entry_point("document_processor")
    graph.add_conditional_edges("document_processor", should_continue, {"continue": "parallel_analysis", END: END})
    graph.add_conditional_edges("parallel_analysis",  should_continue, {"continue": "risk_score",        END: END})
    graph.add_conditional_edges("risk_score",         should_continue, {"continue": "report_generator",  END: END})
    graph.add_conditional_edges("report_generator",   should_continue, {"continue": "questions_agent",   END: END})
    graph.add_edge("questions_agent", END)
    return graph.compile()


pipeline = build_pipeline()


def answer_question(question: str, filename: str, language: str = "English") -> str:
    print(f"\n[Q&A] {question}")
    try:
        context   = search_document.invoke({"query": question, "filename": ""})
        lang_note = f"Answer in {language}." if language != "English" else ""
        prompt    = f"""You are a document analysis assistant.
Answer based ONLY on the document content. Be specific and direct. {lang_note}

Document: {filename}
Question: {question}

Relevant sections:
{context}

Answer:"""
        response = retry_with_backoff(llm.invoke, prompt)
        return response.content.strip()
    except Exception as e:
        return f"Error answering question: {e}"


def analyze_document(file_path: str) -> dict:
    filename = os.path.basename(file_path)
    print(f"\n{'='*50}\nStarting analysis: {filename}\n{'='*50}")

    result = pipeline.invoke(DocumentState(
        file_path=file_path, filename=filename, raw_text="",
        summary="", key_info="", risks="", risk_score=0,
        risk_reasoning="", report="", language="English",
        suggested_questions=[], status="starting", error=""
    ))

    return {
        "filename":            result["filename"],
        "raw_text":            result["raw_text"],
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
# IMPROVEMENT PIPELINE — STATE
# ══════════════════════════════════════════════════════════════════════
class ImprovementState(TypedDict):
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
    doc_type:             str
    critique:             str
    improved_text:        str
    diff_markers:         str
    iteration:            int
    improvement_score:    int
    improvement_history:  list
    final_text:           str
    improvement_status:   str
    thread_id:            str   # ← CHECKPOINTING: unique run ID for resuming


# ══════════════════════════════════════════════════════════════════════
# IMPROVEMENT PIPELINE — AGENTS
# ══════════════════════════════════════════════════════════════════════
def detect_document_type(state: ImprovementState) -> ImprovementState:
    print(f"\n[DocType] Detecting for: {state['filename']}")
    try:
        prompt = f"""Classify this document into ONE of: Resume/CV, Legal Contract, Report, Certificate.
Return ONLY the type name.

Filename: {state['filename']}
Content: {state['raw_text'][:1000]}

Type:"""
        response = retry_with_backoff(llm.invoke, prompt)
        doc_type = response.content.strip()
        known    = ["Resume/CV", "Legal Contract", "Report", "Certificate"]
        doc_type = next((t for t in known if t.lower() in doc_type.lower()), "Report")
        print(f"[DocType] {doc_type}")
        return {**state, "doc_type": doc_type, "improvement_status": "improving"}
    except Exception as e:
        return {**state, "doc_type": "Report", "error": str(e)}


DOC_TYPE_CRITIQUE_RULES = {
    "Resume/CV": """
- Missing/weak sections (Summary, Skills, Experience, Education, Achievements)
- Vague bullets without metrics ("helped team" → "led team of 5, increased X by 30%")
- Missing ATS keywords, poor formatting, spelling/grammar issues
""",
    "Legal Contract": """
- Missing clauses (payment terms, termination, liability, dispute resolution, governing law)
- Ambiguous terms, one-sided obligations, missing party details or signatures section
""",
    "Report": """
- Missing executive summary or conclusion, unsupported claims, poor logical flow
- Missing recommendations, vague scope
""",
    "Certificate": """
- Missing authenticity markers (issuer, date, signature fields)
- Incomplete recipient info, missing validity period, unprofessional language
"""
}

DOC_TYPE_IMPROVE_RULES = {
    "Resume/CV":      "Strengthen bullets with metrics, add missing sections, improve ATS keywords, professional tone.",
    "Legal Contract": "Add missing clauses, clarify ambiguous terms, balance obligations, define all parties and dates.",
    "Report":         "Add executive summary/conclusion, support claims with data placeholders, improve flow, add recommendations.",
    "Certificate":    "Add issuer details, recipient info, validity period, professional language, authenticity markers."
}

def critique_agent(state: ImprovementState) -> ImprovementState:
    iteration        = state.get("iteration", 0) + 1
    print(f"\n[Critique] Round {iteration}")
    base_text        = state.get("improved_text") or state["raw_text"]
    rules            = DOC_TYPE_CRITIQUE_RULES.get(state["doc_type"], DOC_TYPE_CRITIQUE_RULES["Report"])
    text_to_critique = extract_relevant_chunks(base_text, focus_hint="", max_chars=5000)
    try:
        prompt = f"""You are an expert {state['doc_type']} reviewer. Iteration {iteration}/3.

Focus on these issues:
{rules}

For EACH problem:
1. SECTION: which part
2. PROBLEM: what's wrong (specific)
3. SEVERITY: Critical / Major / Minor
4. FIX: exact instruction

If already excellent, say "NO ISSUES FOUND".

Document:
{text_to_critique}

Critique:"""
        response = retry_with_backoff(llm.invoke, prompt)
        critique = response.content.strip()
        print(f"[Critique] Done ({len(critique)} chars)")
        return {**state, "critique": critique, "iteration": iteration}
    except Exception as e:
        return {**state, "error": str(e), "improvement_status": "failed"}


def improvement_agent(state: ImprovementState) -> ImprovementState:
    print(f"\n[Improvement] Round {state['iteration']}")
    base_text       = state.get("improved_text") or state["raw_text"]
    improve_rules   = DOC_TYPE_IMPROVE_RULES.get(state["doc_type"], DOC_TYPE_IMPROVE_RULES["Report"])
    text_to_improve = extract_relevant_chunks(base_text, focus_hint=state.get("critique", ""), max_chars=4000)
    try:
        prompt = f"""You are an expert {state['doc_type']} writer. Fix the document based on the critique.

Rules: {improve_rules}

CRITIQUE:
{state['critique']}

INSTRUCTIONS:
1. Fix ALL Critical and Major issues
2. Preserve good structure
3. Language: {state.get('language', 'English')}
4. Mark changed sections with [IMPROVED]
5. Output the COMPLETE improved document

Document:
{text_to_improve}

Improved Document:"""
        response      = retry_with_backoff(llm.invoke, prompt)
        improved_text = response.content.strip()
        diff_markers  = generate_diff_markers(base_text, improved_text)
        print(f"[Improvement] Done ({len(improved_text)} chars)")
        return {**state, "improved_text": improved_text, "diff_markers": diff_markers}
    except Exception as e:
        return {**state, "error": str(e), "improvement_status": "failed"}


def generate_diff_markers(original: str, improved: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        improved.splitlines(keepends=True),
        fromfile="Original", tofile="Improved", lineterm=""
    )
    out = []
    for line in diff:
        if line.startswith("+++") or line.startswith("---"): out.append(line)
        elif line.startswith("+"): out.append(f"[ADDED]    {line[1:].strip()}")
        elif line.startswith("-"): out.append(f"[REMOVED]  {line[1:].strip()}")
        elif line.startswith("@@"): out.append("\n--- Section ---")
    return "\n".join(out) if out else "No structural changes detected."


def verifier_agent(state: ImprovementState) -> ImprovementState:
    """
    VERIFIER FIX: uses verifier_llm (temperature=0, adversarial system prompt)
    instead of the same llm instance used by improvement_agent.
    Grades independently — won't rubber-stamp its own outputs.

    CHECKPOINTING: state is persisted after every verifier pass via SqliteSaver,
    so a crash on iteration 2 can be resumed from the last checkpoint.
    """
    print(f"\n[Verifier] Round {state['iteration']} (adversarial, t=0)")
    try:
        text_to_score = extract_relevant_chunks(
            state["improved_text"],
            focus_hint=state.get("critique", ""),
            max_chars=3000
        )

        # Use messages format to inject adversarial system prompt
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=VERIFIER_SYSTEM_PROMPT),
            HumanMessage(content=f"""Score this {state['doc_type']} on quality (0–100).

SCORING GUIDE:
- 0–30:   Poor — major issues remain
- 31–60:  Below average — significant problems
- 61–84:  Acceptable — minor issues remain
- 85–100: Excellent — genuinely publication-ready

Critique that was addressed:
{state['critique'][:500]}

Document to score:
{text_to_score}

Return ONLY JSON:
{{"score": 72, "verdict": "...", "remaining_issues": "..."}}

JSON:""")
        ]

        response = retry_with_backoff(verifier_llm.invoke, messages)
        content  = response.content.strip()

        match = re.search(r'\{.*?\}', content, re.DOTALL)
        if match:
            data      = json.loads(match.group())
            score     = max(0, min(100, int(data.get("score", 50))))
            verdict   = data.get("verdict", "")
            remaining = data.get("remaining_issues", "")

            print(f"[Verifier] Score: {score}/100 — {verdict}")

            # FIX #2: copy list before appending (no in-place mutation)
            history = list(state.get("improvement_history", []))
            history.append({
                "iteration":     state["iteration"],
                "score":         score,
                "critique":      state["critique"],
                "improved_text": state["improved_text"],
                "diff_markers":  state.get("diff_markers", ""),
                "verdict":       verdict,
                "remaining":     remaining
            })
            return {**state, "improvement_score": score, "improvement_history": history}

        return {**state, "improvement_score": 50}

    except Exception as e:
        print(f"[Verifier] Error: {e}")
        return {**state, "improvement_score": 50, "error": str(e)}


def finalizer(state: ImprovementState) -> ImprovementState:
    print(f"\n[Finalizer] After {state['iteration']} iteration(s)")
    history = state.get("improvement_history", [])
    if history:
        best       = max(history, key=lambda x: x["score"])
        final_text = best["improved_text"]
        print(f"[Finalizer] Best score: {best['score']}/100")
    else:
        final_text = state.get("improved_text", state["raw_text"])
    return {**state, "final_text": final_text, "improvement_status": "done"}


def should_loop(state: ImprovementState) -> str:
    score     = state.get("improvement_score", 0)
    iteration = state.get("iteration", 0)
    status    = state.get("improvement_status", "improving")

    if status == "failed":   return "finalize"
    if score >= 85:          print(f"[Router] ✅ {score}/100 — done."); return "finalize"
    if iteration >= 3:       print(f"[Router] ⚠️ Max iterations at {score}/100."); return "finalize"

    print(f"[Router] 🔄 {score}/100 < 85, round {iteration}/3 — looping.")
    return "loop"


# ══════════════════════════════════════════════════════════════════════
# CHECKPOINTED IMPROVEMENT PIPELINE
# ══════════════════════════════════════════════════════════════════════
def build_improvement_pipeline(checkpointer=None):
    """
    CHECKPOINTING: accepts an optional SqliteSaver checkpointer.
    When provided, LangGraph persists full state after every node.
    Each run is identified by thread_id — pass the same thread_id
    to resume from the last completed node after a crash.
    """
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
    graph.add_conditional_edges("verifier_agent", should_loop,
        {"loop": "critique_agent", "finalize": "finalizer"})
    graph.add_edge("finalizer", END)

    return graph.compile(checkpointer=checkpointer)


def _get_checkpointer():
    """Return a SqliteSaver instance backed by logs/checkpoints.db."""
    return SqliteSaver.from_conn_string(CHECKPOINT_DB)


# ── Public entry points ───────────────────────────────────────────────

def improve_document(file_path: str, existing_analysis: dict = None,
                     thread_id: str = None) -> dict:
    """
    Run the self-correcting improvement loop with full checkpointing.

    Args:
        file_path:         Path to the PDF.
        existing_analysis: Result from analyze_document() — skips re-analysis if present.
        thread_id:         Pass a previous thread_id to RESUME a crashed run.
                           If None, a new UUID is generated for this run.

    Returns:
        Dict with results + thread_id (save this to enable resumption).
    """
    filename  = os.path.basename(file_path)
    thread_id = thread_id or str(uuid.uuid4())

    print(f"\n{'='*50}")
    print(f"Improvement loop: {filename}  [thread: {thread_id[:8]}...]")
    print(f"{'='*50}")

    if existing_analysis and existing_analysis.get("raw_text"):
        print("[Improve] Reusing existing analysis.")
        base = existing_analysis
    else:
        print("[Improve] Running full analysis pipeline first.")
        base = analyze_document(file_path)
        if base.get("status") == "failed":
            return {"error": base.get("error", "Analysis failed"), "status": "failed"}

    initial_state = ImprovementState(
        file_path=file_path, filename=filename,
        raw_text=base.get("raw_text", ""),
        summary=base.get("summary", ""),
        key_info=base.get("key_info", ""),
        risks=base.get("risks", ""),
        risk_score=base.get("risk_score", 50),
        risk_reasoning=base.get("risk_reasoning", ""),
        report=base.get("report", ""),
        language=base.get("language", "English"),
        suggested_questions=base.get("suggested_questions", []),
        status=base.get("status", "complete"),
        error="",
        doc_type="", critique="", improved_text="",
        diff_markers="", iteration=0, improvement_score=0,
        improvement_history=[], final_text="",
        improvement_status="improving",
        thread_id=thread_id
    )

    with _get_checkpointer() as checkpointer:
        imp_pipeline = build_improvement_pipeline(checkpointer=checkpointer)
        config       = {"configurable": {"thread_id": thread_id}}
        result       = imp_pipeline.invoke(initial_state, config=config)

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
        "thread_id":           thread_id,   # ← caller should store this
        "error":               result.get("error", "")
    }


def resume_improvement(thread_id: str) -> dict:
    """
    Resume a previously interrupted improvement run from its last checkpoint.

    Usage:
        result = resume_improvement(st.session_state.improve_thread_id)

    The pipeline resumes from the last successfully completed node —
    no re-running of already-finished agents.
    """
    print(f"\n[Resume] Resuming thread: {thread_id[:8]}...")
    with _get_checkpointer() as checkpointer:
        imp_pipeline = build_improvement_pipeline(checkpointer=checkpointer)
        config       = {"configurable": {"thread_id": thread_id}}
        # Invoking with None state causes LangGraph to load from checkpoint
        result       = imp_pipeline.invoke(None, config=config)

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
        "thread_id":           thread_id,
        "error":               result.get("error", "")
    }


# ══════════════════════════════════════════════════════════════════════
# CLI TEST
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = analyze_document(sys.argv[1])
        print(f"\n{'='*50}\nFINAL REPORT\n{'='*50}")
        print(result["report"])
        print(f"\nStatus:    {result['status']}")
        print(f"Language:  {result['language']}")
        print(f"Risk Score:{result['risk_score']}/100")
    else:
        print("Usage: python src/agents.py <path_to_pdf>")