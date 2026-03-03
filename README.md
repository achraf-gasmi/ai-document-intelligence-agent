# 📄 AI Document Intelligence Agent

> **Multi-agent document analysis & self-correcting improvement system** powered by LangGraph, LangChain & Groq  
> Analyzes contracts, CVs, certificates and reports — then rewrites them until they pass quality review

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-green?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-orange?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-purple?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 🎯 What It Does

Upload any PDF and get a full AI-powered analysis — then optionally run it through a self-correcting improvement loop that rewrites the document until it reaches professional quality.

### Analysis Pipeline
- 📝 **Concise summary** of the document's purpose and content
- 🔍 **Key information extraction** — parties, dates, amounts, clauses, obligations
- ⚠️ **Risk analysis** — categorized HIGH / MEDIUM / LOW / MISSING
- 🎯 **Smart risk score** (0–100) that understands document type and context
- 💬 **RAG-based Q&A** — ask specific questions, answered from the document
- 🌐 **Multi-language support** — auto-detects and responds in document language
- ⬇️ **Export** — download reports as TXT or PDF

### Improvement Loop *(new)*
- 🧐 **Critique Agent** — identifies exact problems by section, with severity ratings
- ✍️ **Improvement Agent** — rewrites and fixes all Critical and Major issues
- ✅ **Adversarial Verifier** — independent LLM at temperature=0 scores quality 0–100
- 🔄 **Agentic loop** — cycles up to 3 iterations until score ≥ 85
- 🔖 **Checkpointing** — every iteration is persisted; crashed runs can be resumed
- 📊 **Side-by-side diff** — original vs improved with tracked changes per round

---

## 🏗️ Architecture

### Analysis Pipeline

```
User uploads PDF
       ↓
┌─────────────────────────┐
│  Agent 1                │
│  Document Processor     │  ← Extracts text, detects language, stores in ChromaDB
└────────────┬────────────┘
             ↓
    ⚡ ASYNC PARALLEL (asyncio.gather)
┌────────────┬────────────┬────────────┐
│  Agent 2   │  Agent 3   │  Agent 4   │
│ Summarizer │ Extractor  │ Risk Flagger│
└────────────┴─────┬──────┴────────────┘
                   ↓
┌─────────────────────────┐
│  Risk Score Calculator  │  ← LLM-powered, context-aware (0–100)
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  Agent 5                │
│  Report Generator       │
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  Agent 6                │
│  Questions Generator    │  ← Document-specific Q&A suggestions
└─────────────────────────┘
             ↓
    ┌────────┴────────┐
    💬 Q&A Mode    ⬇️ Export
  (ChromaDB RAG)  (TXT / PDF)
```

### Improvement Loop — Agentic Cycle

```
Document (from session or fresh upload)
       ↓
┌─────────────────────────┐
│  Doc Type Detector      │  ← Resume/CV · Legal Contract · Report · Certificate
└────────────┬────────────┘
             ↓
╔═════════════════════════════════════════╗
║   AGENTIC SELF-CORRECTION LOOP          ║
║   (max 3 iterations)                    ║
║                                         ║
║  ┌──────────────────────────────────┐   ║
║  │  Critique Agent                  │   ║
║  │  Section · Problem · Severity    │   ║
║  │  Fix instruction                 │   ║
║  └────────────────┬─────────────────┘   ║
║                   ↓                     ║
║  ┌──────────────────────────────────┐   ║
║  │  Improvement Agent               │   ║
║  │  Rewrites all Critical & Major   │   ║
║  │  issues, marks [IMPROVED]        │   ║
║  └────────────────┬─────────────────┘   ║
║                   ↓                     ║
║  ┌──────────────────────────────────┐   ║
║  │  Verifier Agent                  │   ║
║  │  Adversarial · temperature=0     │   ║
║  │  Independent LLM instance        │   ║
║  └────────────────┬─────────────────┘   ║
║                   ↓                     ║
║         Score ≥ 85 or iter = 3?         ║
║         NO  ──────────────────↑ loop    ║
║         YES ↓                           ║
╚═════════════════════════════════════════╝
             ↓
┌─────────────────────────┐
│  Finalizer              │  ← Picks best-scoring iteration from history
└────────────┬────────────┘
             ↓
    ┌─────────────────────────────┐
    📝 Side-by-side   🔀 Track changes
    🔖 Checkpoint     ⬇️ PDF export
```

### Key Design Decisions

- **Async parallel agents** — Agents 2, 3, 4 run with `asyncio.gather()` (true async I/O), falling back to `ThreadPoolExecutor` if an event loop is already running. ~60% faster than sequential.
- **Adversarial verifier** — the verifier uses a separate `ChatGroq` instance at `temperature=0` with an explicit system prompt instructing it to be harsh and not give credit for cosmetic changes. Grades independently from the improvement agent.
- **LangGraph checkpointing** — every node completion is persisted to `logs/checkpoints.db` via `SqliteSaver`. Each run gets a `thread_id`. Crashed runs can be resumed from the exact node they left off.
- **Smart chunking** — for long documents, improvement agents receive the intro chunk + the chunks with highest keyword overlap with the critique, rather than a blind `[:4000]` slice.
- **Smart reuse** — if a document was already analyzed in the Analyze tab, the Improve tab skips re-analysis and goes straight to the improvement loop.
- **Context-aware risk scoring** — a certificate will never be penalized for missing "dispute resolution clauses."

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Multi-agent orchestration | LangGraph 1.0+ |
| Checkpointing | LangGraph `SqliteSaver` |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Vector store | ChromaDB |
| PDF extraction | PyMuPDF + pdfplumber |
| UI | Streamlit (6 tabs, dark theme) |
| Logging | SQLite (`interactions.db`) |
| PDF export | fpdf2 |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/achraf-gasmi/ai-document-intelligence-agent.git
cd ai-document-intelligence-agent
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `torch` is included for local embeddings. If deploying to a memory-constrained environment (e.g. Streamlit Cloud), use the CPU-only build:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> ```

### 4. Set up environment variables

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here
CHAT_MODEL=llama-3.3-70b-versatile
```

Get your free Groq API key at [console.groq.com](https://console.groq.com)

### 5. Run the app

```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
ai-document-intelligence-agent/
├── app.py                  # Streamlit UI (6 tabs)
├── src/
│   ├── agents.py           # LangGraph pipelines (analysis + improvement loop)
│   ├── tools.py            # LangChain tools (PDF, ChromaDB, LLM)
│   ├── backend.py          # API layer between UI and pipeline
│   └── database.py         # SQLite logging and analytics
├── data/
│   └── chroma_db/          # Persistent vector store
├── logs/
│   ├── interactions.db     # SQLite analysis history
│   └── checkpoints.db      # LangGraph improvement loop checkpoints
├── requirements.txt
└── .env
```

---

## 🧪 Test via CLI

```bash
# Analyze a document directly
python src/agents.py path/to/your_document.pdf

# Test the full backend pipeline
python src/backend.py path/to/your_document.pdf
```

---

## 📊 Risk Score System

The risk score (0–100) represents **danger level** — higher means more risk:

| Score | Level | Example |
|-------|-------|---------|
| 0–20 | 🟢 Low Risk | Certificate, award, informational doc |
| 21–50 | 🟡 Medium Risk | Complete contract with minor issues |
| 51–80 | 🔴 High Risk | Contract with missing critical clauses |
| 81–100 | ⛔ Critical Risk | Dangerously incomplete legal document |

## 🔧 Improvement Score System

The improvement score (0–100) represents **document quality** — higher means better:

| Score | Level | Meaning |
|-------|-------|---------|
| 0–30 | 🔴 Poor | Major sections missing, many critical issues |
| 31–60 | 🟡 Below average | Several significant problems remain |
| 61–84 | 🟡 Acceptable | Minor issues, could still be improved |
| 85–100 | 🟢 Excellent | Publication-ready, no meaningful issues |

The verifier is **adversarial by design** — it uses a separate LLM instance with `temperature=0` and an explicit system prompt that instructs it to be harsh, not reward cosmetic changes, and score conservatively.

---

## 💬 Q&A Mode

After analysis, switch to the **Q&A tab** to ask any question about the document:

- Answered using **ChromaDB semantic search** — finds the most relevant sections
- Suggested questions are **generated dynamically** from the actual document content
- Answers are returned in the **document's language**

---

## 🌐 Multi-Language Support

The system auto-detects document language and responds in kind across all agents:
summary, key info extraction, risk analysis, Q&A, and report generation.

Tested with: English, French, Arabic

---

## 📋 Features Overview

| Feature | Description |
|---------|-------------|
| 📤 PDF Upload | Drag & drop upload |
| ⚡ Async Parallel Agents | 3 agents via `asyncio.gather` |
| 🎯 Smart Risk Score | Context-aware, LLM-powered |
| 🔧 Improvement Loop | Self-correcting agentic cycle |
| ✅ Adversarial Verifier | Independent LLM at temperature=0 |
| 🔖 Checkpointing | Resume interrupted improvement runs |
| 📝 Side-by-side Diff | Original vs improved with track changes |
| 💬 Document Q&A | RAG-based question answering |
| 💡 Smart Suggestions | Document-specific question suggestions |
| 🌐 Multi-language | Auto-detect + respond in document language |
| 📋 History | All past analyses stored in SQLite |
| 📊 Dashboard | Stats, avg risk score, recent files |
| ⬇️ Export | TXT and PDF download (analysis + improved doc) |
| 🕸️ Pipeline View | Visual agent architecture + cycle diagram |

---

## 🗺️ Roadmap

- [ ] Streamlit Cloud deployment
- [ ] Batch document processing
- [ ] Document comparison (upload 2 contracts, compare clause by clause)
- [ ] FastAPI endpoint for programmatic access
- [ ] Word cloud of most flagged risk terms
- [ ] Email alerts for high-risk documents

---

## 👨‍💻 Author

**Achraf Gasmi** — AI Engineer & Consultant  
Specialized in RAG pipelines, LLM applications, and multi-agent systems

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/achrafgasmi-592766134)
[![GitHub](https://img.shields.io/badge/GitHub-Portfolio-black?style=flat-square&logo=github)](https://github.com/achraf-gasmi)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.