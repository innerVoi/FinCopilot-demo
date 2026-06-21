import re


def slugify_filename(text: str) -> str:
    """
    Convert text to a safe filename fragment.
    """
    value = str(text or "report").strip().lower()
    value = re.sub(r"[^a-z0-9_\-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "report"


def build_report_filename(task_id: str | None = None, suffix: str = "md") -> str:
    """
    Build a Markdown report filename.
    """
    safe_task_id = slugify_filename(task_id or "agent_workflow")
    safe_suffix = slugify_filename(suffix or "md").lstrip(".")
    return f"fincopilot_agent_report_{safe_task_id}.{safe_suffix}"


def encode_markdown_for_download(markdown_text: str) -> bytes:
    """
    Encode Markdown text for Streamlit download buttons.
    """
    return str(markdown_text or "").encode("utf-8")
