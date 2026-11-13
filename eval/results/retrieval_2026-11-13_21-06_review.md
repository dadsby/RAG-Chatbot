# Review of retrieval eval 2026-11-13 21:06 (40 rerank candidates)

Change vs 21:01: RERANK_CANDIDATES 20 → 40. (The 21:01 run accidentally still used 20, so it was a repeat of 20:58.
Bonus finding from that: identical top-5 for all 80 questions, so results are fully reproducible. And it ran at ~0.4 s/question with a warm GPU.)

| Config | Hit@1 | Hit@5 | MRR | Cross-lang Hit@5 | s/question |
|---|---|---|---|---|---|
| full, 20 candidates | 83% | 89% | 0.86 | 81% | 0.4 |
| full, 40 candidates | **84%** | **91%** | **0.87** | **85%** | 0.7 |
| hybrid+rerank, 20 | 79% | 87% | 0.82 | 69% | 0.4 |
| hybrid+rerank, 40 | 80% | 89% | 0.83 | 73% | 0.7 |

- full gained S6 and K1, lost nothing. Small (2 of 70 questions), but strictly positive, so keep 40.
- Cost: +0.3 s per question.
- Refusal signal unchanged (answerable median 0.89 vs unanswerable 0.02).

Remaining 6 misses:
- **Chunking:** S15 (small rule inside a big chunk), A3/A4 (rule at the top of anmeldeverordnung p. 6, heading on p. 5), S12.
- **English → German KUSSS sheets:** K2, K5 (English questions flooded by the English AI guide).

Next experiment: smaller chunks (300 → 150 words, overlap 50 → 30).
