import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import TypedDict, Annotated
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage
from src.tools import (
    extract_text_from_pdf,
    store_document,
    summarize_text,
    extract_key_info,
    flag_risks,
    generate_report,
    all_tools
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
    file_path:    str
    filename:     str
    raw_text:     str
    summary:      str
    key_info:     str
    risks:        str
    report:       str
    status:       str
    error:        str


# ── Agent 1: Document Processor ───────────────────────────────────────
def document_processor(state: DocumentState) -> DocumentState:
    """Extracts and stores document text."""
    print(f"\n[Agent 1] Processing document: {state['filename']}")
    try:
        # Extract text
        raw_text = extract_text_from_pdf.invoke({"file_path": state["file_path"]})

        if raw_text.startswith("Error"):
            return {**state, "error": raw_text, "status": "failed"}

        # Store in ChromaDB
        store_result = store_document.invoke({
            "file_path": state["file_path"],
            "content":   raw_text
        })
        print(f"[Agent 1] {store_result}")

        return {
            **state,
            "raw_text": raw_text,
            "status":   "processed"
        }
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


# ── Agent 2: Summarizer ───────────────────────────────────────────────
def summarizer_agent(state: DocumentState) -> DocumentState:
    """Generates a concise document summary."""
    print(f"\n[Agent 2] Summarizing document...")
    try:
        summary = summarize_text.invoke({"text": state["raw_text"]})
        print(f"[Agent 2] Summary generated ({len(summary)} chars)")
        return {**state, "summary": summary, "status": "summarized"}
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


# ── Agent 3: Key Info Extractor ───────────────────────────────────────
def extractor_agent(state: DocumentState) -> DocumentState:
    """Extracts key information from the document."""
    print(f"\n[Agent 3] Extracting key information...")
    try:
        key_info = extract_key_info.invoke({"text": state["raw_text"]})
        print(f"[Agent 3] Key info extracted ({len(key_info)} chars)")
        return {**state, "key_info": key_info, "status": "extracted"}
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


# ── Agent 4: Risk Flagger ─────────────────────────────────────────────
def risk_agent(state: DocumentState) -> DocumentState:
    """Identifies risks and red flags in the document."""
    print(f"\n[Agent 4] Analyzing risks...")
    try:
        risks = flag_risks.invoke({"text": state["raw_text"]})
        print(f"[Agent 4] Risk analysis complete ({len(risks)} chars)")
        return {**state, "risks": risks, "status": "analyzed"}
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


# ── Agent 5: Report Generator ─────────────────────────────────────────
def report_agent(state: DocumentState) -> DocumentState:
    """Combines all analysis into a final report."""
    print(f"\n[Agent 5] Generating final report...")
    try:
        report = generate_report.invoke({
            "summary":  state["summary"],
            "key_info": state["key_info"],
            "risks":    state["risks"],
            "filename": state["filename"]
        })
        print(f"[Agent 5] Report generated ({len(report)} chars)")
        return {**state, "report": report, "status": "complete"}
    except Exception as e:
        return {**state, "error": str(e), "status": "failed"}


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

    # Add nodes
    graph.add_node("document_processor", document_processor)
    graph.add_node("summarizer",          summarizer_agent)
    graph.add_node("extractor",           extractor_agent)
    graph.add_node("risk_analyzer",       risk_agent)
    graph.add_node("report_generator",    report_agent)

    # Entry point
    graph.set_entry_point("document_processor")

    # Edges with failure routing
    graph.add_conditional_edges(
        "document_processor",
        should_continue,
        {"continue": "summarizer", END: END}
    )
    graph.add_conditional_edges(
        "summarizer",
        should_continue,
        {"continue": "extractor", END: END}
    )
    graph.add_conditional_edges(
        "extractor",
        should_continue,
        {"continue": "risk_analyzer", END: END}
    )
    graph.add_conditional_edges(
        "risk_analyzer",
        should_continue,
        {"continue": "report_generator", END: END}
    )
    graph.add_edge("report_generator", END)

    return graph.compile()


# ── Pipeline instance ─────────────────────────────────────────────────
pipeline = build_pipeline()


# ── Main entry point ──────────────────────────────────────────────────
def analyze_document(file_path: str) -> dict:
    """Run the full multi-agent pipeline on a document."""
    filename = os.path.basename(file_path)
    print(f"\n{'='*50}")
    print(f"Starting analysis: {filename}")
    print(f"{'='*50}")

    initial_state = DocumentState(
        file_path = file_path,
        filename  = filename,
        raw_text  = "",
        summary   = "",
        key_info  = "",
        risks     = "",
        report    = "",
        status    = "starting",
        error     = ""
    )

    result = pipeline.invoke(initial_state)

    return {
        "filename": result["filename"],
        "summary":  result["summary"],
        "key_info": result["key_info"],
        "risks":    result["risks"],
        "report":   result["report"],
        "status":   result["status"],
        "error":    result.get("error", "")
    }


# ── Test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = analyze_document(sys.argv[1])
        print(f"\n{'='*50}")
        print("FINAL REPORT:")
        print(f"{'='*50}")
        print(result["report"])
        print(f"\nStatus: {result['status']}")
    else:
        print("Usage: python src/agents.py <path_to_pdf>")