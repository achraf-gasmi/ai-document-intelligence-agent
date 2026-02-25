import os
import fitz  # PyMuPDF
import pdfplumber
from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_core.documents import Document
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings

import warnings
import logging
warnings.filterwarnings("ignore")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"}
)

load_dotenv()

# ── LLM & Embeddings ─────────────────────────────────────────────────
llm = ChatGroq(
    model=os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile"),
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3
)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ── ChromaDB ──────────────────────────────────────────────────────────
vectorstore = Chroma(
    persist_directory="data/chroma_db",
    embedding_function=embeddings,
    collection_name="documents"
)

# ── Tool 1: Extract text from PDF ────────────────────────────────────
@tool
def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text content from a PDF file."""
    try:
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        if not text.strip():
            # fallback to pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        print(f"[Tool] Extracted {len(text)} characters from {file_path}")
        return text.strip()
    except Exception as e:
        return f"Error extracting text: {e}"


# ── Tool 2: Store document in ChromaDB ───────────────────────────────
@tool
def store_document(file_path: str, content: str) -> str:
    """Store document content in ChromaDB for semantic search."""
    try:
        filename = os.path.basename(file_path)

        # Check if document already exists
        existing = vectorstore.get(where={"source": filename})
        if existing and len(existing["ids"]) > 0:
            print(f"[Tool] Document {filename} already in ChromaDB, skipping.")
            return f"Document {filename} already stored — skipping."

        chunk_size = 1000
        overlap    = 200
        chunks     = []

        for i in range(0, len(content), chunk_size - overlap):
            chunk = content[i:i + chunk_size]
            if chunk.strip():
                chunks.append(Document(
                    page_content=chunk,
                    metadata={
                        "source":   filename,
                        "chunk_id": len(chunks)
                    }
                ))

        vectorstore.add_documents(chunks)
        print(f"[Tool] Stored {len(chunks)} chunks from {filename}")
        return f"Stored {len(chunks)} chunks from {filename} in ChromaDB."
    except Exception as e:
        return f"Error storing document: {e}"


# ── Tool 3: Search document ───────────────────────────────────────────
@tool
def search_document(query: str, filename: str = "") -> str:
    """Search for relevant sections in stored documents."""
    try:
        results = vectorstore.similarity_search(
            query,
            k=5,
            filter={"source": filename} if filename else None
        )
        if not results:
            return "No relevant sections found."

        combined = "\n\n---\n\n".join([r.page_content for r in results])
        print(f"[Tool] Found {len(results)} relevant sections for: {query}")
        return combined
    except Exception as e:
        return f"Error searching document: {e}"

# ── Tool 4: Summarize text ────────────────────────────────────────────
@tool
def summarize_text(text: str, language: str = "English") -> str:
    """Generate a concise summary of the provided text."""
    try:
        lang_note = f"\nIMPORTANT: Respond entirely in {language}." if language != "English" else ""
        prompt = f"""Summarize the following document concisely in 3-5 sentences.
Focus on the main purpose, key parties involved, and core terms.{lang_note}

Document:
{text[:4000]}

Summary:"""
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"Error summarizing: {e}"


# ── Tool 5: Extract key information ──────────────────────────────────
@tool
def extract_key_info(text: str, language: str = "English") -> str:
    """Extract key information like dates, parties, amounts, and clauses."""
    try:
        lang_note = f"\nIMPORTANT: Respond entirely in {language}." if language != "English" else ""
        prompt = f"""Extract the following key information from this document.
Return as a structured list:

- Document Type:
- Parties Involved:
- Key Dates:
- Financial Amounts:
- Key Clauses/Terms:
- Obligations:
- Duration/Validity:
{lang_note}

Document:
{text[:4000]}

Extracted Information:"""
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"Error extracting info: {e}"


# ── Tool 6: Flag risks ────────────────────────────────────────────────
@tool
def flag_risks(text: str, language: str = "English") -> str:
    """Identify potential risks, red flags, and missing sections."""
    try:
        lang_note = f"\nIMPORTANT: Respond entirely in {language}." if language != "English" else ""
        prompt = f"""Analyze this document for potential risks and issues.
Identify and list:

🔴 HIGH RISK — Critical issues that need immediate attention
🟡 MEDIUM RISK — Issues that should be reviewed carefully
🟢 LOW RISK — Minor concerns or suggestions
⚠️ MISSING — Important sections or clauses that are absent
{lang_note}

Document:
{text[:4000]}

Risk Analysis:"""
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"Error flagging risks: {e}"

# ── Tool 7: Generate report ───────────────────────────────────────────
@tool
def generate_report(summary: str, key_info: str, risks: str, filename: str) -> str:
    """Combine analysis results into a final structured report."""
    try:
        prompt = f"""Create a professional document analysis report based on the following:

SUMMARY:
{summary}

KEY INFORMATION:
{key_info}

RISK ANALYSIS:
{risks}

Format as a clean, professional report with clear sections.
Document: {filename}

Report:"""
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"Error generating report: {e}"


# ── Export all tools ──────────────────────────────────────────────────
all_tools = [
    extract_text_from_pdf,
    store_document,
    search_document,
    summarize_text,
    extract_key_info,
    flag_risks,
    generate_report
]