"""Answer a question using only the stored documents.

Run from the project root:
    python -m rag.ask "Wie oft darf ich eine Prüfung wiederholen?"
    python -m rag.ask "What is StEOP?" --show-context     # also print the retrieved chunks
    python -m rag.ask                                     # interactive mode, empty line to quit
"""

import argparse

from dotenv import load_dotenv

from rag import config
from rag.answer import answer_question, build_context
from rag.config import ROOT, get_embedder, get_reranker


def show(question: str, show_context: bool = False) -> None:
    r = answer_question(question)
    if show_context:
        print("\n--- Retrieved context ---\n" + build_context(r["hits"]) + "\n-------------------------")
    print("\n" + r["answer"] + "\n")
    if r["refused_by"] == "threshold":
        print(f"(Refused without asking the LLM: best reranker score {r['top_score']:.3f} "
              f"< threshold {config.REFUSAL_THRESHOLD})")
    print("Retrieved:")
    for h in r["hits"]:
        print(f"  {h['score']:.3f}  {h['source']}, p. {h['page']}")
    u = r["usage"]
    tokens = f", {u.prompt_tokens} in / {u.completion_tokens} out tokens" if u else ""
    print(f"Time: retrieval {r['retrieval_ms']:.0f} ms, LLM {r['llm_ms']:.0f} ms{tokens}")


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
        show(args.question, args.show_context)
        return
    while True:
        question = input("\nQuestion (empty to quit): ").strip()
        if not question:
            break
        show(question, args.show_context)


if __name__ == "__main__":
    main()
