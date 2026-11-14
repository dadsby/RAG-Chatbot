"""Run all manual test questions in one go and save the answers to a file.

Run from the project root:
    python -m eval.run_manual

Output: eval/results/manual_<date-time>.md  (answer, retrieved pages, scores, timing per question)
Then compare each answer with the expected one in eval/manual_questions.md.
"""

from datetime import datetime

from dotenv import load_dotenv

from rag import config
from rag.answer import answer_question
from rag.config import ROOT, get_embedder, get_reranker

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
    if config.USE_RERANKER:
        get_reranker()

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"manual_{datetime.now():%Y-%m-%d_%H-%M}.md"

    lines = [f"# Manual run {datetime.now():%Y-%m-%d %H:%M}\n",
             f"Embedding: {config.EMBEDDING_MODEL} | translation: {config.QUERY_TRANSLATION} | "
             f"hybrid: {config.HYBRID_SEARCH} | reranker: {config.RERANKER_MODEL if config.USE_RERANKER else 'off'} | "
             f"refusal threshold: {config.REFUSAL_THRESHOLD}\n"]
    for qid, question in QUESTIONS:
        print(f"[{qid}] {question}")
        r = answer_question(question)
        lines.append(f"## {qid}. {question}\n")
        lines.append(r["answer"] + "\n")
        if r["refused_by"] == "threshold":
            lines.append(f"_(refused without LLM: top score {r['top_score']:.3f})_\n")
        lines.append("Retrieved:")
        for h in r["hits"]:
            lines.append(f"- {h['score']:.3f}  {h['source']}, p. {h['page']}")
        u = r["usage"]
        tokens = f", {u.prompt_tokens} in / {u.completion_tokens} out tokens" if u else ""
        lines.append(f"\nTime: retrieval {r['retrieval_ms']:.0f} ms, LLM {r['llm_ms']:.0f} ms{tokens}\n")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved to {out_file}")


if __name__ == "__main__":
    main()
