# Review of answer eval 2026-11-13 22:00 (main set, 80 questions)

Answer model and judge: qwen2.5:7b. Because the judge is the same small model, I re-checked every non-"correct" verdict by hand.

## Numbers: judge vs. after manual check

| | Judge (7B) | After manual check |
|---|---|---|
| **Overall: correct answer or correct refusal** | 67/80 (84%) | **71/80 (89%)** |
| Answerable: correct | 57/70 (81%) | **61/70 (87%)** |
| Answerable: partial | 11 | 6 |
| Answerable: wrong | 1 | 2 |
| Answerable: wrongly refused | 1 | 1 |
| Unanswerable: correctly refused | 10/10 | 10/10 (5 by threshold, 5 by LLM) |
| Cites a correct page | 90% | 90% |
| Answer in the question's language | 86% | **97%** (the checker flagged short answers like "180 ECTS"; now fixed) |

Judge mistakes I corrected:
- **B1/B2** (library loan period): correct. The document gives no number, and the answer says exactly that. The judge didn't get the trick question.
- **I3** (grade calculation): correct. The judge's reason makes no sense (".5 instead of .5").
- **AI15** (master length "4 semesters"): fine for the question asked.
- **AI8**: judged "partial" but actually **wrong**, see below.

## Real problems (all on the answer side, not retrieval)
1. **Outdated document conflict (AI8).** The answer gave "9–26 September 2026", mixing the 2026 year with the 2025/26 dates from the Informatik guide. The correct dates (8–25 Sept 2026) were retrieved too.
   → Documents of different years contradict each other. The model needs to know which source is newer.
2. **Misreading (K4).** "Does the prerequisite check include the StEOP?" → "Yes". The text says the opposite. A negation error by the 7B model.
3. **Refused although the right page was #1 (S6).** English question, German rule text: the model didn't connect them.
4. **Incomplete lists/numbers (S12, S7, K3).** It gave the exam months as "Sept, Oct, Jan" (missing Nov/Dec/Feb), dropped "within 4 weeks", and dropped the 270-minute threshold.
5. **Mixing sources (A3).** It blended a Satzung rule into the course-deregistration answer.
6. **Language (S4, A4).** English questions answered by quoting German text.

## Speed
Retrieval 3.0 s + LLM 7.5 s per question (plus 2–4 s live translation). The retrieval-only eval ran at 0.9 s, so the reranker and the 7B model are
probably fighting over the 6 GB of graphics memory. That's too slow for a nice demo.

## Conclusion
Retrieval is solid. Almost all remaining errors come from the 7B answer model: reading mistakes, incomplete answers, mixing outdated sources.
The biggest lever now is the answer model, not the search.
