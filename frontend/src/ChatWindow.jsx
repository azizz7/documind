import { useState, useRef, useEffect } from "react";
import SourceCard from "./SourceCard";
import QuestionSuggestions from "./QuestionSuggestions";

export default function ChatWindow({ messages, onSendMessage, documentReady, apiBase, selectedDoc, setSelectedDoc, documents }) {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const question = inputValue.trim();
    if (!question || !documentReady) return;
    onSendMessage(question);
    setInputValue("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-window">
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            {documentReady
              ? "Document ready. Ask anything about it below."
              : "Upload a PDF on the left to get started."}
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className={`message message-${msg.role}`}>
              {msg.role === "assistant" && <div className="avatar avatar-ai">AI</div>}
              {msg.role === "user" && <div className="avatar avatar-user" />}
              <div className="message-wrapper">
                {msg.role === "assistant" && msg.targetDoc && msg.targetDoc !== 'all' && (
                  <div className="target-doc-label">Searching in: {msg.targetDoc}</div>
                )}
                <div className="message-bubble">
                  {msg.loading ? (
                    <div className="typing-indicator">
                      <span /><span /><span />
                    </div>
                  ) : (
                    <p style={{ whiteSpace: "pre-wrap" }}>{msg.content}</p>
                  )}
                </div>

              {/* Sources only shown after streaming completes (when msg.streaming is false) */}
              {msg.role === "assistant" && !msg.loading && !msg.streaming && msg.sources?.length > 0 && (
                <div className="sources-section">
                  <div className="sources-grid">
                    {msg.sources.map((source, si) => (
                      <SourceCard key={si} source={source} />
                    ))}
                  </div>
                </div>
              )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {!documentReady ? null : (
        <div className="filter-bar">
          <button 
            className={`filter-pill ${selectedDoc === 'all' ? 'active' : ''}`} 
            onClick={() => setSelectedDoc('all')}
          >
            All documents
          </button>
          {documents && documents.map((doc, idx) => (
            <button 
              key={idx} 
              className={`filter-pill ${selectedDoc === doc ? 'active' : ''}`} 
              onClick={() => setSelectedDoc(doc)}
              title={doc}
            >
              {doc.length > 20 ? doc.substring(0, 20) + "..." : doc}
            </button>
          ))}
        </div>
      )}

      {!documentReady ? null : (
        <QuestionSuggestions 
          apiBase={apiBase} 
          selectedDoc={selectedDoc} 
          onSelect={(q) => {
            setInputValue(q);
            if (inputRef.current) inputRef.current.focus();
          }} 
        />
      )}

      <form className="input-area" onSubmit={handleSubmit}>
        <textarea
          ref={inputRef}
          className="chat-input"
          value={inputValue}
          onChange={e => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            documentReady
              ? "Ask a question about your document..."
              : "Upload a document first"
          }
          disabled={!documentReady}
          rows={2}
        />
        <button
          type="submit"
          className="send-button"
          disabled={!documentReady || !inputValue.trim()}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>
        </button>
      </form>
    </div>
  );
}
