# Review of retrieval eval 2026-11-13 15:21 (first automatic run, 80 questions)

## Headline (dense baseline → full pipeline)

| | dense | full (translate + hybrid + rerank) |
|---|---|---|
| Hit@1 (right page ranked first) | 53% | **83%** |
| Hit@5 (recall) | 73% | **89%** |
| MRR | 0.62 | **0.86** |
| Precision@5 | 0.22 | 0.29 |
| Cross-language Hit@5 | 46% | **81%** |
| Search time per question (CPU) | 0.1 s | **~17 s** |

## What each step did
- **Translation** fixes cross-language recall (46% → 77%) but barely moves Hit@1.
- **BM25 hybrid** alone doesn't help (73% → 73%). It only pays off together with translation (86%) and as a candidate source for the reranker.
- **Reranker** is the big precision win: Hit@1 47% → 83%, MRR 0.61 → 0.86. The right page goes from "somewhere in the top 5" to "first".
- **Without translation, hybrid+rerank is best on same-language questions (98%)** but drops on cross-language (69%). "full" is the best overall but loses A3 and K1: the translated versions crowd the 20-candidate pool. A bigger pool should fix this.

## Precision@5
It looks low, but most questions have exactly one relevant page, so 5 chunks can't all be relevant. Hit@1 = 83% is the more useful precision number.

## Refusing unanswerable questions
- The reranker's top score separates them well: median 0.89 for answerable questions vs 0.016 for unanswerable ones.
- 8/10 unanswerable questions score below 0.2. The exceptions are the two WiFi-password questions (0.88 / 0.82): the guides do talk about WiFi/eduroam, just not a password. Retrieval is right there, and the LLM has to refuse.
- The lowest-scoring answerable questions (S14, A4, S6, B2) are exactly the retrieval misses. So a low score also means "we didn't find it".
- A threshold around 0.01–0.02 → refuse without calling the LLM: faster and safer.

## Remaining misses (8, full config)
- **Cross-language into German rules/KUSSS sheets:** S6, S12, A4, K2, K5. English questions get flooded by the English AI guide.
- **Chunking:** S15 (the "foreign language" rule is a small section inside a chunk about ECTS/semester length) and A3/A4 (the course-deregistration rule sits at the top of anmeldeverordnung p. 6, its § heading is on p. 5).
- **K1:** KUSSS p. 5 is a very short page (mostly figure captions).

## Next steps (in order)
1. **Speed:** ~17 s per question on CPU is unusable. Run the reranker on the GPU (CUDA PyTorch, fp16) or switch to the smaller reranker, then re-measure.
2. Raise RERANK_CANDIDATES 20 → 40 (fixes the A3/K1 drop in "full"); only affordable once step 1 is done.
3. Refusal threshold on the reranker score.
4. Chunking: carry section headings into chunks / allow chunks across page borders.

Caveat: 80 questions labelled by hand, so a difference of ±5 points between configs can be noise.
