"""Automatic retrieval evaluation: how often do we find the right page, and how much noise comes with it?

Run from the project root:
    python -m eval.run_retrieval                       # all configurations
    python -m eval.run_retrieval --configs dense full  # only some

Uses eval/eval_set.json (questions + the pages that contain the answer). No LLM answers are
generated here, only the search is tested, so it's fast and fully automatic.
Translations are cached in eval/cache/translations.json, so the LLM is only asked once per question.

Metrics (a retrieved chunk counts as relevant if its file + page is in the question's gold pages):
  Hit@1 / Hit@5   share of questions with a relevant chunk at rank 1 / in the top 5  (= recall)
  MRR             average of 1/rank of the first relevant chunk (1.0 = always first)
  Precision@5     share of the top-5 chunks that are relevant (noise check; max < 1 when only
                  one page is relevant, so compare configs with each other, not with 1.0)
"""

import argparse
import json
import time
from datetime import datetime
from statistics import mean

from dotenv import load_dotenv

from rag import config
from rag.config import ROOT, get_embedder, get_reranker
from rag.retrieval import query_versions, retrieve

EVAL_SET = ROOT / "eval" / "eval_set.json"
CACHE = ROOT / "eval" / "cache" / "translations.json"
K = 5
DEPTH = 10  # how deep we look for MRR

CONFIGS = {
    # name: (translate, hybrid, reranker)
    "dense":            (False, False, False),
    "dense+translate":  (True,  False, False),
    "hybrid":           (False, True,  False),
    "hybrid+translate": (True,  True,  False),
    "hybrid+rerank":    (False, True,  True),
    "full":             (True,  True,  True),
}


def load_translations(questions: list[dict]) -> dict[str, list[str]]:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    missing = [q for q in questions if q["question"] not in cache]
    if missing:
        print(f"Translating {len(missing)} questions with the LLM (cached for next time)...")
        for i, q in enumerate(missing, 1):
            cache[q["question"]] = query_versions(q["question"], translate=True)
            print(f"  {i}/{len(missing)}", end="\r")
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        print()
    return cache


def is_relevant(hit: dict, gold: dict) -> bool:
    return hit["page"] in gold.get(hit["source"], [])


def evaluate(questions, translations, translate, hybrid, rerank) -> dict:
    rows = []
    for q in questions:
        t0 = time.perf_counter()
        hits = retrieve(q["question"], k=DEPTH, translate=translate, hybrid=hybrid,
                        use_reranker=rerank, versions=translations[q["question"]])
        ms = 1000 * (time.perf_counter() - t0)
        rel = [is_relevant(h, q["gold"]) for h in hits] if q["answerable"] else []
        first = next((i for i, r in enumerate(rel) if r), None)
        rows.append({
            "id": q["id"], "lang": q["lang"], "doc_lang": q["doc_lang"], "answerable": q["answerable"],
            "hit1": first == 0, "hit5": first is not None and first < K,
            "rr": 1 / (first + 1) if first is not None else 0.0,
            "p5": sum(rel[:K]) / K if rel else 0.0,
            "top_score": hits[0]["score"] if hits else 0.0,
            "top5": [f"{h['source']} p{h['page']}" for h in hits[:K]],
            "ms": ms,
        })
    return {"rows": rows}


def summarise(rows: list[dict]) -> dict:
    ans = [r for r in rows if r["answerable"]]
    if not ans:
        return {}
    return {"n": len(ans), "hit1": mean(r["hit1"] for r in ans), "hit5": mean(r["hit5"] for r in ans),
            "mrr": mean(r["rr"] for r in ans), "p5": mean(r["p5"] for r in ans)}


def abstain_check(rows: list[dict]) -> str:
    """With a reranker, does the top score separate answerable from unanswerable questions?"""
    ans = sorted(r["top_score"] for r in rows if r["answerable"])
    una = sorted(r["top_score"] for r in rows if not r["answerable"])
    if not una:
        return ""
    best_t, best_acc = None, 0.0
    for t in sorted(set(ans + una)):
        acc = (sum(s >= t for s in ans) + sum(s < t for s in una)) / (len(ans) + len(una))
        if acc > best_acc:
            best_t, best_acc = t, acc
    return (f"top score answerable: median {ans[len(ans)//2]:.3f} (min {ans[0]:.3f}) | "
            f"unanswerable: median {una[len(una)//2]:.3f} (max {una[-1]:.3f}) | "
            f"best threshold {best_t:.3f} -> {best_acc:.0%} correct answer/refuse decisions")


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="*", default=list(CONFIGS), choices=list(CONFIGS))
    args = parser.parse_args()

    questions = json.loads(EVAL_SET.read_text(encoding="utf-8"))
    get_embedder()
    if any(CONFIGS[c][2] for c in args.configs):
        get_reranker()
    translations = load_translations(questions)

    results = {}
    for name in args.configs:
        print(f"Running {name}...")
        results[name] = evaluate(questions, translations, *CONFIGS[name])

    # ---------- report
    out = [f"# Retrieval eval {datetime.now():%Y-%m-%d %H:%M}\n",
           f"{len(questions)} questions ({sum(q['answerable'] for q in questions)} answerable). "
           f"Embedding: {config.EMBEDDING_MODEL}, reranker: {config.RERANKER_MODEL}, "
           f"chunks: {config.CHUNK_WORDS} words, header stripping: {config.STRIP_HEADERS}, k={K}.\n",
           "## Overall (answerable questions)\n",
           "| Config | Hit@1 | Hit@5 (recall) | MRR | Precision@5 | ms/question* |",
           "|---|---|---|---|---|---|"]
    for name, res in results.items():
        s = summarise(res["rows"])
        ms = mean(r["ms"] for r in res["rows"])
        out.append(f"| {name} | {s['hit1']:.0%} | {s['hit5']:.0%} | {s['mrr']:.2f} | {s['p5']:.2f} | {ms:.0f} |")
    out.append("\n*Search only; translation is cached here. In the live app add ~2-4 s per question for the translation call.\n")

    out += ["## Hit@5 by language (question → documents)\n",
            "| Config | same language | cross-language | German questions | English questions |",
            "|---|---|---|---|---|"]
    for name, res in results.items():
        rows = [r for r in res["rows"] if r["answerable"]]
        same = [r for r in rows if r["lang"] in r["doc_lang"]]
        cross = [r for r in rows if r["lang"] not in r["doc_lang"]]
        de = [r for r in rows if r["lang"] == "de"]
        en = [r for r in rows if r["lang"] == "en"]
        f = lambda rs: f"{mean(r['hit5'] for r in rs):.0%} ({len(rs)})" if rs else "-"
        out.append(f"| {name} | {f(same)} | {f(cross)} | {f(de)} | {f(en)} |")

    rerank_runs = [n for n in results if CONFIGS[n][2]]
    if rerank_runs:
        out += ["\n## Can the reranker score detect unanswerable questions?\n"]
        for name in rerank_runs:
            out.append(f"- **{name}**: {abstain_check(results[name]['rows'])}")

    best = max(results, key=lambda n: (summarise(results[n]['rows'])["hit5"], summarise(results[n]['rows'])["mrr"]))
    misses = [r for r in results[best]["rows"] if r["answerable"] and not r["hit5"]]
    by_id = {q["id"]: q for q in questions}
    out += [f"\n## Misses of the best config ({best})\n"]
    if not misses:
        out.append("None: every answerable question had a relevant page in the top 5.")
    for r in misses:
        q = by_id[r["id"]]
        gold = ", ".join(f"{f} p{','.join(map(str, p))}" for f, p in q["gold"].items())
        out.append(f"- **{r['id']}** {q['question']}  \n  gold: {gold}  \n  got: {'; '.join(r['top5'])}")

    stamp = f"{datetime.now():%Y-%m-%d_%H-%M}"
    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"retrieval_{stamp}.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (out_dir / f"retrieval_{stamp}.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
    print("\n".join(out[3:3 + len(results) + 2]))
    print(f"\nFull report: eval/results/retrieval_{stamp}.md")


if __name__ == "__main__":
    main()
