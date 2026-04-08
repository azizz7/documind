<div align="center">

# DocuMind — RAG Document Assistant

**Chat with your documents using AI. Get instant answers with sources.**

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)
![LangChain](https://img.shields.io/badge/LangChain-0.2-purple?style=flat-square)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

</div>

---

## What is this?

DocuMind is a full-stack RAG (Retrieval-Augmented Generation) application that lets you upload PDF documents and ask questions about them in natural language. It retrieves the most relevant sections from your documents and uses an LLM to generate accurate, grounded answers — always showing you the source so you can verify.

Built from scratch with a production-grade architecture including streaming responses, conversation memory, multi-document support, scoped retrieval, AI-powered question suggestions, and a fully custom dark UI.

---

## Demo

| Feature | Description |
|---|---|
| Multi-PDF support | Upload multiple documents, switch between them or query all at once |
| Streaming answers | Responses stream token by token — no waiting |
| Source citations | Every answer shows exactly which chunk it came from |
| Conversation memory | Follow-up questions work naturally — it remembers context |
| Question suggestions | AI generates contextual questions based on your loaded documents |
| Scoped retrieval | Filter searches to a specific document or search across all |
| RAGAS evaluation | Automated faithfulness and answer relevancy scoring |

---

## Architecture

```
PDF Upload
    │
    ▼
Text Extraction (PyMuPDF)
    │
    ▼
Chunking (RecursiveCharacterTextSplitter — 1500 chars, 200 overlap)
    │
    ▼
Embeddings (HuggingFace all-MiniLM-L6-v2 — runs locally, no API cost)
    │
    ▼
Vector Storage (ChromaDB — persists to disk)
    │
    ▼
User Question → Embed → Cosine Similarity Search → Top-K Chunks
    │
    ▼
Prompt Builder (System + Context + Chat History + Question)
    │
    ▼
LLM (Groq — llama-3.1-8b-instant) → Streaming Response
    │
    ▼
Answer + Source Citations → React Frontend
```

---

## Tech Stack

**Backend**
- Python 3.11
- FastAPI — REST API with streaming support (SSE)
- LangChain — RAG orchestration and prompt management
- ChromaDB — vector database with metadata filtering
- HuggingFace Sentence Transformers — local embeddings (all-MiniLM-L6-v2)
- Groq API — LLM inference (llama-3.1-8b-instant)
- PyMuPDF — PDF text extraction with layout awareness
- RAGAS — automated RAG evaluation framework

**Frontend**
- React 18 with Vite
- Custom dark UI (no component library)
- Server-Sent Events for streaming
- Conversation history management

---

## Key Technical Decisions

**Why local embeddings?**
HuggingFace's all-MiniLM-L6-v2 runs entirely on your machine — no API calls, no cost, no latency for embedding. This also means your document contents never leave your server during the ingestion phase.

**Why ChromaDB over FAISS?**
ChromaDB persists to disk automatically and supports metadata filtering out of the box. This enables scoped retrieval — filtering vector search to a specific document using `filter={"source": filename}` without maintaining a separate index per document.

**Why streaming?**
LLM responses can take 5-10 seconds for long answers. Streaming via Server-Sent Events means the first tokens appear in ~500ms — dramatically improving perceived performance without changing actual latency.

**Why conversation memory?**
Without history, every question is isolated. "What did the authors conclude?" followed by "Who were they?" breaks without memory. We pass the last 5 turns as context, trimmed to control token cost.

**Chunk size tuning**
After testing, 1500 characters with 200 overlap performed significantly better than the standard 500/50 defaults for academic and legal documents. Larger chunks preserve more semantic context per retrieval.

---

## Getting Started

### Prerequisites
- Python 3.11
- Node.js 18+
- Groq API key (free at console.groq.com)

### Installation

```bash
# Clone the repo
git clone https://github.com/azizz7/documind.git
cd documind

# Backend setup
cd backend
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Add your API key
echo "GROQ_API_KEY=your_key_here" > .env

# Start backend
python main.py
```

```bash
# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| POST | /upload | Upload and ingest a PDF |
| POST | /chat | Standard RAG query |
| POST | /chat/stream | Streaming RAG query (SSE) |
| GET | /documents | List all ingested documents |
| DELETE | /documents/{name} | Remove a document |
| POST | /suggest-questions | Generate AI question suggestions |
| POST | /evaluate | Run RAGAS evaluation |
| GET | /health | Health check |

---

## Evaluation

The project includes automated evaluation using RAGAS:

- **Faithfulness** — measures if answers are grounded in retrieved context
- **Answer Relevancy** — measures if answers actually address the question

Run evaluation from the UI by clicking the Evaluate tab, or directly:

```bash
cd backend
python evaluate.py
```

---

## Project Structure

```
documind/
├── backend/
│   ├── main.py          # FastAPI routes
│   ├── ingest.py        # PDF → chunks → embeddings → ChromaDB
│   ├── rag.py           # Query pipeline with streaming + memory
│   ├── evaluate.py      # RAGAS evaluation
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── ChatWindow.jsx
    │   ├── FileUpload.jsx
    │   ├── DocumentList.jsx
    │   ├── QuestionSuggestions.jsx
    │   ├── EvaluationPanel.jsx
    │   └── App.css
    └── package.json
```

---

## Troubleshooting

**"Error: Load failed. Is the backend running?"**
Ensure the FastAPI server is running (`python main.py` in the `backend/` directory) and verify your `GROQ_API_KEY` inside `.env` is valid and active.

**"No documents have been uploaded yet"**
The vector database is empty. Upload a PDF using the left sidebar drop-zone to initialize the collection.

**Port 8000/3000 already in use**
Kill existing processes using `kill $(lsof -t -i:8000)` and `kill $(lsof -t -i:3000)` respectively.

---

## License

MIT — free to use, modify, and distribute.

---

<div align="center">
Built with LangChain · ChromaDB · Groq · React
</div>
