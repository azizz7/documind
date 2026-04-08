"""
evaluate.py — Evaluates the RAG pipeline using the RAGAS framework.

RAGAS measures three core metrics:

1. FAITHFULNESS
   "Did the answer actually come from the retrieved context?"
   Scores 0–1. A score of 1 means every claim in the answer
   is supported by the retrieved chunks. A score of 0.4 means
   ~40% of claims are grounded — the rest are hallucinated.
   How it works: RAGAS breaks the answer into individual claims,
   then checks each claim against the context using an LLM judge.

2. ANSWER RELEVANCY
   "Does the answer actually address the question asked?"
   Scores 0–1. An answer that's technically correct but off-topic
   gets a low score. Measured by generating questions from the
   answer and checking if they match the original question.

3. CONTEXT RECALL (requires reference/ground truth answer)
   "Did the retrieved chunks contain the information needed to answer?"
   This measures whether your vector search found the right chunks.
   Requires a ground truth answer to compare against.
   We use a simplified version that checks context relevance without
   requiring ground truth — useful for quick automated evals.

Why evaluate?
A RAG system can fail in two ways:
- Retrieval failure: the wrong chunks were fetched (bad embeddings or chunking)
- Generation failure: the LLM ignored the context or hallucinated
RAGAS separates these two failure modes so you know what to fix.
"""

import os
from dotenv import load_dotenv
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from rag import query_rag

load_dotenv()


def run_evaluation(test_questions: list[str]) -> dict:
    """
    Runs the RAG pipeline on a list of test questions,
    then evaluates the results using RAGAS.

    Parameters:
        test_questions: list of question strings to test

    Returns:
        A dict with per-question results and aggregate scores.

    How RAGAS works under the hood:
    It uses an LLM (GPT-4 by default) as a judge to evaluate quality.
    This is called "LLM-as-judge" evaluation — instead of needing human
    labels for every question, you use a strong LLM to assess quality.
    """

    print("Running RAG pipeline on test questions...")

    # Run RAG for each question and collect the inputs RAGAS needs
    questions = []
    answers = []
    contexts = []

    for q in test_questions:
        print(f"  Processing: {q}")
        result = query_rag(q)

        questions.append(q)
        answers.append(result["answer"])
        # RAGAS expects contexts as a list of lists — each question gets
        # a list of context string chunks
        contexts.append(result["context_chunks"])

    # ── Build the RAGAS Dataset ──
    # RAGAS requires a HuggingFace Dataset object with specific column names:
    # - "question": the input question
    # - "answer": the LLM's generated answer
    # - "contexts": list of retrieved context strings for that question
    eval_dataset = Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
    })

    print("\nRunning RAGAS evaluation (this calls GPT-4 as judge)...")

    # ── Run RAGAS ──
    # faithfulness: checks if answer claims are grounded in context
    # answer_relevancy: checks if answer is relevant to the question
    results = evaluate(
        dataset=eval_dataset,
        metrics=[faithfulness, answer_relevancy]
    )

    # Convert results to a readable dict
    scores_df = results.to_pandas()

    # Build a summary report
    report = {
        "aggregate_scores": {
            "faithfulness": round(float(scores_df["faithfulness"].mean()), 3),
            "answer_relevancy": round(float(scores_df["answer_relevancy"].mean()), 3),
        },
        "per_question": []
    }

    for i, row in scores_df.iterrows():
        report["per_question"].append({
            "question": questions[i],
            "answer_preview": answers[i][:150] + "...",
            "faithfulness": round(float(row["faithfulness"]), 3),
            "answer_relevancy": round(float(row["answer_relevancy"]), 3),
        })

    return report


def interpret_scores(report: dict) -> str:
    """
    Converts raw RAGAS scores into human-readable interpretation.
    Useful for the API response and UI display.
    """
    faith = report["aggregate_scores"]["faithfulness"]
    relevancy = report["aggregate_scores"]["answer_relevancy"]

    interpretation = []

    if faith >= 0.8:
        interpretation.append(f"Faithfulness: {faith} — GOOD. Most answers are grounded in the document.")
    elif faith >= 0.5:
        interpretation.append(f"Faithfulness: {faith} — MODERATE. Some hallucination detected. Consider smaller chunks or stricter prompt.")
    else:
        interpretation.append(f"Faithfulness: {faith} — POOR. Significant hallucination. Review your prompt template.")

    if relevancy >= 0.8:
        interpretation.append(f"Answer Relevancy: {relevancy} — GOOD. Answers address the questions well.")
    elif relevancy >= 0.5:
        interpretation.append(f"Answer Relevancy: {relevancy} — MODERATE. Some answers are off-topic.")
    else:
        interpretation.append(f"Answer Relevancy: {relevancy} — POOR. Check retrieval — wrong chunks may be surfacing.")

    return "\n".join(interpretation)


# ── Quick test you can run directly ──
if __name__ == "__main__":
    sample_questions = [
        "What is the main topic of this document?",
        "What are the key findings or conclusions?",
        "What methodology was used?",
    ]

    report = run_evaluation(sample_questions)
    print("\n=== EVALUATION REPORT ===")
    print(interpret_scores(report))
    print("\nPer-question breakdown:")
    for item in report["per_question"]:
        print(f"\nQ: {item['question']}")
        print(f"   Faithfulness: {item['faithfulness']} | Relevancy: {item['answer_relevancy']}")
