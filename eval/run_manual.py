"""Run all manual test questions in one go and save the answers to a file.

Run from the project root:
    python -m eval.run_manual

Output: eval/results/manual_<date-time>.md  (answer, retrieved pages, scores, timing per question)
Then compare each answer with the expected one in eval/manual_questions.md.
"""

import time
from datetime import datetime

from dotenv import load_dotenv

from rag.ask import build_context, generate, retrieve
from rag import config
from rag.config import ROOT, get_embedder

QUESTIONS = [
    # German
    ("1", "Wie oft darf ich eine negativ beurteilte Prüfung wiederholen?"),
    ("2", "Darf ich eine positive Prüfung wiederholen, um die Note zu verbessern?"),
    ("3", "What is the StEOP and how do I complete it?"),
    ("4", "Was kostet das Parkticket für Studierende?"),
    ("5", "Darf ich meinen Hund mit auf den Campus nehmen?"),
    ("6", "How long is the AI master's and what language is it taught in?"),
    ("7", "Bis wann muss ich mich von einer Lehrveranstaltung abmelden?"),
    ("8", "Wie lange darf ich ein Buch aus der Bibliothek ausleihen?"),
    ("9", "Who won the Champions League in 2026?"),
    ("10", "Wie lautet das WLAN-Passwort der JKU?"),
    # English -> English documents
    ("E1", "How many ECTS of free electives do I need in the AI bachelor, and where can I take them?"),
    ("E2", "How do I find a topic for my bachelor thesis?"),
    ("E3", "How do I sign up for the AI mentoring program?"),
    # English -> German documents
    ("E4", "How many times can I retake a failed exam?"),
    ("E5", "How much does student parking cost per semester?"),
    ("E6", "Can I bring my dog to campus?"),
    ("E7", "Until when can I deregister from a course?"),
    ("E8", "How long can I borrow a library book?"),
    # Not answerable
    ("E9", "What is the JKU WiFi password?"),
    ("E10", "Who won the Champions League in 2026?"),
]


def main() -> None:
    load_dotenv(ROOT / ".env")
    get_embedder()  # load once, not per question

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"manual_{datetime.now():%Y-%m-%d_%H-%M}.md"

    lines = [f"# Manual run {datetime.now():%Y-%m-%d %H:%M}\n",
             f"Embedding: {config.EMBEDDING_MODEL} | translation: {config.QUERY_TRANSLATION} | "
             f"hybrid: {config.HYBRID_SEARCH} | reranker: {config.RERANKER_MODEL if config.USE_RERANKER else 'off'}\n"]
    for qid, question in QUESTIONS:
        print(f"[{qid}] {question}")
        t0 = time.perf_counter()
        hits = retrieve(question)
        t1 = time.perf_counter()
        answer, usage = generate(question, build_context(hits))
        t2 = time.perf_counter()

        lines.append(f"## {qid}. {question}\n")
        lines.append(answer + "\n")
        lines.append("Retrieved:")
        for h in hits:
            lines.append(f"- {h['score']:.3f}  {h['source']}, p. {h['page']}")
        tokens = f", {usage.prompt_tokens} in / {usage.completion_tokens} out tokens" if usage else ""
        lines.append(f"\nTime: retrieval {1000 * (t1 - t0):.0f} ms, LLM {1000 * (t2 - t1):.0f} ms{tokens}\n")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
