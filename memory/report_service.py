import uuid
from datetime import datetime, timezone

from memory.db import execute_sql, initialize_memory_db, query_all, query_one


DEFAULT_REPORT_TITLE = "FinCopilot Multi-Agent Finance Report"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_report_id() -> str:
    return f"report_{uuid.uuid4().hex}"


def extract_report_title(report_markdown: str | None) -> str:
    for line in str(report_markdown or "").splitlines():
        text = line.strip()
        if text.startswith("#"):
            title = text.lstrip("#").strip()
            return title[:80] if title else DEFAULT_REPORT_TITLE
    return DEFAULT_REPORT_TITLE


def extract_report_summary(report_markdown: str | None, max_chars: int = 1200) -> str:
    lines = [
        line.strip()
        for line in str(report_markdown or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    summary = "\n\n".join(lines[:8])
    return summary[:max_chars].rstrip() if len(summary) > max_chars else summary


def persist_report(
    user_id: str,
    workspace_id: str,
    turn_id: str,
    report_markdown: str | None,
    report_title: str | None = None,
    report_summary: str | None = None,
    db_path: str | None = None,
) -> dict:
    initialize_memory_db(db_path=db_path)
    report_id = generate_report_id()
    markdown = report_markdown or ""
    execute_sql(
        """
        INSERT INTO reports (
            report_id, turn_id, user_id, workspace_id, report_title,
            report_summary, report_markdown, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_id,
            turn_id,
            user_id,
            workspace_id,
            report_title or extract_report_title(markdown),
            report_summary or extract_report_summary(markdown),
            markdown,
            now_iso(),
        ),
        db_path=db_path,
    )
    return get_report(user_id, workspace_id, report_id, db_path=db_path) or {}


def get_report(user_id: str, workspace_id: str, report_id: str, db_path: str | None = None) -> dict | None:
    return query_one(
        """
        SELECT *
        FROM reports
        WHERE user_id = ? AND workspace_id = ? AND report_id = ?
        """,
        (user_id, workspace_id, report_id),
        db_path=db_path,
    )


def list_reports(user_id: str, workspace_id: str, limit: int = 50, db_path: str | None = None) -> list[dict]:
    initialize_memory_db(db_path=db_path)
    return query_all(
        """
        SELECT *
        FROM reports
        WHERE user_id = ? AND workspace_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, workspace_id, max(1, int(limit))),
        db_path=db_path,
    )
