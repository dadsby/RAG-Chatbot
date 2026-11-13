# Manual test questions (first round)

For each one, run `python -m rag.ask "<question>" --show-context` and note:
did it retrieve the right page? Is the answer correct? Is the citation right?

These are the seed of the real eval set (Phase 3), so keep your notes.

| # | Question | Expected answer | Where it is | Retrieved right page? | Answer correct? | Notes |
|---|----------|-----------------|-------------|----|----|----|
| 1 | Wie oft darf ich eine negativ beurteilte Prüfung wiederholen? | 4 times. StEOP exams only 3 times. The last exam of the degree gets one extra try | satzung_studienrecht_2026.pdf, p. 29 (section starts p. 28) | | | Rule is split across a page break, a good test of page-based chunking |
| 2 | Darf ich eine positive Prüfung wiederholen, um die Note zu verbessern? | Yes, once, within the legal deadline. The old positive grade becomes void as soon as you take the retake | satzung_studienrecht_2026.pdf, p. 28–29 | | | |
| 3 | What is the StEOP and how do I complete it? | Introductory phase for first-semester students. Done once you have at least 9 ECTS from the core StEOP pool. Max 21 extra ECTS from the auxiliary table meanwhile | Bachelor_AI_Studienleitfaden.pdf, p. 29 | | | English doc, English question |
| 4 | Was kostet das Parkticket für Studierende? | €195 per semester (visitors €1.60 per started half hour) | parkordnung_kostenblatt_2026.pdf, p. 1 | | | Table-style layout |
| 5 | Darf ich meinen Hund mit auf den Campus nehmen? | No, except guide dogs and partner dogs (medical confirmation needed) | hausordnung_2026.pdf, p. 8 | | | |
| 6 | How long is the AI master's and what language is it taught in? | 4 semesters, 120 ECTS, English (B2) | flyer_master_ai.pdf, p. 3 | | | |
| 7 | Bis wann muss ich mich von einer Lehrveranstaltung abmelden? | Before the first session (or by waiving at the first session). The curriculum can set a later deadline | anmeldeverordnung.pdf, p. 6 | | | |
| 8 | Wie lange darf ich ein Buch aus der Bibliothek ausleihen? | **Trick question:** the document says loan periods are set separately and published online. It does NOT give a number. Extension is possible if nobody reserved the book | benuetzungsordnung_bibliothek.pdf, p. 5 | | | Should NOT invent "4 weeks" |
| 9 | Who won the Champions League in 2026? | Should say the documents don't contain this | — | | | Off-topic |
| 10 | Wie lautet das WLAN-Passwort der JKU? | Should say the documents don't contain this (the guides may explain eduroam login, but there's no password) | — | | | Plausible but not answerable |

Cross-language bonus: ask #3 in German ("Was ist die StEOP?") and #1 in English. Does retrieval still find the right page?

## English questions

### English question → English document (should be easy)

| # | Question | Expected answer | Where it is | Right page? | Correct? | Notes |
|---|----------|-----------------|-------------|----|----|----|
| E1 | How many ECTS of free electives do I need in the AI bachelor, and where can I take them? | 9 ECTS, any course at JKU or any other EU university | Bachelor_AI_Studienleitfaden.pdf, p. 34 | | | |
| E2 | How do I find a topic for my bachelor thesis? | Thesis is supervised by an institute. Check institute websites or ask lecturers, you can propose your own topic, external (e.g. at a company) is possible but needs an institute to supervise. Also the ÖH thesis exchange | Bachelor_AI_Studienleitfaden.pdf, p. 17 | | | |
| E3 | How do I sign up for the AI mentoring program? | Mentors introduce themselves in the first lesson of KV Current Topics in AI. Then join your mentor's group on that course's Moodle page. No joining after the deadline | Bachelor_AI_Studienleitfaden.pdf, p. 30 | | | |

### English question → German document (cross-language, the interesting part)

| # | Question | Expected answer | Where it is | Right page? | Correct? | Notes |
|---|----------|-----------------|-------------|----|----|----|
| E4 | How many times can I retake a failed exam? | 4 times. StEOP exams only 3. Last exam of the degree gets one extra try | satzung_studienrecht_2026.pdf, p. 29 | | | Compare with the German version's scores |
| E5 | How much does student parking cost per semester? | €195 per semester | parkordnung_kostenblatt_2026.pdf, p. 1 | | | |
| E6 | Can I bring my dog to campus? | No, except guide dogs and partner dogs (medical confirmation needed) | hausordnung_2026.pdf, p. 8 | | | |
| E7 | Until when can I deregister from a course? | Before the first session (or by waiving at the first session). The curriculum can set a later deadline | anmeldeverordnung.pdf, p. 6 | | | |
| E8 | How long can I borrow a library book? | **Trick:** no number in the docs. Loan periods are published separately online. Extension possible if nobody reserved it | benuetzungsordnung_bibliothek.pdf, p. 5 | | | Must NOT invent a number |

### Not answerable

| # | Question | Expected answer | Right? | Notes |
|---|----------|-----------------|----|----|
| E9 | What is the JKU WiFi password? | Documents don't contain this | | |
| E10 | Who won the Champions League in 2026? | Documents don't contain this | | |
