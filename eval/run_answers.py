"""Automatic answer evaluation: is the final answer correct, grounded, cited, in the right language,
and does the system refuse when it should?

Run from the project root:
    python -m eval.run_answers                    # 80-question main set (~10-15 min)
    python -m eval.run_answers --set heldout      # 20 held-out questions (~3-4 min)
    python -m eval.run_answers --limit 10         # quick smoke test
    python -m eval.run_answers --no-judge         # only the automatic checks, no LLM grading

How each answer is checked:
  Automatic (no LLM):  refused or not, citations present, cited page is a gold page,
                       cited pages were actually retrieved, answer language = question language
  LLM judge:           correct / partial / wrong compared to the expected answer, and
                       "faithful" = every claim is backed by the retrieved text (no outside knowledge)

The judge uses JUDGE_* settings from .env if present, otherwise the same LLM as the answers.
A 7B model grading itself is a weak judge: spot-check its verdicts, and if you can, set a
stronger JUDGE_MODEL (e.g. via an API) for the numbers you put in the README.
"""

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from statistics import mean

from dotenv import load_dotenv

from rag import config
from rag.answer import answer_question, build_context, detect_language
from rag.config import ROOT, get_embedder, get_reranker
from rag.llm import chat, model_name

from eval.common import SETS, load_set, load_translations

CITATION = re.compile(r"\[([^\[\],]+?\.pdf),\s*(?:p\.|S\.|page)\s*(\d+)\]", re.IGNORECASE)

JUDGE_PROMPT = """You grade answers of a document question-answering system.

You get: the question, a reference answer written by a human, the context passages the system
retrieved, and the system's answer.

Return ONLY a JSON object, no other text:
{"correctness": "correct" | "partial" | "wrong", "faithful": true | false, "reason": "<one short sentence>"}

correctness (compare with the reference answer):
- "correct": contains the key facts of the reference and nothing that contradicts it
- "partial": some key facts are right but important ones are missing or vague
- "wrong":   contradicts the reference or misses the point
faithful:
- true if every factual claim in the answer is supported by the context passages
- false if the answer states anything that is not in the context (outside knowledge counts as false)
Ignore citation formatting and language/style."""


def judge(question: str, reference: str, context: str, answer: str) -> dict:
    user = (f"Question: {question}\n\nReference answer: {reference}\n\n"
            f"Context passages:\n{context}\n\nSystem answer: {answer}")
    reply, _ = chat(JUDGE_PROMPT, user, role="judge")
    match = re.search(r"\{.*\}", reply, re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    verdict = str(data.get("correctness", "")).lower()
    if verdict not in {"correct", "partial", "wrong"}:
        verdict = "unparsed"
    faithful = data.get("faithful")
    if isinstance(faithful, str):
        faithful = faithful.strip().lower() == "true"
    return {"correctness": verdict, "faithful": faithful if isinstance(faithful, bool) else None,
            "reason": str(data.get("reason", reply[:200]))}


def check(q: dict, r: dict, use_judge: bool) -> dict:
    cited = {(f.strip(), int(p)) for f, p in CITATION.findall(r["answer"])}
    retrieved = {(h["source"], h["page"]) for h in r["hits"]}
    gold = {(f, p) for f, pages in q["gold"].items() for p in pages}
    answer_wo_cites = CITATION.sub("", r["answer"])
    row = {
        "id": q["id"], "question": q["question"], "lang": q["lang"], "answerable": q["answerable"],
        "answer": r["answer"], "refused": r["refused"], "refused_by": r["refused_by"],
        "top_score": r["top_score"], "retrieval_ms": r["retrieval_ms"], "llm_ms": r["llm_ms"],
        "prompt_tokens": getattr(r["usage"], "prompt_tokens", None),
        "completion_tokens": getattr(r["usage"], "completion_tokens", None),
        "retrieved": [f"{s} p{p}" for s, p in [(h["source"], h["page"]) for h in r["hits"]]],
        "has_citation": bool(cited),
        "cites_gold": bool(cited & gold),
        "cites_only_retrieved": bool(cited) and cited <= retrieved,
        # None = answer too short to tell (e.g. "180 ECTS"), counted as fine
        "language_ok": r["refused"] or detect_language(answer_wo_cites, default=None) in (None, q["lang"]),
        "correctness": None, "faithful": None, "reason": "",
    }
    if q["answerable"] and not r["refused"] and use_judge:
        row.update(judge(q["question"], q["expected_answer"], build_context(r["hits"]), r["answer"]))
    return row


def pct(rows, key) -> str:
    vals = [bool(r[key]) for r in rows if r[key] is not None]
    return f"{mean(vals):.0%}" if vals else "-"


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", default="main", choices=list(SETS))
    parser.add_argument("--limit", type=int, default=None, help="only the first N questions")
    parser.add_argument("--no-judge", action="store_true", help="skip the LLM judge")
    args = parser.parse_args()

    questions = load_set(args.set)[:args.limit]
    get_embedder()
    if config.USE_RERANKER:
        get_reranker()
    translations = load_translations(questions)

    rows = []
    for i, q in enumerate(questions, 1):
        print(f"[{i}/{len(questions)}] {q['id']} {q['question']}")
        r = answer_question(q["question"], versions=translations[q["question"]])
        rows.append(check(q, r, use_judge=not args.no_judge))

    ans = [r for r in rows if r["answerable"]]
    answered = [r for r in ans if not r["refused"]]
    una = [r for r in rows if not r["answerable"]]
    verdicts = Counter(r["correctness"] for r in answered)
    n_ans = len(ans) or 1
    correct_total = verdicts["correct"] + sum(r["refused"] for r in una)

    out = [f"# Answer eval {datetime.now():%Y-%m-%d %H:%M} ({args.set} set, {len(rows)} questions)\n",
           f"Answer model: {model_name('answer')} | judge: {'off' if args.no_judge else model_name('judge')} | "
           f"refusal threshold: {config.REFUSAL_THRESHOLD} | chunks: {config.CHUNK_WORDS} words | "
           f"rerank candidates: {config.RERANK_CANDIDATES}\n",
           "## Summary\n",
           "| Metric | Value |", "|---|---|",
           f"| **Overall: correct answer or correct refusal** | **{correct_total}/{len(rows)} "
           f"({correct_total / max(len(rows), 1):.0%})** |" if not args.no_judge else "| Overall | (judge off) |",
           f"| Answerable: correct | {verdicts['correct']}/{len(ans)} ({verdicts['correct'] / n_ans:.0%}) |",
           f"| Answerable: partial | {verdicts['partial']}/{len(ans)} ({verdicts['partial'] / n_ans:.0%}) |",
           f"| Answerable: wrong | {verdicts['wrong']}/{len(ans)} ({verdicts['wrong'] / n_ans:.0%}) |",
           f"| Answerable: wrongly refused | {sum(r['refused'] for r in ans)}/{len(ans)} "
           f"(threshold {sum(r['refused_by'] == 'threshold' for r in ans)}, LLM {sum(r['refused_by'] == 'llm' for r in ans)}) |",
           f"| Faithful (no outside knowledge), of answered | {pct(answered, 'faithful')} |",
           f"| Has a citation, of answered | {pct(answered, 'has_citation')} |",
           f"| Cites a correct (gold) page, of answered | {pct(answered, 'cites_gold')} |",
           f"| Cites only retrieved pages, of answered | {pct(answered, 'cites_only_retrieved')} |",
           f"| Answer in the question's language | {pct(answered, 'language_ok')} |",
           f"| Unanswerable: correctly refused | {sum(r['refused'] for r in una)}/{len(una)} "
           f"(threshold {sum(r['refused_by'] == 'threshold' for r in una)}, LLM {sum(r['refused_by'] == 'llm' for r in una)}) |",
           f"| Avg retrieval time | {mean(r['retrieval_ms'] for r in rows) / 1000:.1f} s |",
           f"| Avg LLM time (when called) | {mean([r['llm_ms'] for r in rows if r['llm_ms']] or [0]) / 1000:.1f} s |",
           f"| LLM calls saved by the refusal threshold | {sum(r['refused_by'] == 'threshold' for r in rows)}/{len(rows)} |",
           ""]
    if verdicts.get("unparsed"):
        out.append(f"Note: {verdicts['unparsed']} judge replies couldn't be parsed (counted as not correct).\n")

    out += ["## Per question\n",
            "| ID | Verdict | Faithful | Cites gold | Lang | Refused | Answer |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if not r["answerable"]:
            verdict = "✅ refused" if r["refused"] else "❌ answered"
        elif r["refused"]:
            verdict = "❌ refused"
        else:
            verdict = {"correct": "✅ correct", "partial": "🟡 partial", "wrong": "❌ wrong"}.get(r["correctness"], "–")
        short = r["answer"].replace("\n", " ").replace("|", "/")
        short = short[:140] + ("…" if len(short) > 140 else "")
        yn = lambda v: "–" if v is None else ("yes" if v else "no")
        out.append(f"| {r['id']} | {verdict} | {yn(r['faithful'])} | {yn(r['cites_gold']) if r['answerable'] and not r['refused'] else '–'} "
                   f"| {'ok' if r['language_ok'] else 'WRONG'} | {r['refused_by'] or '–'} | {short} |")

    problems = [r for r in rows if (r["answerable"] and (r["refused"] or r["correctness"] in {"partial", "wrong", "unparsed"}
                                                         or r["faithful"] is False))
                or (not r["answerable"] and not r["refused"])]
    out += ["\n## Problems to look at\n"]
    if not problems:
        out.append("None.")
    for r in problems:
        out.append(f"- **{r['id']}** {r['question']}  \n  answer: {r['answer'][:300]}  \n"
                   f"  judge: {r['correctness']}, faithful={r['faithful']} — {r['reason']}  \n"
                   f"  top score {r['top_score']:.3f}; retrieved: {'; '.join(r['retrieved'])}")

    stamp = f"{datetime.now():%Y-%m-%d_%H-%M}"
    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"answers_{args.set}_{stamp}"
    (out_dir / f"{name}.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (out_dir / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(out[3:23]))
    print(f"\nFull report: eval/results/{name}.md")


if __name__ == "__main__":
    main()
