from agent.report_exporter import (
    build_report_filename,
    encode_markdown_for_download,
    slugify_filename,
)


def test_slugify_filename_returns_safe_fragment():
    assert slugify_filename("Cashflow Safety Check!") == "cashflow_safety_check"
    assert slugify_filename("") == "report"


def test_build_report_filename_returns_markdown_filename():
    filename = build_report_filename("cashflow_safety_check")

    assert filename.startswith("fincopilot_agent_report_cashflow_safety_check")
    assert filename.endswith(".md")


def test_encode_markdown_for_download_returns_bytes_and_roundtrips():
    markdown = "# Report\n\nHello"
    encoded = encode_markdown_for_download(markdown)

    assert isinstance(encoded, bytes)
    assert encoded.decode("utf-8") == markdown
