"""Deterministic rule checks plus optional LLM-as-judge RAGAS-style metrics."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from src.account_brief import AccountBrief, build_account_brief  # pyright: ignore[reportMissingImports]
from src.config import settings  # pyright: ignore[reportMissingImports]
from src.data_loader import account_map, get_account_tickets, load_tickets  # pyright: ignore[reportMissingImports]
from src.llm import complete_json  # pyright: ignore[reportMissingImports]
from src.retrieval import get_retriever  # pyright: ignore[reportMissingImports]
from src.triage import TriageResult, triage_ticket  # pyright: ignore[reportMissingImports]

ROOT = Path(__file__).resolve().parents[1]


class JudgeResult(BaseModel):
    score: float
    notes: str


def add(rows: list[dict], case_id: str, task: str, kind: str, passed: bool, score: float, notes: str) -> None:
    rows.append(
        {
            "case_id": case_id,
            "task": task,
            "type": kind,
            "pass": bool(passed),
            "score": round(max(0.0, min(1.0, score)), 3),
            "notes": notes,
        }
    )


def source_valid(brief: AccountBrief) -> bool:
    sources = {}
    for ticket in load_tickets():
        sources[ticket["ticket_id"]] = ticket.get("body", "")
    account = account_map().get(brief.account_id)
    if account:
        sources.update({f"ACCOUNT_NOTE-{i + 1}": note for i, note in enumerate(account.get("escalation_notes", []))})
    return all(r.ticket_id in sources and r.quote in sources[r.ticket_id] for r in brief.open_risks)


def judge(metric: str, answer: str, evidence: str) -> tuple[float, str]:
    if not settings.api_key or settings.api_key.startswith("your-"):
        return 0.0, "skipped: LLM_API_KEY not configured"
    result = complete_json("judge_v1.txt", f"METRIC: {metric}\nANSWER:\n{answer}\nEVIDENCE:\n{evidence}", JudgeResult)
    return result.score, result.notes


def run() -> list[dict]:
    rows: list[dict] = []
    try:
        triage_cases = json.loads((ROOT / "evals" / "cases_triage.json").read_text(encoding="utf-8"))
        brief_cases = json.loads((ROOT / "evals" / "cases_brief.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("Evaluation case files are missing or invalid") from exc
    retriever = get_retriever()
    for case in triage_cases:
        result = triage_ticket(
            case["subject"],
            case["body"],
            retriever=retriever,
            allow_offline=not settings.api_key or settings.api_key.startswith("your-"),
        )
        valid = (
            isinstance(result, TriageResult)
            and result.category
            in {"Bug", "Feature Request", "How-To", "Performance", "Billing", "Integration", "Onboarding", "Data Loss"}
            and result.urgency in {"P1", "P2", "P3", "P4"}
        )
        citation_ok = result.matched_kb_doc is None or (ROOT / result.matched_kb_doc.source_file).exists()
        add(
            rows,
            case["id"],
            "Task 1",
            "rule",
            valid and citation_ok,
            1.0 if valid and citation_ok else 0.0,
            "schema and citation check",
        )
        if case.get("product") and case["product"] != "Billing":
            expected = case["product"].lower().replace(" ", "-") + ".md"
            hit = any(
                expected in h["chunk"].source_file for h in retriever.search(case["subject"] + " " + case["body"], k=3)
            )
            add(
                rows,
                case["id"],
                "Task 1",
                "retrieval_hit_rate",
                hit,
                1.0 if hit else 0.0,
                f"expected product document {expected}",
            )
        if case.get("adversarial"):
            # RAG grounding metrics are undefined for ungroundable inputs; the correct
            # behaviour for an ambiguous/empty ticket is to ask for clarification.
            asks = "?" in result.draft_first_response
            add(
                rows,
                case["id"],
                "Task 1",
                "adversarial_clarification",
                asks,
                1.0 if asks else 0.0,
                "ambiguous/empty ticket must elicit a clarifying question, not fabricated grounding",
            )
        elif settings.api_key and not settings.api_key.startswith("your-"):
            evidence = "\n\n".join(h["chunk"].text for h in retriever.search(case["subject"] + " " + case["body"], k=3))
            for metric in ("faithfulness", "answer relevancy", "context precision"):
                score, notes = judge(metric, result.draft_first_response, evidence)
                add(rows, case["id"], "Task 1", metric, score >= 0.5, score, notes)
    for case in brief_cases:
        kwargs = {
            "window_days": case.get("window_days", 90),
            "allow_offline": not settings.api_key or settings.api_key.startswith("your-"),
        }
        first = build_account_brief(case["account_id"], **kwargs)
        valid = (
            isinstance(first, AccountBrief)
            and bool(first.executive_summary)
            and (not first.account_found or first.account_id == case["account_id"])
        )
        add(
            rows,
            case["id"],
            "Task 2",
            "rule",
            valid and source_valid(first),
            1.0 if valid and source_valid(first) else 0.0,
            "schema, graceful missing-account, and quote-substring check",
        )
        second = build_account_brief(case["account_id"], **kwargs)
        same = first.model_dump_json() == second.model_dump_json()
        add(rows, case["id"], "Task 2", "determinism", same, 1.0 if same else 0.0, "byte-identical model JSON")
        if first.account_found and settings.api_key and not settings.api_key.startswith("your-"):
            account = account_map()[first.account_id]
            tickets = get_account_tickets(first.account_id)
            evidence = json.dumps({"account": account, "tickets": tickets}, ensure_ascii=False, sort_keys=True)
            score, notes = judge("groundedness", first.executive_summary, evidence)
            add(rows, case["id"], "Task 2", "groundedness", score >= 0.5, score, notes)
    return rows


def main() -> None:
    rows = run()
    report = {
        "metrics": rows,
        "summary": {
            "total": len(rows),
            "passed": sum(row["pass"] for row in rows),
            "api_judges_enabled": bool(settings.api_key and not settings.api_key.startswith("your-")),
        },
    }
    (ROOT / "evals" / "eval_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = ["# Evaluation report", "", "| Case | Task | Type | Pass | Score | Notes |", "|---|---|---|---:|---:|---|"]
    lines.extend(
        f"| {r['case_id']} | {r['task']} | {r['type']} | {'PASS' if r['pass'] else 'FAIL'} | {r['score']:.3f} | {r['notes'].replace('|', '/')} |"
        for r in rows
    )
    lines.extend(["", f"Passed **{report['summary']['passed']} / {report['summary']['total']}** checks."])
    (ROOT / "evals" / "eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
