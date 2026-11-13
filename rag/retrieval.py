"""Find the chunks that best answer a question.

Pipeline (each step can be switched on/off in rag/config.py):

  question
    -> [query translation]  LLM rewrites it in German + English
    -> vector search        per question version (meaning)
    -> [BM25 search]        per question version (exact keywords)
    -> RRF fusion           merge all ranked lists into one
    -> [reranker]           cross-encoder re-sorts the best candidates
    -> top k chunks
"""

import re
from functools import lru_cache

from rag import config
from rag.config import embed_query, get_collection, get_reranker
from rag.llm import chat

# ---------------------------------------------------------------- query translation

TRANSLATE_PROMPT = """Translate the user's question into German and into English.
Reply with exactly two lines: line 1 the German version, line 2 the English version.
No numbering, no quotes, no other text."""


def translate_query(question: str) -> list[str]:
    """Return the question in German and English (best effort; [] if the reply is odd)."""
    reply, _ = chat(TRANSLATE_PROMPT, question)
    lines = [l.strip() for l in reply.splitlines() if l.strip()]
    if len(lines) == 1:
        # Small models sometimes put both versions on one line: "Wie ...? How ...?"
        lines = [part.strip() for part in re.split(r"(?<=\?)\s+", lines[0]) if part.strip()]
    return lines[:2]


def query_versions(question: str, translate: bool) -> list[str]:
    versions = [question]
    if translate:
        for q in translate_query(question):
            if q.lower() not in {v.lower() for v in versions}:
                versions.append(q)
    return versions


# ---------------------------------------------------------------- corpus + BM25

STOPWORDS = set("""
der die das den dem des ein eine einer eines einem einen und oder aber in im ist sind
wie was wann wo wer ich du mich mir mein meine meinen kann darf muss soll für von zu zum
zur mit auf an am bei nach über aus als auch nicht wird werden es sie er wir ihr bis
the a an and or of to in on at for from is are be can do does how what when where who
i my me you your it this that with by as if than not
""".split())


@lru_cache(maxsize=1)
def _stemmer():
    import snowballstemmer
    return snowballstemmer.stemmer("german")


def tokenize(text: str) -> list[str]:
    """Lowercase words, drop stopwords, stem ('Prüfungen' and 'Prüfung' -> same token)."""
    words = [w for w in re.findall(r"\w+", text.lower()) if w not in STOPWORDS and len(w) > 1]
    return _stemmer().stemWords(words)


@lru_cache(maxsize=1)
def corpus() -> dict:
    """All chunks from Chroma, plus a BM25 index over them (built once per process)."""
    from rank_bm25 import BM25Okapi
    data = get_collection().get(include=["documents", "metadatas"])
    chunks = {cid: {"id": cid, "text": t, "source": m["source"], "page": m["page"]}
              for cid, t, m in zip(data["ids"], data["documents"], data["metadatas"])}
    ids = list(chunks)
    bm25 = BM25Okapi([tokenize(chunks[i]["text"]) for i in ids])
    return {"chunks": chunks, "ids": ids, "bm25": bm25}


# ---------------------------------------------------------------- search steps

def dense_search(query: str, n: int) -> list[tuple[str, float]]:
    result = get_collection().query(query_embeddings=[embed_query(query)], n_results=n,
                                    include=["distances"])
    return [(cid, 1 - d) for cid, d in zip(result["ids"][0], result["distances"][0])]


def bm25_search(query: str, n: int) -> list[tuple[str, float]]:
    c = corpus()
    scores = c["bm25"].get_scores(tokenize(query))
    best = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
    return [(c["ids"][i], float(scores[i])) for i in best if scores[i] > 0]


def rrf(ranked_lists: list[list[tuple[str, float]]], k: int = config.RRF_K) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: rank matters, raw scores don't (they aren't comparable)."""
    fused: dict[str, float] = {}
    for ranking in ranked_lists:
        for rank, (cid, _) in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


def rerank(question: str, candidates: list[str]) -> list[tuple[str, float]]:
    chunks = corpus()["chunks"]
    scores = get_reranker().predict([(question, chunks[cid]["text"]) for cid in candidates])
    return sorted(zip(candidates, map(float, scores)), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------- full pipeline

def retrieve(question: str, k: int = config.TOP_K, *, translate: bool | None = None,
             hybrid: bool | None = None, use_reranker: bool | None = None,
             versions: list[str] | None = None) -> list[dict]:
    """Return the top-k chunks as dicts: text, source, page, score.

    Options default to rag/config.py. `versions` lets you pass pre-computed question
    translations (the eval script caches them so experiments don't re-call the LLM).
    """
    translate = config.QUERY_TRANSLATION if translate is None else translate
    hybrid = config.HYBRID_SEARCH if hybrid is None else hybrid
    use_reranker = config.USE_RERANKER if use_reranker is None else use_reranker

    if versions is None:
        versions = query_versions(question, translate)
    elif not translate:
        versions = versions[:1]

    pool = max(config.RERANK_CANDIDATES, k)
    lists = []
    for q in versions:
        lists.append(dense_search(q, pool))
        if hybrid:
            lists.append(bm25_search(q, pool))
    ranked = lists[0] if len(lists) == 1 else rrf(lists)

    if use_reranker:
        ranked = rerank(question, [cid for cid, _ in ranked[:config.RERANK_CANDIDATES]])

    chunks = corpus()["chunks"]
    return [{**chunks[cid], "score": score} for cid, score in ranked[:k]]
