import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents import analyze_document, answer_question
from src.database import init_db, log_analysis, get_all_analyses, get_stats

# ── Initialize DB on import ───────────────────────────────────────────
init_db()

def process_document(file_path: str, original_filename: str = None) -> dict:
    """Main entry point — runs the full multi-agent pipeline."""
    print(f"\n[Backend] Starting pipeline for: {file_path}")

    result = analyze_document(file_path)

    if original_filename:
        result["filename"] = original_filename

    log_analysis(
        filename   = result["filename"],
        status     = result["status"],
        summary    = result["summary"],
        key_info   = result["key_info"],
        risks      = result["risks"],
        report     = result["report"],
        risk_score = result.get("risk_score", 0),
        language   = result.get("language", "English"),
        error      = result.get("error", "")
    )

    return result


def ask_document(question: str, filename: str, language: str = "English") -> str:
    """Answer a question about an analyzed document."""
    return answer_question(question, filename, language)


def get_history() -> list:
    """Return all past analyses from SQLite."""
    rows = get_all_analyses()
    return [
        {
            "id":         row[0],
            "timestamp":  row[1],
            "filename":   row[2],
            "status":     row[3],
            "summary":    row[4],
            "key_info":   row[5],
            "risks":      row[6],
            "risk_score": row[7],
            "report":     row[8],
            "language":   row[9],
            "error":      row[10]
        }
        for row in rows
    ]


def get_dashboard_stats() -> dict:
    """Return stats for the analytics dashboard."""
    return get_stats()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = process_document(sys.argv[1])
        print(f"\nStatus:              {result['status']}")
        print(f"Language:            {result['language']}")
        print(f"Risk Score:          {result['risk_score']}/100")
        print(f"Suggested Questions: {result.get('suggested_questions', [])}")
        print(f"Summary:             {result['summary'][:200]}...")
    else:
        stats = get_dashboard_stats()
        print(f"\nDashboard Stats: {stats}")