# Review of held-out retrieval eval 2026-11-13 21:27

20 new questions, never used for tuning. Final config ("full").

| | Tuning set (80) | Held-out (20) |
|---|---|---|
| Hit@1 | 90% | **88%** |
| Hit@5 (recall) | 99% | **94%** (15/16) |
| MRR | 0.93 | **0.91** |
| Precision@5 | 0.39 | 0.38 |
| Same-language Hit@5 | 100% | 100% |
| Cross-language Hit@5 | 96% | 83% (5/6) |

**The tuning generalises.** Held-out numbers are only a few points below the tuning set, which is the normal "optimism gap".
Hit@1 88% / Hit@5 94% are the honest numbers for the README (small sample: 16 questions, so roughly ±10 points).

Only miss: HO4 (English question about the Anmeldeverordnung). That's the same document and pattern as A4 in the main set:
English questions about the German Anmeldeverordnung are the system's weak spot.

## Refusal threshold: important finding
Top reranker scores of the 4 unanswerable held-out questions: 0.954 (WS 2027/28 start), 0.755 (childcare), 0.131 (Linz AG ticket), 0.055 (lecture hall seats).
The threshold 0.024 would refuse **none** of them early.

- The threshold catches **off-topic** questions (Champions League, weather: scores ~0.001).
- It can't catch **on-topic questions whose specific detail is missing**: the AI guide has WS 2026/27 dates but not 2027/28, and "Betreuung" in the Satzung means thesis supervision, not childcare.
- So the threshold is a cheap first filter. The LLM still has to do the real refusing. The answer eval measures whether it does.
- Good news: no answerable held-out question scored below 0.024 (lowest 0.044), so the threshold causes no false refusals.
