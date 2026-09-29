"""Load synthetic support data and perform dataset-anchored account joins."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import settings


def _read(name: str) -> list[dict[str, Any]]:
    path = settings.root / "data" / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError(f"Unable to load dataset file: {path}") from exc


def load_tickets() -> list[dict[str, Any]]:
    return sorted(_read("tickets.json"), key=lambda x: (x.get("created_at", ""), x.get("ticket_id", "")))


def load_accounts() -> list[dict[str, Any]]:
    return sorted(_read("accounts.json"), key=lambda x: x.get("account_id", ""))


def account_map() -> dict[str, dict[str, Any]]:
    return {a["account_id"]: a for a in load_accounts()}


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def dataset_max_date(tickets: list[dict[str, Any]] | None = None) -> datetime:
    rows = tickets if tickets is not None else load_tickets()
    return max((parse_date(t["created_at"]) for t in rows), default=datetime.now(timezone.utc))


def get_account_tickets(
    account_id: str,
    *,
    days: int = 90,
    reference_date: datetime | None = None,
    tickets: list[dict[str, Any]] | None = None,
    account: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows = tickets if tickets is not None else load_tickets()
    account = account if account is not None else account_map().get(account_id)
    company = str(account.get("company", "")).casefold() if account else ""
    cutoff = (reference_date or dataset_max_date(rows)) - timedelta(days=days)
    selected = [
        ticket
        for ticket in rows
        if (
            ticket.get("account_id") == account_id or (company and str(ticket.get("company", "")).casefold() == company)
        )
        and parse_date(ticket["created_at"]) >= cutoff
    ]
    return sorted(
        {ticket["ticket_id"]: ticket for ticket in selected}.values(),
        key=lambda x: (x.get("created_at", ""), x.get("ticket_id", "")),
    )
