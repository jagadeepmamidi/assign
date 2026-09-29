"""Application configuration, rooted at repository directory."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    base_url: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    api_key: str = os.getenv("LLM_API_KEY", "")
    model: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    cache_dir: Path = ROOT / ".cache"
    chroma_dir: Path = ROOT / ".chroma"


settings = Settings()


def require_api_key() -> str:
    if not settings.api_key or settings.api_key.startswith("your-"):
        raise RuntimeError("LLM_API_KEY is missing. Copy .env.example to .env and add an OpenAI-compatible API key.")
    return settings.api_key
