from memory.report_service import (
    extract_report_summary,
    extract_report_title,
    generate_report_id,
    get_report,
    list_reports,
    persist_report,
)


def test_report_extractors():
    markdown = "# My Report\n\n摘要第一段\n\n## Detail\n\n详情"
    assert extract_report_title(markdown) == "My Report"
    assert "摘要第一段" in extract_report_summary(markdown)


def test_generate_report_id_has_prefix():
    assert generate_report_id().startswith("report_")


def test_persist_get_and_list_reports_scoped(tmp_path):
    db_path = str(tmp_path / "memory.db")
    report = persist_report("user_a", "shop_1", "turn_1", "# Report\n\n正文", db_path=db_path)
    assert report["report_title"] == "Report"
    assert get_report("user_a", "shop_1", report["report_id"], db_path=db_path)["report_markdown"]
    assert get_report("user_b", "shop_1", report["report_id"], db_path=db_path) is None
    assert len(list_reports("user_a", "shop_1", db_path=db_path)) == 1
