import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = "logs/interactions.db"

def init_db():
    """Initialize the SQLite database."""
    os.makedirs("logs", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            filename    TEXT NOT NULL,
            status      TEXT NOT NULL,
            summary     TEXT,
            key_info    TEXT,
            risks       TEXT,
            risk_score  INTEGER DEFAULT 0,
            report      TEXT,
            language    TEXT DEFAULT 'English',
            error       TEXT,
            char_count  INTEGER
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized.")


def log_analysis(filename, status, summary, key_info, risks, report,
                 risk_score=0, language="English", error=""):
    """Log a document analysis to SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO analyses
        (timestamp, filename, status, summary, key_info, risks,
         risk_score, report, language, error, char_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        filename,
        status,
        summary,
        key_info,
        risks,
        risk_score,
        report,
        language,
        error,
        len(report) if report else 0
    ))

    conn.commit()
    conn.close()
    print(f"[DB] Logged analysis for {filename}")


def get_all_analyses():
    """Retrieve all analyses from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM analyses ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_analysis_by_filename(filename):
    """Retrieve the latest analysis for a specific file."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM analyses
        WHERE filename = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (filename,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_stats():
    """Get summary statistics for the dashboard."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM analyses")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analyses WHERE status = 'complete'")
    successful = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM analyses WHERE status = 'failed'")
    failed = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(risk_score) FROM analyses WHERE status = 'complete'")
    avg_risk = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT filename, risk_score, language, timestamp
        FROM analyses
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    recent = [
        {
            "filename":   row[0],
            "risk_score": row[1],
            "language":   row[2],
            "timestamp":  row[3]
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return {
        "total":      total,
        "successful": successful,
        "failed":     failed,
        "avg_risk":   round(avg_risk, 1),
        "recent":     recent
    }