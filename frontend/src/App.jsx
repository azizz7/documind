import { useState, useEffect } from "react";
import FileUpload from "./FileUpload";
import ChatWindow from "./ChatWindow";
import EvaluationPanel from "./EvaluationPanel";
import DocumentList from "./DocumentList";
import "./App.css";

// The base URL of our FastAPI backend
// In production, this would be your deployed server URL
const API_BASE = "http://localhost:8000";

export default function App() {
  // ── State ──
  // React state = data that, when changed, causes the UI to re-render.
  // Every useState call returns [currentValue, setterFunction].

  // Array of ingested document filenames
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState('all');
  
  // Document is ready if we have at least one uploaded
  const documentReady = documents.length > 0;

  // Array of chat messages: [{ role: "user"|"assistant", content, sources }]
  const [messages, setMessages] = useState([]);

  // Whether the API server is reachable
  const [serverOnline, setServerOnline] = useState(false);

  // Which tab is active: "chat" or "evaluate"
  const [activeTab, setActiveTab] = useState("chat");

  // ── Health Check on mount ──
  // useEffect with [] runs once when the component first renders (like componentDidMount)
  // We ping the /health endpoint to show a status indicator
  // Pull document list from API
  const fetchDocuments = () => {
    fetch(`${API_BASE}/documents`)
      .then(res => res.json())
      .then(data => {
        if (data && data.documents) {
          setDocuments(data.documents);
        }
      })
      .catch(() => console.error("Failed to load documents"));
  };

  // ── Initialization on mount ──
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(res => res.json())
      .then(() => setServerOnline(true))
      .catch(() => setServerOnline(false));

    fetchDocuments();
  }, []);

  // ── Handle PDF Upload ──
  const handleUploadSuccess = () => {
    fetchDocuments();
  };

  // ── Handle sending a chat message (streaming version) ──
  const handleSendMessage = async (question) => {
    // Add user message immediately
    const userMessage = { role: "user", content: question, sources: [] };

    // Build the chat history from current messages to pass for memory.
    // We include only role + content, not UI-only fields like loading/streaming.
    const historyForAPI = messages.map(m => ({
      role: m.role,
      content: m.content
    }));

    setMessages(prev => [...prev, userMessage]);

    // Add a loading placeholder for the assistant reply
    setMessages(prev => [...prev, {
      role: "assistant", content: "", sources: [], loading: true, streaming: false, targetDoc: selectedDoc
    }]);

    try {
      // Call the streaming endpoint
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          question, 
          chat_history: historyForAPI,
          doc_filter: selectedDoc === 'all' ? null : selectedDoc
        }),
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      // response.body is a ReadableStream — we get a reader to consume it
      const reader = response.body.getReader();
      // TextDecoder converts raw bytes → UTF-8 strings
      const decoder = new TextDecoder();

      let sources = [];
      let fullAnswer = "";

      // Switch the placeholder from loading to streaming
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant", content: "", sources: [], loading: false, streaming: true, targetDoc: selectedDoc
        };
        return updated;
      });

      // Read loop — runs until the stream closes
      while (true) {
        // reader.read() returns { value: Uint8Array, done: boolean }
        const { value, done } = await reader.read();
        if (done) break;

        // Decode the binary chunk to a string
        const text = decoder.decode(value, { stream: true });

        // The SSE format gives us potentially multiple events per chunk.
        // Split on "\n\n" to separate individual events.
        const lines = text.split("\n\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6); // strip "data: " prefix

          if (data === "[DONE]") break;

          if (data.startsWith("SOURCES:")) {
            // Parse the source list sent before the token stream
            sources = JSON.parse(data.slice(8));
          } else {
            // Regular token — unescape newlines and append to answer
            const token = data.replace(/\\n/g, "\n");
            fullAnswer += token;

            // Update the last message live as tokens arrive.
            // We use the functional form of setMessages so we always
            // operate on the latest state, not a stale closure.
              setMessages(prev => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: "assistant",
                content: fullAnswer,
                sources: [],
                loading: false,
                streaming: true,
                targetDoc: selectedDoc
              };
              return updated;
            });
          }
        }
      }

      // Stream complete — set final state with sources visible
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: fullAnswer,
          sources,
          loading: false,
          streaming: false,
          targetDoc: selectedDoc
        };
        return updated;
      });

    } catch (error) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: `Error: ${error.message}. Is the backend running?`,
          sources: [],
          loading: false,
          streaming: false
        };
        return updated;
      });
    }
  };

  // ── Render ──
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="logo-square">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#0c0c0e" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
          </div>
          <h1>DocuMind</h1>
          {documents.length > 0 && (
            <span className="doc-count-badge">{documents.length} {documents.length === 1 ? 'doc' : 'docs'}</span>
          )}
        </div>
        <div className="header-right">
          <span className={`status-dot ${serverOnline ? "online" : "offline"}`} />
          <span className="status-label">{serverOnline ? "Connected" : "Disconnected"}</span>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="tabs">
        <button
          className={`tab ${activeTab === "chat" ? "active" : ""}`}
          onClick={() => setActiveTab("chat")}
        >
          Chat
        </button>
        <button
          className={`tab ${activeTab === "evaluate" ? "active" : ""}`}
          onClick={() => setActiveTab("evaluate")}
        >
          Evaluate
        </button>
      </nav>

      {/* Main content */}
      <main className="main">
        {/* Left panel: file upload */}
        <aside className="sidebar">
          <FileUpload
            apiBase={API_BASE}
            onUploadSuccess={handleUploadSuccess}
          />
          <DocumentList
            apiBase={API_BASE}
            documents={documents}
            onRefresh={fetchDocuments}
          />
        </aside>

        {/* Right panel: chat or evaluation */}
        <section className="content">
          {activeTab === "chat" ? (
            <ChatWindow
              messages={messages}
              onSendMessage={handleSendMessage}
              documentReady={documentReady}
              apiBase={API_BASE}
              selectedDoc={selectedDoc}
              setSelectedDoc={setSelectedDoc}
              documents={documents}
            />
          ) : (
            <EvaluationPanel apiBase={API_BASE} documentReady={documentReady} />
          )}
        </section>
      </main>
    </div>
  );
}
