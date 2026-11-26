"""LangChain integration: names, schemas, direct invocation, registry."""

import json
import sys

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("chromadb")

from langchain_core.messages import ToolMessage  # noqa: E402
from langchain_core.tools import BaseTool  # noqa: E402

from backend.ai.tools.registry import TOOL_NAMES  # noqa: E402

EXPECTED_ARGS = {
    "search_laureates": {"name", "year", "category", "birth_country", "gender", "limit"},
    "get_laureate_details": {"laureate_id", "include_explanation_level"},
    "get_nobel_statistics": {"operation", "category", "start_year", "end_year", "affiliation_country", "limit"},
    "search_nobel_knowledge": {"query", "level", "laureate_id", "k", "dedupe_by_document"},
}
REQUIRED = {
    "search_laureates": set(),
    "get_laureate_details": {"laureate_id"},
    "get_nobel_statistics": {"operation"},
    "search_nobel_knowledge": {"query"},
}


def test_registry_contains_exactly_four_tools(tools):
    assert tuple(tools) == TOOL_NAMES == (
        "search_laureates", "get_laureate_details", "get_nobel_statistics", "search_nobel_knowledge")
    assert all(isinstance(t, BaseTool) for t in tools.values())


@pytest.mark.parametrize("name", TOOL_NAMES)
def test_tool_schema_and_description(tools, name):
    tool = tools[name]
    assert tool.name == name
    assert len(tool.description) > 80 and "Use" in tool.description
    schema = tool.tool_call_schema.model_json_schema()
    assert set(schema["properties"]) == EXPECTED_ARGS[name]
    assert set(schema.get("required", [])) == REQUIRED[name]
    # The LLM-facing tool_call_schema is derived by LangChain and omits
    # additionalProperties; the validating args_schema forbids extra fields.
    assert tool.args_schema.model_json_schema().get("additionalProperties") is False
    for prop in schema["properties"].values():
        assert prop.get("description")


def test_category_enum_exposed_in_schema(tools):
    schema = tools["search_laureates"].tool_call_schema.model_json_schema()
    text = json.dumps(schema["properties"]["category"])
    for category in ("Chemistry", "Economic Sciences", "Physiology or Medicine"):
        assert category in text


def test_operation_enum_exposed_in_schema(tools):
    text = json.dumps(tools["get_nobel_statistics"].tool_call_schema.model_json_schema()["properties"]["operation"])
    assert "top_birth_countries" in text and "laureates_by_affiliation_institution" in text


def test_direct_invoke_returns_envelope(tools):
    result = tools["search_laureates"].invoke({"year": 2022, "category": "Chemistry"})
    assert result["tool"] == "search_laureates" and result["ok"] is True


def test_validation_errors_use_the_same_envelope(tools):
    for name, args in [("search_laureates", {"year": "not-a-year"}), ("get_laureate_details", {}),
                       ("get_nobel_statistics", {"operation": "delete_all"}),
                       ("search_nobel_knowledge", {"query": "x", "unexpected": True})]:
        result = tools[name].invoke(args)
        assert result["ok"] is False and result["tool"] == name
        assert result["error"]["type"] == "validation_error"


def test_tool_call_invocation_returns_json_tool_message(tools):
    message = tools["get_nobel_statistics"].invoke(
        {"type": "tool_call", "id": "call-1", "name": "get_nobel_statistics", "args": {"operation": "summary"}})
    assert isinstance(message, ToolMessage) and message.tool_call_id == "call-1"
    payload = json.loads(message.content)
    assert payload["ok"] is True and payload["data"]["result"]["laureate_prize_awards"] == 15


def test_invalid_tool_call_returns_json_error_message(tools):
    message = tools["search_laureates"].invoke(
        {"type": "tool_call", "id": "call-2", "name": "search_laureates", "args": {"category": "Mathematics"}})
    payload = json.loads(message.content)
    assert payload["ok"] is False and "Mathematics" in payload["error"]["message"]


@pytest.mark.parametrize("name, args", [
    ("search_laureates", {"name": "Curie"}),
    ("get_laureate_details", {"laureate_id": 249, "include_explanation_level": "Expert"}),
    ("get_nobel_statistics", {"operation": "women_by_era"}),
    ("search_nobel_knowledge", {"query": "mRNA immune system", "k": 5}),
])
def test_all_outputs_are_json_serialisable(tools, name, args):
    result = tools[name].invoke(args)
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_plain_functions_work_without_langchain_invoke(tool_context):
    from backend.ai.tools.langchain_tools import build_tool_functions

    functions = build_tool_functions(tool_context)
    assert functions["search_laureates"](year=2022, category="Chemistry")["data"]["total_matches"] == 3
    assert functions["search_laureates"](year=1800)["ok"] is False


def test_no_chat_model_or_agent_is_loaded(tools):
    for module in ("langchain_openai", "openai"):
        assert module not in sys.modules, f"{module} should not be imported by the tool layer"


@pytest.mark.parametrize("name", TOOL_NAMES)
def test_schemas_use_standard_json_schema_bounds(tools, name):
    # Regression: Field constraints placed after a BeforeValidator rendered as
    # non-standard "ge"/"le" keys, which LLM providers ignore.
    text = json.dumps(tools[name].tool_call_schema.model_json_schema())
    assert '"ge"' not in text and '"le"' not in text


def test_bounds_are_visible_to_the_llm(tools):
    year = tools["search_laureates"].tool_call_schema.model_json_schema()["properties"]["year"]["anyOf"][0]
    assert year["minimum"] == 1901 and year["type"] == "integer"
    k = tools["search_nobel_knowledge"].tool_call_schema.model_json_schema()["properties"]["k"]
    assert (k["minimum"], k["maximum"]) == (1, 10)
