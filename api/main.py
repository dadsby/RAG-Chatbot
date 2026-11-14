"""Web API + interface for the document assistant.

Run from the project root (with the venv active):
    python -m uvicorn api.main:app --port 8000                  # only this PC: http://localhost:8000
    python -m uvicorn api.main:app --host 0.0.0.0 --port 8000   # other devices in the same Wi-Fi too
Set APP_PASSWORD in .env before letting other people in.

Endpoints
    GET  /api/health                  status, number of chunks, models in use
    GET  /api/documents               indexed PDFs (name, pages, chunks, size)
    POST /api/documents               upload a PDF (multipart field "file"), indexes it right away
    GET  /api/documents/{name}/file   the PDF itself (the UI opens it at the cited page)
    POST /api/ask                     {"question": "..."} -> answer, sources, timings
"""

import base64
import csv
import os
import re
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pymupdf
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from rag import config
from rag.answer import answer_question
from rag.config import RAW_DIR, ROOT, get_embedder, get_reranker
from rag.ingest import ingest_file
from rag.llm import model_name
from rag.retrieval import corpus

WEB_DIR = ROOT / "web"
MAX_UPLOAD_MB = 50
CITATION = re.compile(r"\[([^\[\],]+?\.pdf),\s*(?:p\.|S\.|page)\s*(\d+)\]", re.IGNORECASE)

# The models and Chroma aren't built for many requests at once; one at a time is plenty for a demo.
_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(ROOT / ".env")
    get_embedder()          # load models once at startup, not on the first question
    if config.USE_RERANKER:
        get_reranker()
    corpus()
    # Warm-up: one full question so GPU kernels, the reranker and the LLM are loaded before
    # the first real user asks. Otherwise the first answer takes 3-4x longer.
    print("Warming up (one test question)...")
    try:
        t0 = time.perf_counter()
        answer_question("Wie oft darf ich eine Prüfung wiederholen?")
        print(f"Ready after warm-up ({time.perf_counter() - t0:.1f} s). Open http://localhost:8000")
    except Exception as exc:  # e.g. Ollama not running: start anyway, the UI will show the error
        print(f"Warm-up failed ({exc}). Starting anyway.")
    yield


app = FastAPI(title="RAG Document Assistant", lifespan=lifespan)


@app.middleware("http")
async def password_gate(request: Request, call_next):
    """If APP_PASSWORD is set in .env, the browser asks for it (any user name works).

    Use it whenever other people can reach the app, e.g. through a tunnel: otherwise anyone
    with the link can upload files and use your laptop's GPU.
    """
    password = os.environ.get("APP_PASSWORD")
    if password:
        auth = request.headers.get("authorization", "")
        ok = False
        if auth.lower().startswith("basic "):
            try:
                _, _, given = base64.b64decode(auth[6:]).decode("utf-8").partition(":")
                ok = secrets.compare_digest(given, password)
            except Exception:
                ok = False
        if not ok:
            return Response("Password required", status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Fundstelle"'})
    return await call_next(request)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


def titles() -> dict[str, str]:
    """Nice document titles from data/sources.csv (if present). Uploaded files fall back to the file name."""
    path = ROOT / "data" / "sources.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {row["filename"]: row["title"] for row in csv.DictReader(f) if row.get("title")}


def safe_pdf_path(name: str) -> Path:
    """Only plain file names inside data/raw/, so nobody can request ../../something."""
    if not name.lower().endswith(".pdf") or Path(name).name != name:
        raise HTTPException(400, "Invalid file name")
    path = RAW_DIR / name
    if not path.is_file():
        raise HTTPException(404, "Document not found")
    return path


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "chunks": len(corpus()["ids"]),
        "documents": len(list(RAW_DIR.glob("*.pdf"))),
        "embedding_model": config.EMBEDDING_MODEL,
        "reranker": config.RERANKER_MODEL if config.USE_RERANKER else None,
        "llm": model_name("answer"),
        "translation": config.QUERY_TRANSLATION,
    }


@app.get("/api/documents")
def list_documents():
    chunk_counts: dict[str, int] = {}
    for chunk in corpus()["chunks"].values():
        chunk_counts[chunk["source"]] = chunk_counts.get(chunk["source"], 0) + 1
    docs = []
    names = titles()
    for path in sorted(RAW_DIR.glob("*.pdf"), key=lambda p: names.get(p.name, p.name).lower()):
        try:
            with pymupdf.open(path) as pdf:
                pages = pdf.page_count
        except Exception:
            pages = None
        docs.append({"name": path.name, "title": names.get(path.name), "pages": pages, "chunks": chunk_counts.get(path.name, 0),
                     "size_kb": round(path.stat().st_size / 1024)})
    return {"documents": docs}


@app.post("/api/documents")
def upload_document(file: UploadFile = File(...)):
    name = Path(file.filename or "").name
    name = re.sub(r"[^\w.\- ]", "_", name).strip()
    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    data = file.file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {MAX_UPLOAD_MB} MB")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "This file doesn't look like a PDF")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / name
    path.write_bytes(data)
    t0 = time.perf_counter()
    with _lock:
        try:
            chunks = ingest_file(path)
        except Exception as exc:
            path.unlink(missing_ok=True)
            raise HTTPException(422, f"Couldn't read this PDF: {exc}") from exc
        corpus.cache_clear()  # rebuild the BM25 index so the new chunks are searchable
        corpus()
    if chunks == 0:
        return {"name": name, "chunks": 0, "seconds": round(time.perf_counter() - t0, 1),
                "warning": "No text found. It may be a scanned PDF."}
    return {"name": name, "chunks": chunks, "seconds": round(time.perf_counter() - t0, 1)}


@app.get("/api/documents/{name}/file")
def get_document_file(name: str):
    return FileResponse(safe_pdf_path(name), media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{name}"'})


@app.post("/api/ask")
def ask(req: AskRequest):
    question = req.question.strip()
    with _lock:
        r = answer_question(question)
    cited = [{"source": f.strip(), "page": int(p)} for f, p in CITATION.findall(r["answer"])]
    usage = r["usage"]
    return {
        "question": question,
        "answer": r["answer"],
        "refused": r["refused"],
        "refused_by": r["refused_by"],
        "language": r["lang"],
        "top_score": round(r["top_score"], 4),
        "citations": cited,
        "sources": [{"source": h["source"], "page": h["page"], "score": round(h["score"], 4),
                     "text": h["text"]} for h in r["hits"]],
        "timing": {"retrieval_ms": round(r["retrieval_ms"]), "llm_ms": round(r["llm_ms"]),
                   **{k: round(v) for k, v in r["steps_ms"].items()}},
        "tokens": {"prompt": getattr(usage, "prompt_tokens", None),
                   "completion": getattr(usage, "completion_tokens", None)},
    }


# The web interface (index.html, app.js, styles.css). Mounted last so /api/* wins.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
