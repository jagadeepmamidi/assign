"""Environment-backed configuration for the local invoice engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    database_path: Path = Path(os.getenv("INVOICE_DB_PATH", str(ROOT / "data" / "invoice_engine.sqlite3")))
    upload_max_bytes: int = int(os.getenv("INVOICE_MAX_UPLOAD_BYTES", "10485760"))


settings = Settings()
