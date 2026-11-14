# RAG Document Assistant

Ask questions about PDF documents and get answers that cite the exact file and page, or a clear "the documents don't contain this" when they don't.

Demo and test data: public JKU Linz study documents (exam rules, KUSSS guides, study guides), in German and English.

> Work in progress. Evaluation results will go here.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # then edit .env (see comments inside)

python scripts/download_jku_pdfs.py   # get the documents into data/raw/
python -m rag.ingest                  # chunk, embed and store them in Chroma
python -m rag.ask "Wie oft darf ich eine Prüfung wiederholen?"   # command line
python -m uvicorn api.main:app --port 8000                      # web app: open http://localhost:8000
```

## Web app

`api/main.py` (FastAPI) serves a small web interface from `web/` (plain HTML/CSS/JS, no build step):

- **Library:** all indexed PDFs; drop in a new PDF and it's indexed on the spot
- **Chat:** ask in German or English; answers show clickable citation pills
- **Source panel:** the exact passage behind a citation, with a button that opens the PDF at that page
- **Transparency:** retrieved passages with reranker scores, search and answer time, refusals marked as such
- Light and dark mode, keyboard friendly, works on mobile

The interface is available in English and German (switch in the top bar; the first visit follows the browser language). Answers follow the language of the question.

### Opening it on other devices

- **Same Wi-Fi:** `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`, then open `http://<your-PC's-IP>:8000` on the other device (find the IP with `ipconfig`). Allow Python through the Windows firewall for *private* networks. University Wi-Fi often blocks device-to-device traffic, so use a home network or a phone hotspot.
- **Over the internet (temporary link):** run the app normally, then `cloudflared tunnel --url http://localhost:8000` prints a public `https://….trycloudflare.com` link that works while both are running.
- **Always set `APP_PASSWORD` in `.env` first.** Otherwise anyone with the link can upload files and use your GPU.

API endpoints: `GET /api/health`, `GET /api/documents`, `POST /api/documents` (upload), `GET /api/documents/{name}/file`, `POST /api/ask`.

## How it works

1. **Query translation**: the LLM rewrites the question in German and English (the documents are mixed).
2. **Hybrid search**: vector search (multilingual-e5-base) + BM25 keyword search, for every question version, merged with Reciprocal Rank Fusion.
3. **Reranking**: a multilingual cross-encoder (bge-reranker-v2-m3) re-scores the best 40 candidates against every question version.
4. **Early refusal**: if even the best chunk scores below a threshold, the answer is "not in the documents" and the LLM isn't called at all.
5. **Answer**: the top 5 chunks (150 words each) go to the LLM, which must answer only from them, in the question's language, and cite `[file, p. X]`.

Every step can be switched on/off in `rag/config.py`.

## Evaluation

- `eval/eval_set.json`: 80 hand-labelled questions (German + English, 26 cross-language, 10 unanswerable) with the file and page(s) that contain the answer. Used while tuning.
- `eval/heldout_set.json`: 20 new questions that were **not** used for tuning, for an honest final number.

```bash
python -m eval.run_retrieval                         # retrieval: recall, MRR, precision per setup
python -m eval.run_retrieval --set heldout --configs full
python -m eval.run_answers --set heldout             # answers: correct/partial/wrong (LLM judge), faithfulness,
python -m eval.run_answers                           #   citations, language, refusals, latency
python -m eval.run_manual                            # 20 full answers for reading by hand
```

Reports land in `eval/results/`.
