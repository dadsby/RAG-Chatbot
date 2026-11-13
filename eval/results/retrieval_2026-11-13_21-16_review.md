# Review of retrieval eval 2026-11-13 21:16 (rerank with all question versions)

Change vs 21:10: RERANK_ALL_VERSIONS = True. The reranker scores every candidate against the original question
AND its German/English translations and keeps the best score.

| full | before | after |
|---|---|---|
| Hit@1 | 84% | **90%** |
| Hit@5 (recall) | 96% | **99%** (69/70) |
| MRR | 0.89 | **0.93** |
| Precision@5 | 0.38 | 0.39 |
| Cross-language Hit@5 | 88% | **96%** |
| Correct answer/refuse decisions (threshold) | 92% | **94%** |
| s/question (search only) | 0.5 | 0.9 |

- Gained K2, K5 (top 5) and S12, B2, K2, K5 (rank 1). Lost nothing.
- Cost: reranker does ~3x the work → +0.4 s.
- One miss left: A4 (English question about course deregistration). It still lands on exam deregistration.

## Caveat: we tuned on the test set
All settings (chunk size, candidates, rerank mode) were picked by looking at these same 80 questions,
so the numbers are probably a bit optimistic. To report them honestly, write ~20 NEW questions
(not looked at during tuning) and run them once as a held-out check.
