"""Answer a question using only the stored documents.

Run from the project root:
    python -m rag.ask "Wie oft darf ich eine Prüfung wiederholen?"
    python -m rag.ask "What is StEOP?" --show-context     # also print the retrieved chunks
    python -m rag.ask                                     # interactive mode, empty line to quit
"""

import argparse
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

from rag.config import QUERY_TRANSLATION, ROOT, TOP_K, embed_query, get_collection, get_embedder

NO_ANSWER = "The documents don't contain an answer to this question."

SYSTEM_PROMPT = f"""You answer questions about university documents.

Rules:
- Use ONLY the context passages below. Never use outside knowledge.
- After each statement, cite its source by copying the tag shown above that passage
  exactly, e.g. [satzung_studienrecht_2026.pdf, p. 29]. Never cite passage numbers.
- If the passages don't contain the answer, reply with exactly: "{NO_ANSWER}"
  (translated into the question's language if needed) and nothing else.
- Answer in the same language as the question. Keep it short and precise."""


TRANSLATE_PROMPT = """Translate the user's question into German and into English.
Reply with exactly two lines: line 1 the German version, line 2 the English version.
No numbering, no quotes, no other text."""


def get_client() -> OpenAI:
    return OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])


def translate_query(question: str) -> list[str]:
    """Return the question in German and English (best effort; [] if the reply is odd)."""
    response = get_client().chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0,
        messages=[{"role": "system", "content": TRANSLATE_PROMPT},
                  {"role": "user", "content": question}],
    )
    lines = [l.strip() for l in response.choices[0].message.content.splitlines() if l.strip()]
    if len(lines) == 1:
        # Small models sometimes put both versions on one line: "Wie ...? How ...?"
        lines = [part.strip() for part in re.split(r"(?<=\?)\s+", lines[0]) if part.strip()]
    return lines[:2]


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    """Search with the original question (plus German/English versions if enabled).

    Each version returns its own top k. A chunk found by several versions keeps its
    best score, then the overall top k are returned.
    """
    queries = [question]
    if QUERY_TRANSLATION:
        queries += [q for q in translate_query(question) if q.lower() != question.lower()]

    best: dict[str, dict] = {}
    for query in queries:
        result = get_collection().query(
            query_embeddings=[embed_query(query)],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        for cid, text, meta, dist in zip(result["ids"][0], result["documents"][0],
                                         result["metadatas"][0], result["distances"][0]):
            sim = 1 - dist  # cosine distance -> similarity
            if cid not in best or sim > best[cid]["similarity"]:
                best[cid] = {"text": text, "source": meta["source"], "page": meta["page"],
                             "similarity": sim, "query": query}
    return sorted(best.values(), key=lambda h: h["similarity"], reverse=True)[:k]


def build_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f"Source: [{h['source']}, p. {h['page']}]\n{h['text']}" for h in hits
    )


def generate(question: str, context: str) -> tuple[str, object]:
    response = get_client().chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0,  # same question -> (nearly) same answer; easier to evaluate
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    return response.choices[0].message.content.strip(), response.usage


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
        print(f"  {h['similarity']:.3f}  {h['source']}, p. {h['page']}")
    tokens = f", {usage.prompt_tokens} in / {usage.completion_tokens} out tokens" if usage else ""
    print(f"Time: retrieval {1000 * (t1 - t0):.0f} ms, LLM {1000 * (t2 - t1):.0f} ms{tokens}")


def main() -> None:
    load_dotenv(ROOT / ".env")
    get_embedder()  # load the embedding model once up front, so it isn't counted as retrieval time
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
