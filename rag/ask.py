"""Answer a question using only the stored documents.

Run from the project root:
    python -m rag.ask "Wie oft darf ich eine Prüfung wiederholen?"
    python -m rag.ask "What is StEOP?" --show-context     # also print the retrieved chunks
    python -m rag.ask                                     # interactive mode, empty line to quit
"""

import argparse
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

from rag.config import ROOT, TOP_K, embed_query, get_collection

NO_ANSWER = "The documents don't contain an answer to this question."

SYSTEM_PROMPT = f"""You answer questions about university documents.

Rules:
- Use ONLY the numbered context passages below. Never use outside knowledge.
- After each statement, cite its source in the form [file, p. X].
- If the passages don't contain the answer, reply with exactly: "{NO_ANSWER}"
  (translated into the question's language if needed) and nothing else.
- Answer in the same language as the question. Keep it short and precise."""


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    result = get_collection().query(
        query_embeddings=[embed_query(question)],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    hits = []
    for text, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        hits.append({"text": text, "source": meta["source"], "page": meta["page"],
                     "similarity": 1 - dist})  # cosine distance -> similarity
    return hits


def build_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] ({h['source']}, p. {h['page']})\n{h['text']}" for i, h in enumerate(hits, start=1)
    )


def generate(question: str, context: str) -> tuple[str, object]:
    client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
    response = client.chat.completions.create(
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
