# 📄 AI Document Intelligence Agent

> **Multi-agent document analysis & self-correcting improvement system**  
> powered by LangGraph · LangChain · Groq · React/Vite · FastAPI

Analyzes contracts, CVs, certificates and reports — then rewrites them through an agentic self-correction loop until they pass quality review.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-green?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-orange?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18-blue?style=flat-square&logo=react)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-purple?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 🎯 What It Does

Upload any PDF and get a full AI-powered analysis in seconds. Optionally run it through a self-correcting improvement loop that critiques, rewrites, and verifies the document across up to 3 iterations — until it reaches professional quality.

### Analysis Pipeline
- 📝 **Concise summary** of the document's purpose and content
- 🔍 **Key information extraction** — parties, dates, amounts, clauses, obligations
- ⚠️ **Risk analysis** — categorized Critical / High / Medium / Low
- 🎯 **Smart risk score** (0–100) — context-aware, understands document type
- 💬 **RAG-based Q&A** — ask specific questions, answered from the actual document
- 🌐 **Multi-language support** — auto-detects and responds in the document's language
- ⬇️ **Export** — download reports as TXT or PDF

### Improvement Loop
- 🧐 **Critique Agent** — identifies problems by section with severity ratings (Critical / Major / Minor)
- ✍️ **Improvement Agent** — rewrites all Critical and Major issues, marks changes with `[IMPROVED]`
- ✅ **Adversarial Verifier** — independent LLM at `temperature=0` scores quality 0–100
- 🔄 **Agentic loop** — cycles up to 3 iterations until score ≥ 85, with progressive scoring
- 🔖 **Checkpointing** — every iteration is persisted to SQLite; crashed runs can be resumed
- 📊 **Side-by-side diff** — original vs improved with full track-changes view per round

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
│ Summarizer │ Extractor  │ Risk Flagger│  ← ~60% faster than sequential
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
║   (max 3 iterations · checkpointed)     ║
║                                         ║
║  ┌──────────────────────────────────┐   ║
║  │  Critique Agent                  │   ║
║  │  Finds NEW issues only each round│   ║
║  │  Round 1 → Critical              │   ║
║  │  Round 2 → Major                 │   ║
║  │  Round 3 → Minor                 │   ║
║  └────────────────┬─────────────────┘   ║
║                   ↓                     ║
║  ┌──────────────────────────────────┐   ║
║  │  Improvement Agent               │   ║
║  │  Rewrites all Critical & Major   │   ║
║  │  Builds on previous rounds       │   ║
║  │  Marks changes with [IMPROVED]   │   ║
║  └────────────────┬─────────────────┘   ║
║                   ↓                     ║
║  ┌──────────────────────────────────┐   ║
║  │  Verifier Agent                  │   ║
║  │  Adversarial · temperature=0     │   ║
║  │  Scores relative to prev round   │   ║
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
    ┌──────────────────────────────┐
    📝 Side-by-side diff  🔀 Track changes
    🔖 Resume checkpoint  ⬇️ PDF export
```

**Typical score progression:**
```
Round 1: ~52/100  ← Critical issues addressed
Round 2: ~71/100  ← Major issues addressed
Round 3: ~86/100  ← Minor issues polished → loop exits ✅
```

### Key Design Decisions

- **Async parallel agents** — Agents 2, 3, 4 run with `asyncio.gather()` (true async I/O), falling back to `ThreadPoolExecutor` if an event loop is already running. ~60% faster than sequential.
- **Adversarial verifier** — separate `ChatGroq` instance at `temperature=0` with an explicit system prompt instructing it to be harsh and conservative. Scores relative to the previous round to guarantee progressive improvement.
- **Iterative context** — critique agent receives history of already-fixed issues and never re-flags them. Improvement agent receives a progress summary and is instructed not to regress previous fixes.
- **LangGraph checkpointing** — every node completion is persisted to `logs/checkpoints.db` via `SqliteSaver`. Each run gets a UUID `thread_id`. Crashed runs resume from the exact node they left off.
- **Smart chunking** — improvement agents receive the intro chunk + chunks with highest keyword overlap with the current critique, rather than a blind `[:4000]` slice.
- **Smart reuse** — if a document was already analyzed, the Improve tab skips re-analysis and goes straight to the loop.
- **Context-aware risk scoring** — a certificate will never be penalized for missing dispute resolution clauses.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Multi-agent orchestration | LangGraph 1.0+ |
| Checkpointing | LangGraph `SqliteSaver` (`langgraph-checkpoint-sqlite`) |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Vector store | ChromaDB |
| PDF extraction | PyMuPDF + pdfplumber |
| REST API | FastAPI 0.115 + Uvicorn |
| Frontend | React 18 + Vite + TypeScript |
| State management | Zustand |
| Routing | React Router v6 |
| Styling | Tailwind CSS v4 |
| Legacy UI | Streamlit (6 tabs, dark theme) |
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
pip install langgraph-checkpoint-sqlite   # install separately
```

> **Note:** `torch` is included for local embeddings. For memory-constrained environments (e.g. Streamlit Cloud), use the CPU-only build:
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

### 5a. Run — Streamlit UI (legacy)

```bash
streamlit run app.py
```

### 5b. Run — React frontend + FastAPI backend

```bash
# Terminal 1 — backend
uvicorn api:app --reload --port 8000

# Terminal 2 — frontend
cd docintel
npm install
npm run dev
# → http://localhost:5173
```

> The React frontend ships with `MOCK_MODE = true` — it works fully offline with realistic mock data.  
> To connect to the real backend, open `docintel/src/api/client.ts` and set `MOCK_MODE = false`.

---

## 📁 Project Structure

```
ai-document-intelligence-agent/
│
├── api.py                        # FastAPI layer (connects React frontend to backend)
├── app.py                        # Streamlit UI — 6 tabs (legacy)
├── requirements.txt
├── .env
│
├── src/
│   ├── agents.py                 # LangGraph pipelines (analysis + improvement loop)
│   ├── tools.py                  # LangChain tools (PDF extraction, ChromaDB, LLM)
│   ├── backend.py                # Business logic layer (used by both app.py and api.py)
│   └── database.py               # SQLite logging and analytics
│
├── docintel/                     # React/Vite frontend
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   └── src/
│       ├── App.tsx               # Router + layout
│       ├── main.tsx
│       ├── index.css             # Design tokens + global styles
│       ├── api/
│       │   └── client.ts         # All API calls + mock data (MOCK_MODE toggle)
│       ├── store/
│       │   └── useStore.ts       # Zustand global state
│       ├── components/
│       │   ├── Sidebar.tsx       # Navigation
│       │   ├── Toast.tsx         # Notifications
│       │   └── ui/
│       │       └── index.tsx     # Shared primitives (Badge, Card, Button, etc.)
│       └── panels/
│           ├── Analyze.tsx       # Upload + pipeline stepper + results
│           ├── QA.tsx            # Chat interface (RAG)
│           ├── Improve.tsx       # Loop diagram + diff viewer + iteration history
│           ├── Pipeline.tsx      # Architecture diagrams + tech stack
│           ├── History.tsx       # Searchable analysis history table
│           └── Dashboard.tsx     # Metrics + risk distribution + recent files
│
├── data/
│   └── chroma_db/                # Persistent vector store
│
└── logs/
    ├── interactions.db           # SQLite analysis history
    └── checkpoints.db            # LangGraph improvement loop checkpoints
```

---

## 🌐 REST API

The FastAPI layer runs at `http://localhost:8000`. Interactive docs available at `/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Upload a PDF — runs the 6-agent analysis pipeline |
| `POST` | `/ask` | Q&A on an analyzed document (RAG) |
| `POST` | `/improve` | Run the self-correcting improvement loop |
| `POST` | `/resume` | Resume an interrupted improvement run by `thread_id` |
| `GET` | `/history` | List all past analyses from SQLite |
| `GET` | `/stats` | Dashboard statistics (totals, avg risk, recent files) |
| `DELETE` | `/history` | Clear all analysis history |

### Example: analyze a document

```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@contract.pdf"
```

### Example: ask a question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the termination clause?", "filename": "contract.pdf", "language": "English"}'
```

### Example: resume an improvement run

```bash
curl -X POST http://localhost:8000/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "your-thread-id-here"}'
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
| 61–84 | 🟡 Acceptable | Minor issues, could be improved further |
| 85–100 | 🟢 Excellent | Publication-ready, no meaningful issues |

The verifier is **adversarial by design** — it uses a separate LLM instance with `temperature=0`, scores relative to the previous round, and is instructed never to reward cosmetic changes.

---

## 💬 Q&A Mode

After analysis, switch to the **Q&A panel** to ask any question about the document:

- Answered using **ChromaDB semantic search** — retrieves the most relevant sections
- **Suggested questions** are generated dynamically from the actual document content
- Answers are returned in the **document's detected language**
- Full **conversation history** is preserved within the session

---

## 🌐 Multi-Language Support

The system auto-detects document language and responds in kind across all agents: summary, key info extraction, risk analysis, Q&A, and report generation.

Tested with: English, French, Arabic

---

## 📋 Features Overview

| Feature | Description |
|---------|-------------|
| 📤 PDF Upload | Drag & drop or click to browse |
| ⚡ Async Parallel Agents | 3 agents via `asyncio.gather` — ~60% faster |
| 🎯 Smart Risk Score | Context-aware, LLM-powered 0–100 |
| 🔧 Improvement Loop | Self-correcting agentic cycle, up to 3 rounds |
| ✅ Adversarial Verifier | Independent LLM at `temperature=0`, progressive scoring |
| 🔖 Checkpointing | `SqliteSaver` — resume interrupted improvement runs |
| 📝 Side-by-side Diff | Original vs improved with full track-changes view |
| 💬 Document Q&A | RAG-based semantic search over document |
| 💡 Smart Suggestions | Document-specific question suggestions |
| 🌐 Multi-language | Auto-detect + respond in document language |
| 🌐 REST API | FastAPI layer — 7 endpoints, Swagger UI at `/docs` |
| ⚛️ React Frontend | Vite + TypeScript + Zustand + React Router v6 |
| 📋 History | All past analyses stored in SQLite |
| 📊 Dashboard | Stats, avg risk score, risk distribution chart |
| ⬇️ Export | TXT and PDF download — analysis report + improved document |
| 🕸️ Pipeline View | Visual agent architecture + animated cycle diagram |

---

## 🧪 Test via CLI

```bash
# Analyze a document directly from the terminal
python src/agents.py path/to/your_document.pdf

# Test the full backend pipeline
python src/backend.py path/to/your_document.pdf
```


---

## 👨‍💻 Author

**Achraf Gasmi** — AI Engineer & Consultant  
Specialized in RAG pipelines, LLM applications, and multi-agent systems

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/achraf-gasmi-592766134/)
[![GitHub](https://img.shields.io/badge/GitHub-Portfolio-black?style=flat-square&logo=github)](https://github.com/achraf-gasmi)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
