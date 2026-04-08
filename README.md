# RAG Document Assistant

Chat with your PDFs using Retrieval-Augmented Generation (RAG).

## Tech Stack
- **Backend**: Python, FastAPI, LangChain, ChromaDB, OpenAI
- **Frontend**: React (Vite), plain CSS
- **Evaluation**: RAGAS

## Project Structure
```
rag-document-assistant/
├── backend/
│   ├── main.py          # FastAPI routes
│   ├── ingest.py        # PDF → chunks → embeddings → ChromaDB
│   ├── rag.py           # query → vector search → LLM → answer
│   ├── evaluate.py      # RAGAS faithfulness + relevancy scoring
│   ├── requirements.txt
│   └── .env             # OPENAI_API_KEY (never commit this)
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── ChatWindow.jsx
    │   ├── FileUpload.jsx
    │   ├── SourceCard.jsx
    │   ├── EvaluationPanel.jsx
    │   └── App.css
    ├── package.json
    └── vite.config.js
```

## Setup & Run

### 1. Get an OpenAI API Key
Sign up at platform.openai.com, create an API key.

### 2. Backend setup
```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Add your API key to .env
echo "OPENAI_API_KEY=your-key-here" > .env

# Start the server
python main.py
# Server runs at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev
# App runs at http://localhost:3000
```

### 4. Use it
1. Open http://localhost:3000
2. Upload a PDF in the left panel
3. Wait for ingestion to complete (~5-30 seconds depending on PDF size)
4. Type questions in the chat
5. Click "Evaluate" tab to run RAGAS scoring

## How It Works

### Ingestion Pipeline (runs once per PDF)
PDF file → pdfplumber extracts text → RecursiveCharacterTextSplitter
splits into 500-char chunks with 50-char overlap → OpenAI text-embedding-3-small
converts each chunk to a 1536-dim vector → ChromaDB stores vectors + text on disk

### Query Pipeline (runs on every question)
User question → embed with same model → cosine similarity search in ChromaDB
→ retrieve top-4 chunks → build prompt (system + context + question) → GPT-4o-mini
→ answer + source references returned to frontend

### Evaluation
RAGAS uses GPT-4 as a judge to score:
- **Faithfulness**: are all answer claims supported by the retrieved context?
- **Answer Relevancy**: does the answer actually address the question?

## Key Design Decisions
- **ChromaDB over FAISS**: persists to disk, no need to re-embed on restart
- **gpt-4o-mini**: cheaper than GPT-4 for the generation step, adequate quality
- **temperature=0**: deterministic answers for a document Q&A use case
- **chunk_size=500, overlap=50**: good default; tune based on your document type
- **top_k=4**: balance between enough context and avoiding irrelevant noise
