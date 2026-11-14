"""Tiny wrapper around any OpenAI-compatible chat API (Ollama, OpenAI, ...), configured in .env.

Two roles:
  "answer" uses LLM_BASE_URL / LLM_API_KEY / LLM_MODEL       (answers + query translation)
  "judge"  uses JUDGE_BASE_URL / JUDGE_API_KEY / JUDGE_MODEL (grading answers in eval/run_answers.py),
           falling back to the LLM_* values if JUDGE_* isn't set.
"""

import os
from functools import lru_cache

from openai import OpenAI


def _setting(role: str, name: str) -> str:
    if role == "judge" and os.environ.get(f"JUDGE_{name}"):
        return os.environ[f"JUDGE_{name}"]
    return os.environ[f"LLM_{name}"]


@lru_cache(maxsize=2)
def get_client(role: str = "answer") -> OpenAI:
    return OpenAI(base_url=_setting(role, "BASE_URL"), api_key=_setting(role, "API_KEY"))


def model_name(role: str = "answer") -> str:
    return _setting(role, "MODEL")


def chat(system: str, user: str, role: str = "answer") -> tuple[str, object]:
    """Send one system + user message, return (reply text, token usage)."""
    extra = {}
    # temperature 0 = same question -> (nearly) same answer; easier to evaluate.
    # Newer Claude models reject temperature < 1 through the OpenAI-compatible API, so skip it there.
    if "anthropic.com" not in _setting(role, "BASE_URL"):
        extra["temperature"] = 0
    response = get_client(role).chat.completions.create(
        model=model_name(role),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **extra,
    )
    return (response.choices[0].message.content or "").strip(), response.usage
