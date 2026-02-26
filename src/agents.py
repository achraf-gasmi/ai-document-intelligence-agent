import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
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

# ── State ─────────────────────────────────────────────────────────────
class DocumentState(TypedDict):
    file_path:           str
    filename:            str
    raw_text:            str
    summary:             str
    key_info:            str
    risks:               str
    risk_score:          int
    risk_reasoning:      str      # ← add this
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
        # Search without filename filter
        context = search_document.invoke({
            "query":    question,
            "filename": ""  # empty string instead of None
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
        risk_reasoning      = "",      # ← add this
        report              = "",
        language            = "English",
        suggested_questions = [],
        status              = "starting",
        error               = ""
    )

    result = pipeline.invoke(initial_state)

    return {
        "filename":            result["filename"],
        "summary":             result["summary"],
        "key_info":            result["key_info"],
        "risks":               result["risks"],
        "risk_score":          result.get("risk_score", 0),
        "risk_reasoning":      result.get("risk_reasoning", ""),   # ← add this
        "report":              result["report"],
        "language":            result.get("language", "English"),
        "suggested_questions": result.get("suggested_questions", []),
        "status":              result["status"],
        "error":               result.get("error", "")
    }


# ── Test ──────────────────────────────────────────────────────────────
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