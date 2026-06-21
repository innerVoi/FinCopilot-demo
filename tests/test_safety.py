from src.safety import (
    append_disclaimer,
    build_finance_safety_instruction,
    get_disclaimer,
    sanitize_llm_output,
)


def test_get_disclaimer_returns_non_empty_string():
    assert isinstance(get_disclaimer(), str)
    assert get_disclaimer()


def test_append_disclaimer_adds_disclaimer():
    result = append_disclaimer("测试文本")

    assert "测试文本" in result
    assert get_disclaimer() in result


def test_sanitize_llm_output_contains_disclaimer():
    result = sanitize_llm_output("模型输出")

    assert get_disclaimer() in result


def test_build_finance_safety_instruction_returns_instruction():
    instruction = build_finance_safety_instruction()

    assert "不得" in instruction
    assert "投资" in instruction
    assert "税务" in instruction
