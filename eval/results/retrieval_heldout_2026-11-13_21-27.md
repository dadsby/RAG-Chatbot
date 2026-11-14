# Retrieval eval 2026-11-13 21:27 (heldout set)

20 questions (16 answerable). Embedding: intfloat/multilingual-e5-base, reranker: BAAI/bge-reranker-v2-m3, chunks: 150 words, header stripping: True, k=5.

## Overall (answerable questions)

| Config | Hit@1 | Hit@5 (recall) | MRR | Precision@5 | ms/question* |
|---|---|---|---|---|---|
| full | 88% | 94% | 0.91 | 0.38 | 1755 |

*Search only; translation is cached here. In the live app add ~2-4 s per question for the translation call.

## Hit@5 by language (question → documents)

| Config | same language | cross-language | German questions | English questions |
|---|---|---|---|---|
| full | 100% (10) | 83% (6) | 100% (7) | 89% (9) |

## Can the reranker score detect unanswerable questions?

- **full**: top score answerable: median 0.918 (min 0.044) | unanswerable: median 0.755 (max 0.954) | best threshold 0.044 -> 80% correct answer/refuse decisions

## Misses of the best config (full)

- **HO4** What results can my course registration have after the allocation?  
  gold: anmeldeverordnung.pdf p4  
  got: Bachelor_AI_Studienleitfaden.pdf p15; Bachelor_AI_Studienleitfaden.pdf p13; Leitfaden_Bachelorstudium_Informatik.pdf p14; anmeldeverordnung.pdf p5; satzung_studienrecht_2026.pdf p13
