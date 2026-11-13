"""Tiny wrapper around any OpenAI-compatible chat API (Ollama, OpenAI, ...), configured in .env."""

import os
from functools import lru_cache

from openai import OpenAI


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])


def chat(system: str, user: str) -> tuple[str, object]:
    """Send one system + user message, return (reply text, token usage)."""
    response = get_client().chat.completions.create(
        model=os.environ["LLM_MODEL"],
        temperature=0,  # same question -> (nearly) same answer; easier to evaluate
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return response.choices[0].message.content.strip(), response.usage
