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
