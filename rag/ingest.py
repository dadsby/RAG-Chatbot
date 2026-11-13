"""Read every PDF in data/raw/, split it into chunks, embed them, store them in Chroma.

Run from the project root:
    python -m rag.ingest            # add/update chunks
    python -m rag.ingest --reset    # wipe the database first (do this after changing chunk settings)
"""

import argparse
import re
import time

import pymupdf

from rag.config import CHUNK_WORDS, OVERLAP_WORDS, RAW_DIR, embed_passages, get_collection


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


def load_chunks():
    """Yield (id, text, metadata) for every chunk of every PDF.

    Chunks never cross a page border. That keeps citations exact ("page 29"),
    but a rule that starts at the bottom of one page and ends on the next gets
    split in two. That's a trade-off worth testing later.
    """
    for pdf_path in sorted(RAW_DIR.glob("*.pdf")):
        with pymupdf.open(pdf_path) as doc:
            for page_number, page in enumerate(doc, start=1):
                text = clean(page.get_text())
                for i, chunk in enumerate(chunk_words(text)):
                    chunk_id = f"{pdf_path.name}:p{page_number}:c{i}"
                    yield chunk_id, chunk, {"source": pdf_path.name, "page": page_number}


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
    embeddings = embed_passages(texts)

    collection = get_collection(reset=args.reset)
    batch = 1000  # Chroma limits how much you can add in one call
    for i in range(0, len(ids), batch):
        collection.upsert(  # upsert = insert, or overwrite if the id already exists
            ids=ids[i:i + batch],
            documents=texts[i:i + batch],
            embeddings=embeddings[i:i + batch],
            metadatas=metas[i:i + batch],
        )

    print(f"Done: {collection.count()} chunks in the database ({time.perf_counter() - start:.1f}s).")


if __name__ == "__main__":
    main()
