"""Read every PDF in data/raw/, split it into chunks, embed them, store them in Chroma.

Run from the project root:
    python -m rag.ingest            # add/update chunks
    python -m rag.ingest --reset    # wipe the database first (do this after changing chunk settings)
"""

import argparse
import re
import time
from collections import Counter
from pathlib import Path

import pymupdf

from rag.config import CHUNK_WORDS, OVERLAP_WORDS, RAW_DIR, STRIP_HEADERS, embed_passages, get_collection


def clean(text: str) -> str:
    text = text.replace("­", "")         # soft hyphens (invisible, but break words)
    text = re.sub(r"-\n(\w)", r"\1", text)    # re-join words hyphenated across lines
    return re.sub(r"\s+", " ", text).strip()  # collapse newlines/spaces


def chunk_words(text: str, size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    """Split text into windows of `size` words; each window starts `size - overlap` words later."""
    words = text.split()
    if not words:
        return []
    step = size - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
    return chunks


def _line_key(line: str) -> str:
    """Normalise a line so 'Seite 28 von 54' and 'Seite 29 von 54' count as the same line."""
    return re.sub(r"\d+", "#", line.strip().lower())


def repeated_lines(pages: list[str]) -> set[str]:
    """Lines that appear on at least half of the pages (min. 3) = headers/footers/page numbers."""
    if len(pages) < 3:
        return set()
    counts = Counter()
    for text in pages:
        counts.update({_line_key(l) for l in text.splitlines() if l.strip()})
    threshold = max(3, len(pages) / 2)
    return {key for key, n in counts.items() if n >= threshold}


def strip_lines(text: str, drop: set[str]) -> str:
    return "\n".join(l for l in text.splitlines() if _line_key(l) not in drop)


def chunks_for_pdf(pdf_path: Path):
    """Yield (id, text, metadata) for every chunk of one PDF.

    Chunks never cross a page border. That keeps citations exact ("page 29"),
    but a rule that starts at the bottom of one page and ends on the next gets
    split in two.
    """
    with pymupdf.open(pdf_path) as doc:
        pages = [page.get_text() for page in doc]
    drop = repeated_lines(pages) if STRIP_HEADERS else set()
    for page_number, raw in enumerate(pages, start=1):
        text = clean(strip_lines(raw, drop))
        for i, chunk in enumerate(chunk_words(text)):
            chunk_id = f"{pdf_path.name}:p{page_number}:c{i}"
            yield chunk_id, chunk, {"source": pdf_path.name, "page": page_number}


def load_chunks():
    """Chunks of every PDF in data/raw/."""
    for pdf_path in sorted(RAW_DIR.glob("*.pdf")):
        yield from chunks_for_pdf(pdf_path)


def store(ids: list[str], texts: list[str], metas: list[dict], collection) -> None:
    embeddings = embed_passages(texts)
    batch = 1000  # Chroma limits how much you can add in one call
    for i in range(0, len(ids), batch):
        collection.upsert(  # upsert = insert, or overwrite if the id already exists
            ids=ids[i:i + batch],
            documents=texts[i:i + batch],
            embeddings=embeddings[i:i + batch],
            metadatas=metas[i:i + batch],
        )


def ingest_file(pdf_path: Path) -> int:
    """(Re-)index a single PDF, e.g. after an upload in the web app. Returns the number of chunks."""
    collection = get_collection()
    collection.delete(where={"source": pdf_path.name})  # drop old chunks if the file was indexed before
    rows = list(chunks_for_pdf(pdf_path))
    if rows:
        ids, texts, metas = (list(x) for x in zip(*rows))
        store(ids, texts, metas, collection)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete the collection first")
    args = parser.parse_args()

    start = time.perf_counter()
    ids, texts, metas = [], [], []
    for chunk_id, text, meta in load_chunks():
        ids.append(chunk_id)
        texts.append(text)
        metas.append(meta)

    if not ids:
        print(f"No PDFs found in {RAW_DIR}. Run scripts/download_jku_pdfs.py first.")
        return

    files = len({m["source"] for m in metas})
    print(f"{len(ids)} chunks from {files} PDFs. Embedding (first run downloads the model)...")
    collection = get_collection(reset=args.reset)
    store(ids, texts, metas, collection)

    print(f"Done: {collection.count()} chunks in the database ({time.perf_counter() - start:.1f}s).")


if __name__ == "__main__":
    main()
