"""
main.py — FastAPI application with all routes.

Routes:
  POST /upload         — upload a PDF and run ingestion
  POST /chat           — standard (non-streaming) RAG query
  POST /chat/stream    — streaming RAG query (tokens arrive word by word)
  GET  /documents      — list all ingested documents
  DELETE /documents/{name} — remove a document from the vector DB
  POST /evaluate       — run RAGAS evaluation
  GET  /health         — server health check
"""

import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from ingest import ingest_pdf, list_ingested_documents, delete_document
from rag import query_rag, query_rag_stream
from evaluate import run_evaluation, interpret_scores

load_dotenv()

app = FastAPI(title="RAG Document Assistant API", version="1.0.0")

# CORS: required so the React app on localhost:3000 can call this API on localhost:8000.
# Browsers enforce the Same-Origin Policy — without this middleware every fetch
# from the frontend would be blocked with a CORS error.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production: replace with your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ── Pydantic request body models ──
# FastAPI uses these to auto-validate incoming JSON.
# Wrong shape → 422 Unprocessable Entity before your code runs.

class ChatRequest(BaseModel):
    question: str
    # chat_history carries previous turns for conversation memory.
    # Default empty list means single-turn mode (backward compatible).
    chat_history: list[dict] = []
    doc_filter: str | None = None

class EvaluateRequest(BaseModel):
    questions: list[str]


class SuggestRequest(BaseModel):
    doc_filter: str | None = None


# ────────────────────────────────────────
# ROUTE: Health check
# ────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ────────────────────────────────────────
# ROUTE: Upload PDF
# ────────────────────────────────────────
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accepts a PDF, saves it temporarily, runs ingestion, then deletes the temp file.
    Uses shutil.copyfileobj to stream the file to disk without loading it all into RAM —
    important for large documents.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    temp_path = UPLOAD_DIR / file.filename
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        result = ingest_pdf(str(temp_path), file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()
        file.file.close()

    return result


# ────────────────────────────────────────
# ROUTE: List ingested documents
# ────────────────────────────────────────
@app.get("/documents")
def get_documents():
    """
    Returns all document names currently stored in ChromaDB.
    The frontend calls this on startup and after each upload so it can
    show the list of available documents in the sidebar.
    """
    docs = list_ingested_documents()
    return {"documents": docs}


# ────────────────────────────────────────
# ROUTE: Delete a document
# ────────────────────────────────────────
@app.delete("/documents/{doc_name}")
def remove_document(doc_name: str):
    """
    Deletes all chunks for a document from ChromaDB.
    Path parameters in FastAPI: {doc_name} in the route string becomes
    the doc_name parameter in the function automatically.
    """
    success = delete_document(doc_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document '{doc_name}' not found.")
    return {"deleted": doc_name}


# ────────────────────────────────────────
# ROUTE: Chat (standard, non-streaming)
# ────────────────────────────────────────
@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Standard RAG query. Waits for the full answer before responding.
    Use this for simple integrations or when streaming is not needed.
    The chat_history field enables multi-turn conversation memory:
    pass the previous messages and the LLM resolves references like
    "they", "it", "the method mentioned above" correctly.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        result = query_rag(request.question, request.chat_history, request.doc_filter)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    return {"answer": result["answer"], "sources": result["sources"]}


# ────────────────────────────────────────
# ROUTE: Chat (streaming)
# ────────────────────────────────────────
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming RAG query using Server-Sent Events (SSE).

    How SSE works:
    - The response Content-Type is "text/event-stream"
    - The connection stays open after the headers are sent
    - The server pushes "data: <text>\n\n" chunks as they become available
    - The browser's EventSource API or fetch ReadableStream reads them live
    - When the server yields "data: [DONE]\n\n", the client knows to close

    Why StreamingResponse?
    FastAPI's StreamingResponse accepts a Python generator and forwards
    each yielded string to the client immediately — no buffering.
    Without it, Python would run the generator to completion and send
    everything at once, defeating the purpose of streaming.

    The generator (query_rag_stream) yields:
    1. "data: SOURCES:[...json...]\n\n"  — source chunks for the sidebar
    2. "data: <token>\n\n" (many times) — LLM output tokens
    3. "data: [DONE]\n\n"               — end signal
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    return StreamingResponse(
        query_rag_stream(request.question, request.chat_history, request.doc_filter),
        media_type="text/event-stream",
        # These headers prevent buffering at the HTTP layer:
        # - Cache-Control: no-cache stops proxies from caching the stream
        # - X-Accel-Buffering: no tells nginx not to buffer SSE responses
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ────────────────────────────────────────
# ROUTE: Suggest Questions
# ────────────────────────────────────────
@app.post("/suggest-questions")
async def suggest_questions_endpoint(request: SuggestRequest):
    """
    Generate 5 AI-powered question suggestions based on available documents.
    """
    try:
        from rag import suggest_questions
        questions = suggest_questions(request.doc_filter)
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")


# ────────────────────────────────────────
# ROUTE: Evaluate
# ────────────────────────────────────────
@app.post("/evaluate")
async def evaluate_pipeline(request: EvaluateRequest):
    """
    Runs RAGAS evaluation on test questions.
    Slow (~1-2 min) because it calls GPT-4 as a judge for each question.
    """
    if not request.questions:
        raise HTTPException(status_code=400, detail="Provide at least one question.")
    try:
        report = run_evaluation(request.questions)
        return {"report": report, "interpretation": interpret_scores(report)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
