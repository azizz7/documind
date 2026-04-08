import os
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain.schema import SystemMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage

load_dotenv()

CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "documents"

# How many chunks to retrieve per query.
# 4 is a good default — enough context without overwhelming the LLM.
TOP_K = 4

# How many previous conversation turns to include in the prompt.
# 1 turn = 1 human message + 1 AI reply.
# Keep this low (3-5) to avoid burning too many tokens on history.
MAX_HISTORY_TURNS = 5


def get_vectorstore() -> Chroma:
    """
    Load ChromaDB from disk using the same embedding model as ingestion.
    Using a different model here than in ingest.py would return garbage results
    because the two vector spaces would be incompatible.
    """
    embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embeddings_model,
        collection_name=COLLECTION_NAME
    )


def format_chunks_as_context(docs: list) -> str:
    """
    Format retrieved Document objects into a single labeled context string.
    Each chunk is separated by a divider so the LLM can see boundaries.
    The [Source] labels are how the LLM knows which document each fact came from.
    """
    parts = []
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "unknown")
        chunk_idx = doc.metadata.get("chunk_index", i)
        parts.append(f"[Source: {source}, Chunk {chunk_idx}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def suggest_questions(doc_filter: str = None) -> list[str]:
    import json
    
    vectorstore = get_vectorstore()
    query = "main topics key findings summary"
    
    if doc_filter:
        retrieved_docs = vectorstore.similarity_search(query, k=3, filter={"source": doc_filter})
    else:
        retrieved_docs = vectorstore.similarity_search(query, k=3)
        
    if not retrieved_docs:
        return []
        
    context = format_chunks_as_context(retrieved_docs)
    
    system_prompt = f"""You are a helpful assistant. Based on the documents available, generate exactly 5 short, specific, interesting questions a user might want to ask. Each question must be under 12 words. Return ONLY a JSON array of 5 strings, no other text. Example: ["What is X?", "How does Y work?"]

Context:
{context}"""

    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.7)
    response = llm.invoke([SystemMessage(content=system_prompt)])
    
    try:
        text = response.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        questions = json.loads(text.strip())
        if isinstance(questions, list):
            return questions[:5]
    except Exception:
        pass
        
    return []


def build_messages_with_history(
    context: str,
    question: str,
    chat_history: list[dict]
) -> list:
    """
    Builds the full message list to send to the LLM, including:
    - A system message with the RAG context
    - Previous conversation turns (conversation memory)
    - The current user question

    Why include history?
    Without it, every question is isolated. "Who wrote this?" → answer.
    "What else did they publish?" → LLM has no idea who 'they' refers to.

    With history, the LLM sees the prior exchanges and resolves references.

    chat_history format: [{"role": "user"|"assistant", "content": "..."}]
    We trim to the last MAX_HISTORY_TURNS pairs to control token cost.
    """

    # System prompt: sets the LLM's role and injects the retrieved context.
    # We put context in the system message so it has the highest weight
    # and is always present regardless of how many history turns there are.
    system_content = f"""You are a helpful assistant that answers questions based strictly on the provided document context.

Use ONLY the information in the context below to answer the question.
If the answer is not found in the context, respond with:
"I don't have enough information in the provided document to answer this."

Context:
{context}"""

    messages = [{"role": "system", "content": system_content}]

    # Add conversation history (trim to last N turns to save tokens)
    # Each "turn" = one user message + one assistant reply = 2 items
    max_items = MAX_HISTORY_TURNS * 2
    recent_history = chat_history[-max_items:] if len(chat_history) > max_items else chat_history

    for turn in recent_history:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Add the current question
    messages.append({"role": "user", "content": question})

    return messages


def query_rag(question: str, chat_history: list[dict] = None, doc_filter: str = None) -> dict:
    """
    Full RAG query pipeline with conversation memory.

    Parameters:
        question: the user's current question
        chat_history: list of previous messages in format
                      [{"role": "user"|"assistant", "content": "..."}]

    Returns:
        answer: LLM response string
        sources: list of source chunk references for the UI
        context_chunks: raw chunk text (used by evaluate.py)
    """
    if chat_history is None:
        chat_history = []

    # ── Step 1: Retrieve relevant chunks ──
    vectorstore = get_vectorstore()
    if doc_filter:
        retrieved_docs = vectorstore.similarity_search(question, k=TOP_K, filter={"source": doc_filter})
    else:
        retrieved_docs = vectorstore.similarity_search(question, k=TOP_K)

    if not retrieved_docs:
        return {
            "answer": "No documents have been uploaded yet. Please upload a PDF first.",
            "sources": [],
            "context_chunks": []
        }

    # ── Step 2: Build prompt with history ──
    context = format_chunks_as_context(retrieved_docs)
    messages = build_messages_with_history(context, question, chat_history)

    # ── Step 3: Call the LLM ──
    # temperature=0: deterministic, no randomness — correct for a Q&A system.
    # If you wanted creative summaries you'd use 0.3-0.7.
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    response = llm.invoke(messages)
    answer = response.content

    # ── Step 4: Build source references ──
    sources = [
        {
            "source": doc.metadata.get("source", "unknown"),
            "chunk_index": doc.metadata.get("chunk_index", 0),
            "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        }
        for doc in retrieved_docs
    ]

    return {
        "answer": answer,
        "sources": sources,
        "context_chunks": [doc.page_content for doc in retrieved_docs]
    }


def query_rag_stream(question: str, chat_history: list[dict] = None, doc_filter: str = None):
    """
    Streaming version of query_rag.

    Instead of waiting for the full answer, this is a Python generator
    that yields tokens as they arrive from the LLM.

    How streaming works:
    - LLMs generate text token by token internally.
    - Normally, the API buffers all tokens and sends the full response at once.
    - With streaming=True, the API sends each token as a Server-Sent Event (SSE)
      as soon as it's generated — no waiting for the full response.
    - FastAPI's StreamingResponse wraps this generator and sends each yielded
      chunk to the browser immediately.
    - The React frontend reads the stream with the Fetch API's ReadableStream.

    Why this matters for UX:
    - Without streaming: user stares at a spinner for 5-10 seconds.
    - With streaming: user sees words appearing within ~500ms, like ChatGPT.
    - The perceived wait time drops dramatically even though total latency is similar.

    This function yields strings in SSE format: "data: <token>\n\n"
    The frontend splits on this format to extract individual tokens.
    """
    if chat_history is None:
        chat_history = []

    # Same retrieval logic as non-streaming version
    vectorstore = get_vectorstore()
    if doc_filter:
        retrieved_docs = vectorstore.similarity_search(question, k=TOP_K, filter={"source": doc_filter})
    else:
        retrieved_docs = vectorstore.similarity_search(question, k=TOP_K)

    if not retrieved_docs:
        yield "data: No documents uploaded yet.\n\n"
        return

    context = format_chunks_as_context(retrieved_docs)
    messages = build_messages_with_history(context, question, chat_history)

    # streaming=True tells the Google Generative AI SDK to return a generator instead of
    # buffering the full response. Each iteration gives a chunk object
    # with a delta containing the next token(s).
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, streaming=True)

    # First, yield the sources as a JSON header before the streamed text
    # The frontend reads this first to render the source cards, then
    # reads the subsequent token stream for the answer text.
    import json
    sources = [
        {
            "source": doc.metadata.get("source", "unknown"),
            "chunk_index": doc.metadata.get("chunk_index", 0),
            "snippet": doc.page_content[:200] + "..."
        }
        for doc in retrieved_docs
    ]
    yield f"data: SOURCES:{json.dumps(sources)}\n\n"

    # Stream the LLM tokens
    # llm.stream() returns an iterator of AIMessageChunk objects
    # Each chunk has a .content attribute with 1-3 tokens of text
    for chunk in llm.stream(messages):
        if chunk.content:
            # Escape newlines so they survive the SSE wire format
            token = chunk.content.replace("\n", "\\n")
            yield f"data: {token}\n\n"

    # Signal stream end so the frontend knows to stop reading
    yield "data: [DONE]\n\n"
