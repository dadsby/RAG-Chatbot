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
python -m rag.ask "Wie oft darf ich eine Prüfung wiederholen?"
```

## How retrieval works

1. **Query translation**: the LLM rewrites the question in German and English (the documents are mixed).
2. **Hybrid search**: vector search (multilingual-e5-base) + BM25 keyword search, for every question version, merged with Reciprocal Rank Fusion.
3. **Reranking**: a multilingual cross-encoder (bge-reranker-v2-m3) re-sorts the best 20 candidates.
4. The top 5 chunks go to the LLM, which must answer only from them and cite `[file, p. X]`.

Every step can be switched on/off in `rag/config.py`.

## Evaluation

`eval/eval_set.json`: 80 hand-labelled questions (German + English, 26 cross-language, 10 unanswerable), each with the file and page(s) that contain the answer.

```bash
python -m eval.run_retrieval     # recall, MRR, precision for each retrieval setup -> eval/results/
python -m eval.run_manual        # full answers for a quick manual check
```
