# Answer eval 2026-11-13 21:37 (heldout set, 20 questions)

Answer model: qwen2.5:7b | judge: qwen2.5:7b | refusal threshold: 0.024 | chunks: 150 words | rerank candidates: 40

## Summary

| Metric | Value |
|---|---|
| **Overall: correct answer or correct refusal** | **18/20 (90%)** |
| Answerable: correct | 14/16 (88%) |
| Answerable: partial | 1/16 (6%) |
| Answerable: wrong | 0/16 (0%) |
| Answerable: wrongly refused | 1/16 (threshold 0, LLM 1) |
| Faithful (no outside knowledge), of answered | 93% |
| Has a citation, of answered | 100% |
| Cites a correct (gold) page, of answered | 80% |
| Cites only retrieved pages, of answered | 100% |
| Answer in the question's language | 87% |
| Unanswerable: correctly refused | 4/4 (threshold 0, LLM 4) |
| Avg retrieval time | 3.2 s |
| Avg LLM time (when called) | 9.1 s |
| LLM calls saved by the refusal threshold | 0/20 |

## Per question

| ID | Verdict | Faithful | Cites gold | Lang | Refused | Answer |
|---|---|---|---|---|---|---|
| HO1 | ✅ correct | yes | yes | ok | – | Minimum three years [satzung_studienrecht_2026.pdf, p. 40] |
| HO2 | ✅ correct | yes | yes | ok | – | If the exam senate cannot reach a decision on the evaluation of a subject, but the majority of the proposed evaluations by the members are p… |
| HO3 | ✅ correct | yes | yes | WRONG | – | 2 [anmeldeverordnung.pdf, p. 2] |
| HO4 | ❌ refused | – | – | ok | llm | The documents don't contain an answer to this question. |
| HO5 | ✅ correct | yes | yes | ok | – | No, the regular building opening hours do not apply to Schloss Auhof. [hausordnung_2026.pdf, p. 4] |
| HO6 | ✅ correct | yes | no | ok | – | Nein, das Radfahren im Parkhaus und in der Tiefgarage ist verboten. Das Befahren des Universitätsgeländes mit Ausnahme der notwendigen Zuste… |
| HO7 | ✅ correct | yes | yes | ok | – | Yes, you have to pay for parking on weekends and public holidays. [parkordnung_2026.pdf, p. 4] |
| HO8 | ✅ correct | yes | yes | WRONG | – | € 8,50 [parkordnung_kostenblatt_2026.pdf, p. 1] |
| HO9 | ✅ correct | yes | yes | ok | – | Nein, das ist verboten. Die Tasche muss während des Aufenthalts in den Bibliotheksräumen in den verschließbaren Garderobenschränken oder in … |
| HO10 | ✅ correct | yes | yes | ok | – | More than EUR 20,- [benuetzungsordnung_bibliothek.pdf, p. 6] |
| HO11 | ✅ correct | yes | yes | ok | – | Die Anmeldfrist zur Prüfung läuft. [kusss_lva_pruefungsanmeldung.pdf, p. 2] |
| HO12 | ✅ correct | yes | yes | ok | – | tnf@oeh.jku.at [Leitfaden_Bachelorstudium_Informatik.pdf, p. 8] |
| HO13 | 🟡 partial | no | yes | ok | – | Nein, es gibt keinen spezifischen Python-Vorbereitungskurs für AI-Studierende. Es wird jedoch ein "Praktische Programmierkenntnisse (Java) u… |
| HO14 | ✅ correct | yes | yes | ok | – | The Bachelor Info Evening takes place in January and is an online event via Zoom where institutes introduce themselves and their work. The S… |
| HO15 | ✅ correct | yes | no | ok | – | Das Institut Integriert Studieren (IIS) unterstützt Studierende mit Behinderungen, chronischen Krankheiten und Neurodiversität, zum Beispiel… |
| HO16 | ✅ correct | yes | no | ok | – | Vienna and Bregenz [flyer_master_ai.pdf, p. 2] |
| HU1 | ✅ refused | – | – | ok | llm | Die Dokumente enthalten keine Antwort auf diese Frage. |
| HU2 | ✅ refused | – | – | ok | llm | The documents don't contain an answer to this question. |
| HU3 | ✅ refused | – | – | ok | llm | Die Dokumente enthalten keine Antwort auf diese Frage. |
| HU4 | ✅ refused | – | – | ok | llm | The documents don't contain an answer to this question. |

## Problems to look at

- **HO4** What results can my course registration have after the allocation?  
  answer: The documents don't contain an answer to this question.  
  judge: None, faithful=None —   
  top score 0.127; retrieved: Bachelor_AI_Studienleitfaden.pdf p15; Bachelor_AI_Studienleitfaden.pdf p13; Leitfaden_Bachelorstudium_Informatik.pdf p14; anmeldeverordnung.pdf p5; satzung_studienrecht_2026.pdf p13
- **HO13** Gibt es einen Python-Vorbereitungskurs für AI-Studierende?  
  answer: Nein, es gibt keinen spezifischen Python-Vorbereitungskurs für AI-Studierende. Es wird jedoch ein "Praktische Programmierkenntnisse (Java) und Python Programming (speziell für AI)" angeboten. [Leitfaden_Bachelorstudium_Informatik.pdf, p. 20]  
  judge: partial, faithful=False — The answer is partially correct as it mentions the relevant Python course, but it incorrectly states that there is no specific Python preparation course for AI students. It also contradicts the reference answer which states 'Ja, Python Programming for Artificial Intelligence'.  
  top score 0.918; retrieved: Leitfaden_Bachelorstudium_Informatik.pdf p20; Leitfaden_Bachelorstudium_Informatik.pdf p20; Bachelor_AI_Studienleitfaden.pdf p20; Bachelor_AI_Studienleitfaden.pdf p30; Bachelor_AI_Studienleitfaden.pdf p33
