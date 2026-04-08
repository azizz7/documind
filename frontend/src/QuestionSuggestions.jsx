import React, { useState, useEffect } from 'react';

export default function QuestionSuggestions({ apiBase, selectedDoc, onSelect }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchQuestions = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${apiBase}/suggest-questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doc_filter: selectedDoc === 'all' ? null : selectedDoc })
      });
      if (response.ok) {
        const data = await response.json();
        setQuestions(data.questions || []);
      } else {
        setQuestions([]);
      }
    } catch (e) {
      console.error(e);
      setQuestions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDoc]);

  if (!loading && questions.length === 0) return null;

  return (
    <div className="suggestions-row">
      {loading ? (
        Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="suggestion-pill skeleton" />
        ))
      ) : (
        <>
          {questions.map((q, i) => (
            <button key={i} className="suggestion-pill" onClick={() => onSelect(q)}>
              {q}
            </button>
          ))}
          <button className="suggestion-refresh" onClick={fetchQuestions} aria-label="Refresh suggestions">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"/>
            </svg>
          </button>
        </>
      )}
    </div>
  );
}
