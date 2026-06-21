from agent_api.tool_schemas import (
    build_tool_descriptions_text,
    get_agent_tool_names,
    get_agent_tool_schemas,
    get_tool_schema,
    validate_tool_name,
)


def test_get_agent_tool_schemas_returns_list():
    schemas = get_agent_tool_schemas()
    assert isinstance(schemas, list)
    assert schemas


def test_tool_schemas_include_cashflow_summary():
    assert "get_cashflow_summary" in get_agent_tool_names()


def test_get_agent_tool_names_returns_list():
    names = get_agent_tool_names()
    assert isinstance(names, list)
    assert "get_full_context_summary" in names


def test_get_tool_schema_returns_named_schema():
    schema = get_tool_schema("get_cashflow_summary")
    assert schema["name"] == "get_cashflow_summary"


def test_validate_tool_name():
    assert validate_tool_name("get_cashflow_summary") is True
    assert validate_tool_name("missing_tool") is False


def test_build_tool_descriptions_text_returns_string():
    text = build_tool_descriptions_text()
    assert isinstance(text, str)
    assert "get_cashflow_summary" in text


def test_tool_descriptions_are_not_empty():
    for schema in get_agent_tool_schemas():
        assert schema["description"]
