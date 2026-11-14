"""Turn a question into an answer: retrieve -> (maybe refuse early) -> LLM answer with citations.

Used by rag/ask.py (command line), eval/run_manual.py and eval/run_answers.py, so all of them
behave exactly the same way.
"""

import re
import time

from rag import config
from rag.llm import chat
from rag.retrieval import retrieve

NO_ANSWER_TOKEN = "NO_ANSWER"
NO_ANSWER_TEXT = {
    "en": "The documents don't contain an answer to this question.",
    "de": "Die Dokumente enthalten keine Antwort auf diese Frage.",
}

SYSTEM_PROMPT = f"""You answer questions about university documents.

Rules:
- Use ONLY the context passages. Never use outside knowledge, not even for facts you are sure about.
- After each statement, cite its source by copying the tag shown above that passage exactly,
  e.g. [satzung_studienrecht_2026.pdf, p. 29]. Never cite passage numbers.
- If the passages don't contain the answer, reply with exactly {NO_ANSWER_TOKEN} and nothing else.
- If you can answer, don't add any sentence saying something is missing from the documents.
- Write the answer in the language you are told to use. Keep it short and precise."""

_DE = set("der die das und ist nicht ich wie was wann wo wer darf kann muss mein meine meinen für von mit "
          "eine einen einer auf im zum zur bei gibt es welche welcher welches bis".split())
_EN = set("the and is not i how what when where who can may must my for of with a an on in to do does "
          "there which until".split())


def detect_language(text: str, default: str | None = "en") -> str | None:
    """Tiny DE/EN guesser: umlauts and common words. Good enough for questions.

    Returns `default` when there's no signal at all (e.g. "180 ECTS" or "Level B2").
    """
    words = re.findall(r"\w+", text.lower())
    de = sum(w in _DE for w in words) + 2 * len(re.findall(r"[äöüß]", text.lower()))
    en = sum(w in _EN for w in words)
    if de == en:
        return default
    return "de" if de > en else "en"


def build_context(hits: list[dict]) -> str:
    return "\n\n".join(f"Source: [{h['source']}, p. {h['page']}]\n{h['text']}" for h in hits)


def clean_reply(reply: str) -> tuple[str, bool]:
    """Return (text, refused). Handles the model mixing an answer with NO_ANSWER."""
    stripped = reply.strip()
    if stripped.upper().startswith(NO_ANSWER_TOKEN):
        return "", True
    if NO_ANSWER_TOKEN in stripped:
        # The model gave an answer AND added the refusal token: keep the answer, drop the token.
        stripped = stripped.replace(NO_ANSWER_TOKEN, "").strip(" .\n")
        if not stripped:
            return "", True
    return stripped, False


def answer_question(question: str, *, versions: list[str] | None = None) -> dict:
    """Full pipeline for one question. Returns a dict with the answer and everything needed to evaluate it."""
    lang = detect_language(question)
    t0 = time.perf_counter()
    steps: dict = {}
    hits = retrieve(question, versions=versions, timings=steps)
    t1 = time.perf_counter()
    top_score = hits[0]["score"] if hits else 0.0

    result = {"question": question, "lang": lang, "hits": hits, "top_score": top_score,
              "retrieval_ms": 1000 * (t1 - t0), "steps_ms": steps, "llm_ms": 0.0, "usage": None}

    # 1) Early refusal: the reranker says nothing relevant was found -> don't even ask the LLM.
    if config.USE_RERANKER and config.REFUSAL_THRESHOLD is not None and top_score < config.REFUSAL_THRESHOLD:
        return {**result, "answer": NO_ANSWER_TEXT[lang], "refused": True, "refused_by": "threshold"}

    # 2) Ask the LLM, telling it explicitly which language to use.
    language_name = "German" if lang == "de" else "English"
    user = f"Context:\n{build_context(hits)}\n\nQuestion: {question}\n\nAnswer in {language_name}."
    reply, usage = chat(SYSTEM_PROMPT, user)
    result["llm_ms"] = 1000 * (time.perf_counter() - t1)
    result["usage"] = usage

    text, refused = clean_reply(reply)
    if refused:
        return {**result, "answer": NO_ANSWER_TEXT[lang], "refused": True, "refused_by": "llm"}
    return {**result, "answer": text, "refused": False, "refused_by": None}
