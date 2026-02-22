import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents import analyze_document
from src.database import init_db, log_analysis, get_all_analyses, get_stats

# ── Initialize DB on import ───────────────────────────────────────────
init_db()

def process_document(file_path: str, original_filename: str = None) -> dict:
    """
    Main entry point — runs the full multi-agent pipeline
    and logs the result to SQLite.
    """
    print(f"\n[Backend] Starting pipeline for: {file_path}")

    result = analyze_document(file_path)

    # Use original filename if provided
    if original_filename:
        result["filename"] = original_filename

    # Log to SQLite
    log_analysis(
        filename = result["filename"],
        status   = result["status"],
        summary  = result["summary"],
        key_info = result["key_info"],
        risks    = result["risks"],
        report   = result["report"],
        error    = result.get("error", "")
    )

    return result


def get_history() -> list:
    """Return all past analyses from SQLite."""
    rows = get_all_analyses()
    return [
        {
            "id":        row[0],
            "timestamp": row[1],
            "filename":  row[2],
            "status":    row[3],
            "summary":   row[4],
            "key_info":  row[5],
            "risks":     row[6],
            "report":    row[7],
            "error":     row[8]
        }
        for row in rows
    ]


def get_dashboard_stats() -> dict:
    """Return stats for the analytics dashboard."""
    return get_stats()


# ── Test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = process_document(sys.argv[1])
        print(f"\nStatus:  {result['status']}")
        print(f"Summary: {result['summary'][:200]}...")
    else:
        print("Usage: python src/backend.py <path_to_pdf>")
        stats = get_dashboard_stats()
        print(f"\nDashboard Stats: {stats}")