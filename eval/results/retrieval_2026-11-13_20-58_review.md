# Review of retrieval eval 2026-11-13 20:58 (reranker on GPU)

Change vs 15:21: PyTorch with CUDA (RTX 4050), reranker in half precision (fp16). Nothing else changed.

| Config | Hit@1 | Hit@5 | MRR | s/question before (CPU) | s/question now (GPU) |
|---|---|---|---|---|---|
| hybrid+rerank | 79% | 87% | 0.82 | ~30 | **1.3** |
| full | 83% | 89% | 0.86 | ~17 | **1.25** |

- ~13x faster with identical quality: fp16 cost no accuracy at all.
- The live app still adds ~2-4 s for the translation call, so ~4-5 s total search time per question.
- Same 8 misses as before.

Next: RERANK_CANDIDATES 20 → 40 (now affordable), to win back A3/K1, which "full" loses to "hybrid+rerank".
