import React from "react";

export default function DocumentList({ apiBase, documents, onRefresh }) {
  if (!documents || documents.length === 0) return null;

  const handleDelete = async (docName) => {
    if (window.confirm(`Are you sure you want to delete ${docName}?`)) {
      try {
        const response = await fetch(`${apiBase}/documents/${encodeURIComponent(docName)}`, {
          method: "DELETE",
        });
        if (response.ok) {
          onRefresh();
        } else {
          console.error("Failed to delete document");
        }
      } catch (err) {
        console.error("Error deleting document", err);
      }
    }
  };

  return (
    <div className="document-list">
      <h3 className="document-list-title">Active Documents</h3>
      {documents.map((doc, idx) => (
        <div key={idx} className="document-row">
          <div className="doc-row-left">
            <span className="doc-active-dot" title="Active" />
            <span className="doc-name">{doc}</span>
          </div>
          <button 
            className="doc-delete-btn" 
            onClick={() => handleDelete(doc)}
            title="Delete document"
            aria-label={`Delete ${doc}`}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              <line x1="10" y1="11" x2="10" y2="17"></line>
              <line x1="14" y1="11" x2="14" y2="17"></line>
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
