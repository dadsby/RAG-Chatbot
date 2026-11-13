# Review of retrieval eval 2026-11-13 21:10 (150-word chunks)

Change vs 21:06: CHUNK_WORDS 300 → 150, OVERLAP 50 → 30 (re-ingested). Everything else the same (40 rerank candidates).

| full | 300 words | 150 words |
|---|---|---|
| Hit@1 | 84% | 84% |
| Hit@5 (recall) | 91% | **96%** |
| MRR | 0.87 | **0.89** |
| Precision@5 | 0.30 | **0.38** |
| Same-language Hit@5 | 95% | **100%** |
| Cross-language Hit@5 | 85% | **88%** |
| s/question | 0.7 | 0.5 |

- Gained S12, S15, A3 (the chunking misses), lost nothing in recall. Hit@1 stays the same: gained S15, A1, A2, lost S7, B2, C2.
- Every German question and every same-language question now finds the right page in the top 5.
- Faster, because the reranker reads shorter texts.
- Refusal signal still clear: answerable median 0.93 vs unanswerable 0.02. The WiFi-password questions stay high (0.93 / 0.85), as expected.

Remaining 3 misses are all English questions about German documents (A4, K2, K5). The reranker scored them with the English question only and preferred English chunks from the AI guide.

Next experiment: rerank with all question versions (original + German + English translation), keep the best score (RERANK_ALL_VERSIONS).
