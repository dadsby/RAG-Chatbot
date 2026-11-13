"""Shared settings and helpers for ingest.py and ask.py.

Everything you might want to tweak in experiments lives here, so later you can
compare e.g. chunk sizes or embedding models by changing one line.
"""

from functools import lru_cache
from pathlib import Path

import chromadb

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CHROMA_DIR = ROOT / "chroma"
COLLECTION_NAME = "jku_docs"

# Embedding model: multilingual (German + English), small enough for a laptop.
# E5 models expect the prefixes "passage: " for documents and "query: " for questions.
# It reads at most 512 tokens per chunk, which is why chunks are ~300 words, not 500:
# German words often split into 2+ tokens, and anything past 512 would be cut off silently.
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"   # was e5-small (baseline)

# Chunking
CHUNK_WORDS = 300     # words per chunk
OVERLAP_WORDS = 50    # words shared between neighbouring chunks, so a sentence cut
                      # at a chunk border still appears whole in one of them

# Retrieval
TOP_K = 5             # how many chunks to give the LLM

# Query translation: before searching, let the LLM rewrite the question in German AND
# English, then search with all versions and merge. Targets the finding that English
# questions miss German documents. Costs one extra (short) LLM call per question.
QUERY_TRANSLATION = True


@lru_cache(maxsize=1)
def get_embedder():
    # Imported here because loading torch is slow; only pay for it when needed.
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_passages(texts: list[str]) -> list[list[float]]:
    vectors = get_embedder().encode(
        ["passage: " + t for t in texts],
        normalize_embeddings=True,   # unit length -> cosine similarity = dot product
        show_progress_bar=True,
        batch_size=32,
    )
    return vectors.tolist()


def embed_query(question: str) -> list[float]:
    vector = get_embedder().encode("query: " + question, normalize_embeddings=True)
    return vector.tolist()


def get_collection(reset: bool = False):
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass  # didn't exist yet
    return client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # compare vectors by angle, not raw distance
    )
