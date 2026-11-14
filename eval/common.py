"""Helpers shared by the eval scripts: question sets and the translation cache."""

import json

from rag.config import ROOT
from rag.retrieval import query_versions

SETS = {
    "main": ROOT / "eval" / "eval_set.json",        # 80 questions, used while tuning
    "heldout": ROOT / "eval" / "heldout_set.json",  # 20 questions, never used for tuning
}
CACHE = ROOT / "eval" / "cache" / "translations.json"


def load_set(name: str) -> list[dict]:
    return json.loads(SETS[name].read_text(encoding="utf-8"))


def load_translations(questions: list[dict]) -> dict[str, list[str]]:
    """Question -> [original, German, English]. Asks the LLM only for questions not cached yet."""
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
