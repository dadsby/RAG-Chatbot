"""Answer a question using only the stored documents.

Run from the project root:
    python -m rag.ask "Wie oft darf ich eine Prüfung wiederholen?"
    python -m rag.ask "What is StEOP?" --show-context     # also print the retrieved chunks
    python -m rag.ask                                     # interactive mode, empty line to quit
"""

import argparse
import time

from dotenv import load_dotenv

from rag import config
from rag.config import ROOT, get_embedder, get_reranker
from rag.llm import chat
from rag.retrieval import retrieve  # noqa: F401  (re-exported for eval scripts)

NO_ANSWER = "The documents don't contain an answer to this question."

SYSTEM_PROMPT = f"""You answer questions about university documents.

Rules:
- Use ONLY the context passages below. Never use outside knowledge.
- After each statement, cite its source by copying the tag shown above that passage
  exactly, e.g. [satzung_studienrecht_2026.pdf, p. 29]. Never cite passage numbers.
- If the passages don't contain the answer, reply with exactly: "{NO_ANSWER}"
  (translated into the question's language if needed) and nothing else.
- Answer in the same language as the question. Keep it short and precise."""


def build_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f"Source: [{h['source']}, p. {h['page']}]\n{h['text']}" for h in hits
    )


def generate(question: str, context: str) -> tuple[str, object]:
    return chat(SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion: {question}")


def answer(question: str, show_context: bool = False) -> None:
    t0 = time.perf_counter()
    hits = retrieve(question)
    t1 = time.perf_counter()
    context = build_context(hits)
    text, usage = generate(question, context)
    t2 = time.perf_counter()

    if show_context:
        print("\n--- Retrieved context ---\n" + context + "\n-------------------------")

    print("\n" + text + "\n")
    print("Retrieved:")
    for h in hits:
        print(f"  {h['score']:.3f}  {h['source']}, p. {h['page']}")
    tokens = f", {usage.prompt_tokens} in / {usage.completion_tokens} out tokens" if usage else ""
    print(f"Time: retrieval {1000 * (t1 - t0):.0f} ms, LLM {1000 * (t2 - t1):.0f} ms{tokens}")


def main() -> None:
    load_dotenv(ROOT / ".env")
    get_embedder()  # load models once up front, so loading isn't counted as retrieval time
    if config.USE_RERANKER:
        get_reranker()
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", help="leave out for interactive mode")
    parser.add_argument("--show-context", action="store_true")
    args = parser.parse_args()

    if args.question:
        answer(args.question, args.show_context)
        return
    while True:
        question = input("\nQuestion (empty to quit): ").strip()
        if not question:
            break
        answer(question, args.show_context)


if __name__ == "__main__":
    main()
