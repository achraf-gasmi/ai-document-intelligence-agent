"""
api.py — FastAPI layer for DocIntel
Connects the React frontend to the LangGraph multi-agent backend.

Run with:
    uvicorn api:app --reload --port 8000

Endpoints:
    POST /analyze       — analyze a PDF
    POST /ask           — Q&A on an analyzed document
    POST /improve       — run the self-correcting improvement loop
    POST /resume        — resume an interrupted improvement run
    GET  /history       — list past analyses
    GET  /stats         — dashboard statistics
    DELETE /history     — clear all history
"""

import os
import json
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Internal modules ──────────────────────────────────────────────────────────
from src.agents import analyze_document, improve_document, resume_improvement
from src.backend import get_history, get_dashboard_stats, ask_document


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_: FastAPI):
    """Ensure required directories exist on startup."""
    os.makedirs("logs",          exist_ok=True)
    os.makedirs("data/chroma_db",exist_ok=True)
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DocIntel API",
    description="Multi-agent document intelligence — LangGraph + Groq",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — allow the Vite dev server and any local origin ─────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str
    filename: str
    language: str = "English"

class ResumeRequest(BaseModel):
    thread_id: str


# ── Helper ────────────────────────────────────────────────────────────────────

def save_upload(file: UploadFile) -> str:
    """
    Write an uploaded file to a temp path and return the path.
    Caller is responsible for cleanup (os.unlink) after use.
    """
    suffix = os.path.splitext(file.filename or "upload")[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
        return tmp.name


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "DocIntel API", "version": "1.0.0"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


# ── POST /analyze ─────────────────────────────────────────────────────────────
@app.post("/analyze", tags=["analysis"])
async def analyze(file: UploadFile = File(...)):
    """
    Accept a PDF upload, run the 6-agent analysis pipeline,
    and return the full result including risk score and report.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    tmp_path = save_upload(file)
    try:
        result = analyze_document(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")
    finally:
        # Clean up temp file — safe now because agents.py stores raw_text in state
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Analysis failed"))

    return JSONResponse(content=result)


# ── POST /ask ─────────────────────────────────────────────────────────────────
@app.post("/ask", tags=["qa"])
async def ask(req: AskRequest):
    """
    Answer a question about a previously analyzed document
    using ChromaDB semantic search (RAG).
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        answer = ask_document(req.question, req.filename, req.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {e}")

    return {"answer": answer}


# ── POST /improve ─────────────────────────────────────────────────────────────
@app.post("/improve", tags=["improvement"])
async def improve(
    file: UploadFile = File(None),
    existing_analysis: str = Form(None),
):
    """
    Run the self-correcting improvement loop on a document.

    Either supply:
    - `file`              — a fresh PDF to analyze then improve, OR
    - `existing_analysis` — JSON string of a previous /analyze result (skips re-analysis)

    Both can be supplied; existing_analysis takes priority to skip re-analysis.
    """
    # Parse existing analysis if provided
    parsed_analysis = None
    if existing_analysis:
        try:
            parsed_analysis = json.loads(existing_analysis)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="existing_analysis must be valid JSON.")

    # Determine file path
    tmp_path = None
    if file and file.filename:
        tmp_path = save_upload(file)
    elif not parsed_analysis:
        raise HTTPException(
            status_code=400,
            detail="Provide either a file or existing_analysis."
        )

    # If no file but we have analysis, use the filename from analysis as a placeholder
    if not tmp_path and parsed_analysis:
        # Create a minimal temp file so improve_document has a path to work with
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name

    try:
        result = improve_document(
            file_path=tmp_path,
            existing_analysis=parsed_analysis,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Improvement failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if result.get("improvement_status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Improvement failed"))

    return JSONResponse(content=result)


# ── POST /resume ──────────────────────────────────────────────────────────────
@app.post("/resume", tags=["improvement"])
async def resume(req: ResumeRequest):
    """
    Resume an interrupted improvement run from its last checkpoint.
    Requires the thread_id returned by a previous /improve call.
    """
    if not req.thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required.")

    try:
        result = resume_improvement(req.thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {e}")

    return JSONResponse(content=result)


# ── GET /history ──────────────────────────────────────────────────────────────
@app.get("/history", tags=["data"])
def history():
    """Return all past analyses from SQLite interactions.db."""
    try:
        rows = get_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load history: {e}")
    return JSONResponse(content=rows)


# ── GET /stats ────────────────────────────────────────────────────────────────
@app.get("/stats", tags=["data"])
def stats():
    """Return dashboard statistics."""
    try:
        data = get_dashboard_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load stats: {e}")
    return JSONResponse(content=data)


# ── DELETE /history ───────────────────────────────────────────────────────────
@app.delete("/history", tags=["data"])
def clear_history():
    """Clear all analysis history from SQLite."""
    try:
        import sqlite3
        db_path = os.path.join("logs", "interactions.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM interactions")
            conn.commit()
            conn.close()
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {e}")


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 10000))

    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )