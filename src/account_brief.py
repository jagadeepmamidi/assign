"""Task 2: deterministic, two-stage TAM account health brief."""

from __future__ import annotations

import argparse
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .data_loader import account_map, get_account_tickets
from .llm import complete_json


class Signal(BaseModel):
    ticket_id: str
    quote: str = Field(min_length=1)
    signal_type: Literal["churn", "escalation"]
    why_matters: str = Field(min_length=1)


class Extraction(BaseModel):
    signals: list[Signal] = Field(default_factory=list)


class Risk(BaseModel):
    ticket_id: str
    quote: str = Field(min_length=1)
    signal_type: Literal["churn", "escalation"]
    why_matters: str = Field(min_length=1)


class Synthesis(BaseModel):
    executive_summary: str = Field(min_length=1)
    open_risks: list[Risk] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)


class AccountBrief(BaseModel):
    model_config = ConfigDict(extra="ignore")
    account_id: str
    company: str | None = None
    account_found: bool
    executive_summary: str = Field(min_length=1)
    open_risks: list[Risk] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# Account health brief: {self.company or self.account_id}",
            "",
            "## Executive summary",
            self.executive_summary,
            "",
            "## Open risks",
        ]
        if self.open_risks:
            lines.extend(
                f'- **{r.signal_type.title()} ({r.ticket_id})** — {r.why_matters} Quote: "{r.quote}"'
                for r in self.open_risks
            )
        else:
            lines.append("- No validated churn or escalation signals in the analysis window.")
        lines.extend(["", "## Talking points"])
        lines.extend(
            f"- {point}"
            for point in self.talking_points or ["Review current health indicators and agree next actions."]
        )
        return "\n".join(lines) + "\n"


def _stable_json(model: BaseModel) -> str:
    return json.dumps(model.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _source_map(account: dict | None, tickets: list[dict]) -> dict[str, str]:
    sources = {t["ticket_id"]: str(t.get("body", "")) for t in tickets}
    if account:
        sources.update(
            {f"ACCOUNT_NOTE-{i + 1}": str(note) for i, note in enumerate(account.get("escalation_notes", []))}
        )
    return sources


def _valid_signals(extraction: Extraction, sources: dict[str, str]) -> list[Signal]:
    valid: list[Signal] = []
    seen: set[tuple[str, str]] = set()
    for signal in extraction.signals:
        source = sources.get(signal.ticket_id, "")
        if source and signal.quote in source and (signal.ticket_id, signal.quote) not in seen:
            valid.append(signal)
            seen.add((signal.ticket_id, signal.quote))
    return sorted(valid, key=lambda s: (s.ticket_id, s.signal_type, s.quote))


def _offline_signals(account: dict | None, tickets: list[dict]) -> list[Signal]:
    sources = _source_map(account, tickets)
    terms = ("cancel", "churn", "compet", "renewal", "frustrat", "escalat", "unhappy", "leaving", "slow response")
    out: list[Signal] = []
    for ticket in tickets:
        for sentence in re.split("(?<=[.!?])[ \t]+|" + chr(10) + "+", str(ticket.get("body", ""))):
            if any(term in sentence.casefold() for term in terms):
                kind: Literal["churn", "escalation"] = (
                    "churn"
                    if any(x in sentence.casefold() for x in ("cancel", "churn", "compet", "leaving", "renewal"))
                    else "escalation"
                )
                out.append(
                    Signal(
                        ticket_id=ticket["ticket_id"],
                        quote=sentence.strip(),
                        signal_type=kind,
                        why_matters="Direct customer signal requires TAM follow-up.",
                    )
                )
                break
    if account:
        for i, note in enumerate(account.get("escalation_notes", []), 1):
            if any(term in str(note).casefold() for term in terms):
                out.append(
                    Signal(
                        ticket_id=f"ACCOUNT_NOTE-{i}",
                        quote=str(note),
                        signal_type="churn"
                        if any(x in str(note).casefold() for x in ("compet", "cancel", "churn", "renewal"))
                        else "escalation",
                        why_matters="Account note records a relationship risk.",
                    )
                )
    return _valid_signals(Extraction(signals=out), sources)


def _offline_brief(account_id: str, account: dict | None, tickets: list[dict]) -> AccountBrief:
    if not account:
        return AccountBrief(
            account_id=account_id,
            company=None,
            account_found=False,
            executive_summary=f"Account {account_id} was not found in accounts.json. {len(tickets)} ticket(s) matched the supplied account ID in the analysis window. No account-level ARR, plan, or renewal data is available.",
            open_risks=[],
            talking_points=["Confirm account ownership and repair the account-to-ticket join."],
        )
    risks = [Risk(**s.model_dump()) for s in _offline_signals(account, tickets)]
    summary = (
        f"{account['company']} is on the {account['plan_tier']} plan with ${account['arr_usd']:,} ARR and health status {account['health_status']}. "
        f"Usage trend is {account['usage_trend']} with {account['seats_active']} of {account['seats_licensed']} seats active. "
        f"Renewal is {account['renewal_date']}; the window contains {len(tickets)} joined ticket(s), including {sum(t.get('urgency') == 'P1' for t in tickets)} P1 ticket(s)."
    )
    points = [
        f"Review {len(risks)} validated risk signal(s) and agree owners before the {account['renewal_date']} renewal.",
        f"Discuss adoption: {account['seats_active']} active seats out of {account['seats_licensed']} licensed.",
        "Confirm remediation plan for recent support pressure and escalation notes.",
    ]
    return AccountBrief(
        account_id=account_id,
        company=account["company"],
        account_found=True,
        executive_summary=summary,
        open_risks=risks,
        talking_points=points,
    )


def build_account_brief(
    account_id: str, *, window_days: int = 90, reference_date=None, allow_offline: bool = False
) -> AccountBrief:
    accounts = account_map()
    account = accounts.get(account_id)
    tickets = get_account_tickets(account_id, days=window_days, reference_date=reference_date, account=account)
    if allow_offline:
        return _offline_brief(account_id, account, tickets)
    if not account:
        return _offline_brief(account_id, None, tickets)
    sources = _source_map(account, tickets)
    ticket_payload = [
        {k: t.get(k) for k in ("ticket_id", "subject", "body", "category", "urgency", "status", "created_at")}
        for t in tickets
    ]
    extract_prompt = f"ACCOUNT ESCALATION NOTES (quote using ACCOUNT_NOTE-N identifiers):\n{json.dumps(account.get('escalation_notes', []), ensure_ascii=False, sort_keys=True)}\n\nTICKETS:\n{json.dumps(ticket_payload, ensure_ascii=False, sort_keys=True)}"
    extraction = _valid_signals(complete_json("brief_extract_v1.txt", extract_prompt, Extraction), sources)
    signal_payload = [s.model_dump() for s in extraction]
    synth_prompt = f"ACCOUNT SUMMARY:\n{json.dumps(account, ensure_ascii=False, sort_keys=True)}\n\nWINDOW TICKETS:\n{json.dumps(ticket_payload, ensure_ascii=False, sort_keys=True)}\n\nVALIDATED SIGNALS (use only these quotes):\n{json.dumps(signal_payload, ensure_ascii=False, sort_keys=True)}"
    synthesis = complete_json("brief_synth_v1.txt", synth_prompt, Synthesis)
    risks = [
        risk for risk in synthesis.open_risks if risk.ticket_id in sources and risk.quote in sources[risk.ticket_id]
    ]
    risks.sort(key=lambda r: (r.ticket_id, r.signal_type, r.quote))
    points = sorted(dict.fromkeys(p.strip() for p in synthesis.talking_points if p.strip()))
    return AccountBrief(
        account_id=account_id,
        company=account["company"],
        account_found=True,
        executive_summary=synthesis.executive_summary,
        open_risks=risks,
        talking_points=points,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one TAM account health brief")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--window-days", type=int, default=90)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    result = build_account_brief(args.account_id, window_days=args.window_days, allow_offline=args.offline)
    print(_stable_json(result))
    print(result.to_markdown())


if __name__ == "__main__":
    main()
