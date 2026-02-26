# 📄 AI Document Intelligence Agent

> **Multi-agent document analysis system** powered by LangGraph, LangChain & Groq  
> Analyzes contracts, invoices, CVs, certificates and reports with 6 specialized AI agents

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-orange?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-purple?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 🎯 What It Does

Upload any PDF document and get an instant, comprehensive AI-powered analysis:

- 📝 **Concise summary** of the document's purpose and content
- 🔍 **Key information extraction** — parties, dates, amounts, clauses, obligations
- ⚠️ **Risk analysis** — categorized HIGH / MEDIUM / LOW / MISSING
- 🎯 **Smart risk score** (0–100) that understands document context
- 💬 **Q&A mode** — ask specific questions about your document
- 🌐 **Multi-language support** — auto-detects and responds in document language
- ⬇️ **Export** — download reports as TXT or PDF

---

## 🏗️ Architecture

```
User uploads PDF
       ↓
┌─────────────────────────┐
│  Agent 1                │
│  Document Processor     │  ← Extracts text, detects language, stores in ChromaDB
└────────────┬────────────┘
             ↓
    ⚡ PARALLEL EXECUTION
┌────────────┬────────────┬────────────┐
│  Agent 2   │  Agent 3   │  Agent 4   │
│ Summarizer │ Extractor  │ Risk Flagger│
└────────────┴─────┬──────┴────────────┘
                   ↓
┌─────────────────────────┐
│  Risk Score Calculator  │  ← LLM-powered, context-aware scoring
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  Agent 5                │
│  Report Generator       │  ← Combines all analyses into final report
└────────────┬────────────┘
             ↓
┌─────────────────────────┐
│  Agent 6                │
│  Questions Generator    │  ← Generates document-specific Q&A suggestions
└─────────────────────────┘
             ↓
    ┌────────┴────────┐
    💬 Q&A Mode    ⬇️ Export
  (ChromaDB RAG)  (TXT / PDF)
```

### Key Design Decisions

- **Parallel execution** — Agents 2, 3, 4 run simultaneously with `ThreadPoolExecutor`, cutting analysis time by ~60%
- **Smart risk scoring** — LLM understands document type: a certificate scores 5/100 (low risk), a contract with missing clauses scores 65/100 (high risk)
- **Persistent ChromaDB** — documents stored once, no re-indexing on re-upload
- **Language-aware** — all agents respond in the detected document language

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Multi-agent orchestration | LangGraph |
| LLM | Groq API — `llama-3.3-70b-versatile` |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Vector store | ChromaDB |
| PDF extraction | PyMuPDF + pdfplumber |
| UI | Streamlit |
| Logging | SQLite |
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
├── app.py                  # Streamlit UI (5 tabs)
├── src/
│   ├── agents.py           # LangGraph multi-agent pipeline
│   ├── tools.py            # LangChain tools (PDF, ChromaDB, LLM)
│   ├── backend.py          # API layer between UI and pipeline
│   └── database.py         # SQLite logging and analytics
├── sample_documents/       # Test documents
├── data/
│   └── chroma_db/          # Persistent vector store
├── logs/
│   └── interactions.db     # SQLite analysis history
├── requirements.txt
└── .env
```

---

## 🧪 Test via CLI

```bash
# Analyze a document directly
python src/agents.py sample_documents/your_document.pdf

# Test the full backend pipeline
python src/backend.py sample_documents/your_document.pdf
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

The scorer is **context-aware** — it considers document type before scoring. A certificate will never be penalized for missing "dispute resolution clauses."

---

## 💬 Q&A Mode

After analysis, switch to the **Q&A tab** to ask any question about the document:

- Questions are answered using **ChromaDB semantic search** — the system finds the most relevant sections
- Suggested questions are **generated dynamically** based on the actual document content
- Answers are returned in the **document's language**

---

## 🌐 Multi-Language Support

The system automatically detects document language and:
- Generates summaries in the detected language
- Extracts key information in the detected language
- Performs risk analysis in the detected language
- Answers Q&A questions in the detected language

Tested with: English, French, Arabic

---

## 📋 Features Overview

| Feature | Description |
|---------|-------------|
| 📤 PDF Upload | Drag & drop, up to 200MB |
| ⚡ Parallel Agents | 3 agents run simultaneously |
| 🎯 Smart Risk Score | Context-aware, LLM-powered |
| 💬 Document Q&A | RAG-based question answering |
| 💡 Smart Suggestions | Document-specific question suggestions |
| 🌐 Multi-language | Auto-detect + respond in document language |
| 📋 History | All past analyses stored in SQLite |
| 📊 Dashboard | Stats, avg risk score, recent files |
| ⬇️ Export | TXT and PDF download |
| 🕸️ Pipeline View | Visual agent architecture diagram |

---

## 🔧 Requirements

```
python >= 3.10
langchain
langchain-groq
langchain-community
langchain-chroma
langgraph
groq
streamlit
pymupdf
pdfplumber
chromadb
sentence-transformers
fpdf2
python-dotenv
```

---

## 🗺️ Roadmap

- [ ] Batch document processing
- [ ] Document comparison (upload 2 contracts, compare them)
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