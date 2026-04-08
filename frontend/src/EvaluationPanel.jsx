import { useState } from "react";

export default function EvaluationPanel({ apiBase, documentReady }) {
  const [questions, setQuestions] = useState(
    "What is the main topic of this document?\nWhat are the key findings?\nWhat methodology was used?"
  );
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");

  const handleEvaluate = async () => {
    const questionList = questions
      .split("\n")
      .map(q => q.trim())
      .filter(q => q.length > 0);

    if (questionList.length === 0) return;

    setLoading(true);
    setError("");
    setReport(null);

    try {
      const response = await fetch(`${apiBase}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ questions: questionList }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail);
      }

      const data = await response.json();
      setReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (score) => {
    if (score >= 0.8) return "score-good";
    if (score >= 0.5) return "score-medium";
    return "score-poor";
  };

  return (
    <div className="eval-panel">
      <h2>Pipeline Evaluation</h2>
      <p className="eval-description">
        Enter test questions (one per line). The system will run each through the RAG pipeline
        and score the responses for faithfulness and answer relevancy using RAGAS.
      </p>

      <textarea
        className="eval-input"
        value={questions}
        onChange={e => setQuestions(e.target.value)}
        rows={6}
        placeholder="Enter one question per line..."
        disabled={!documentReady}
      />

      <button
        className="eval-button"
        onClick={handleEvaluate}
        disabled={!documentReady || loading}
      >
        {loading ? "Evaluating (this takes ~1-2 min)..." : "Run Evaluation"}
      </button>

      {error && <div className="eval-error">{error}</div>}

      {report && (
        <div className="eval-results">
          {/* Aggregate scores */}
          <h3>Aggregate Scores</h3>
          <div className="score-cards">
            <div className="score-card">
              <div className="score-label">Faithfulness</div>
              <div className={`score-value ${scoreColor(report.report.aggregate_scores.faithfulness)}`}>
                {(report.report.aggregate_scores.faithfulness * 100).toFixed(0)}%
              </div>
              <div className="score-hint">Are answers grounded in the document?</div>
            </div>
            <div className="score-card">
              <div className="score-label">Answer Relevancy</div>
              <div className={`score-value ${scoreColor(report.report.aggregate_scores.answer_relevancy)}`}>
                {(report.report.aggregate_scores.answer_relevancy * 100).toFixed(0)}%
              </div>
              <div className="score-hint">Do answers address the questions?</div>
            </div>
          </div>

          {/* Interpretation */}
          <div className="eval-interpretation">
            {report.interpretation}
          </div>

          {/* Per-question breakdown */}
          <h3>Per-Question Breakdown</h3>
          {report.report.per_question.map((item, i) => (
            <div key={i} className="eval-row">
              <p className="eval-question">{item.question}</p>
              <div className="eval-scores">
                <span className={`badge ${scoreColor(item.faithfulness)}`}>
                  Faithfulness: {(item.faithfulness * 100).toFixed(0)}%
                </span>
                <span className={`badge ${scoreColor(item.answer_relevancy)}`}>
                  Relevancy: {(item.answer_relevancy * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
