"""Provider-agnostic OpenAI-compatible LLM wrapper with validation and disk caching."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Iterator
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from .config import require_api_key, settings

T = TypeVar("T", bound=BaseModel)
_EMAIL = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+(?:[.][A-Za-z0-9-]+)+")
_PHONE = re.compile(r"(?<![A-Za-z0-9])(?:[+]?[0-9][0-9 ()-]{7,}[0-9])(?![A-Za-z0-9])")


def redact(text: str) -> str:
    return _PHONE.sub("[REDACTED_PHONE]", _EMAIL.sub("[REDACTED_EMAIL]", text))


def _client() -> OpenAI:
    return OpenAI(api_key=require_api_key(), base_url=settings.base_url)


def _cache_key(prompt_file: str, prompt: str) -> str:
    return hashlib.sha256(f"{settings.model}\n{prompt_file}\n{prompt}".encode()).hexdigest()


def _cached(prompt_file: str, prompt: str) -> str | None:
    path = settings.cache_dir / f"{_cache_key(prompt_file, prompt)}.json"
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["content"]
    except (OSError, KeyError, json.JSONDecodeError, TypeError):
        return None
    return None


def _save_cache(prompt_file: str, prompt: str, content: str) -> None:
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    path = settings.cache_dir / f"{_cache_key(prompt_file, prompt)}.json"
    if not path.exists():
        path.write_text(json.dumps({"content": content}, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def prompt_text(filename: str) -> str:
    return (settings.root / "src" / "prompts" / filename).read_text(encoding="utf-8")


def complete_json(prompt_file: str, rendered_prompt: str, model_type: type[T], *, retries: int = 2) -> T:
    """Call JSON mode, validate with Pydantic, and retry once on invalid output."""
    cached = _cached(prompt_file, rendered_prompt)
    if cached is not None:
        return model_type.model_validate_json(cached)
    base = prompt_text(prompt_file) + "\n\n" + redact(rendered_prompt)
    last_error: Exception | None = None
    for attempt in range(retries):
        prompt = (
            base if attempt == 0 else base + f"\n\nPrevious validation error; return corrected JSON only:\n{last_error}"
        )
        try:
            response = _client().chat.completions.create(
                model=settings.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                seed=42,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            result = model_type.model_validate_json(content)
            _save_cache(prompt_file, rendered_prompt, content)
            return result
        except (ValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
            last_error = exc
            if attempt + 1 == retries:
                raise RuntimeError(f"LLM returned invalid structured output after {retries} attempts: {exc}") from exc
        except Exception as exc:
            last_error = exc
            if attempt + 1 == retries:
                raise RuntimeError(f"LLM request failed after {retries} attempts: {exc}") from exc
            time.sleep(2**attempt)
    raise RuntimeError(f"LLM request failed: {last_error}")


def stream_text(prompt_file: str, rendered_prompt: str) -> Iterator[str]:
    stream = _client().chat.completions.create(
        model=settings.model,
        messages=[{"role": "user", "content": prompt_text(prompt_file) + "\n\n" + redact(rendered_prompt)}],
        temperature=0,
        seed=42,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content if event.choices else None
        if delta:
            yield delta
