import { useState } from "react";

export default function SourceCard({ source }) {
  // Toggle to show/hide the full snippet text
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="source-card">
      <div className="source-header" onClick={() => setExpanded(!expanded)}>
        <span className="source-dot" />
        <span className="source-filename">{source.source}</span>
      </div>

      {/* Snippet preview */}
      <p className="source-snippet">
        {expanded ? source.snippet : source.snippet.slice(0, 100) + "..."}
      </p>

      <button
        className="source-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? "Show less" : "Show more"}
      </button>
    </div>
  );
}
