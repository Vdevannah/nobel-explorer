"""Agent configuration: defaults, validation, secrets and availability (Pydantic only)."""

import pytest

from backend.ai.agent.config import AgentConfig, AgentConfigError, load_agent_config

SECRET = "sk-test-SECRET-value-123"


def test_defaults_are_conservative_and_disabled():
    config = load_agent_config({})
    assert config.enabled is False and config.openai_api_key is None
    assert config.model == "gpt-6-luna"  # replacement for deprecated gpt-4.1-mini
    assert config.reasoning_effort == "none" and config.temperature is None
    assert (config.max_question_chars, config.max_model_calls, config.max_tool_calls) == (1000, 6, 8)
    assert (config.max_duration_seconds, config.max_output_tokens) == (45.0, 800)
    assert (config.provider_timeout_seconds, config.provider_max_retries) == (20.0, 1)
    assert config.recursion_limit == 58  # backstop only (8 * 6 + 10)


def test_environment_overrides():
    config = load_agent_config({
        "AI_AGENT_ENABLED": "true", "OPENAI_API_KEY": SECRET, "OPENAI_MODEL": "gpt-4.1",
        "AI_AGENT_MAX_MODEL_CALLS": "4", "AI_AGENT_MAX_TOOL_CALLS": "3", "AI_AGENT_MAX_DURATION_SECONDS": "30",
        "AI_AGENT_PROVIDER_TIMEOUT_SECONDS": "10", "AI_AGENT_PROVIDER_MAX_RETRIES": "0",
    })
    assert config.enabled and config.model == "gpt-4.1"
    assert (config.max_model_calls, config.max_tool_calls, config.max_duration_seconds) == (4, 3, 30.0)
    assert config.openai_api_key.get_secret_value() == SECRET


@pytest.mark.parametrize("env", [
    {"AI_AGENT_ENABLED": "maybe"},
    {"AI_AGENT_MAX_MODEL_CALLS": "100"},
    {"AI_AGENT_MAX_TOOL_CALLS": "0"},
    {"AI_AGENT_MAX_DURATION_SECONDS": "1"},
    {"AI_AGENT_MAX_OUTPUT_TOKENS": "abc"},
    {"OPENAI_MODEL": "gpt 4; rm -rf /"},
    {"AI_AGENT_PROVIDER_TIMEOUT_SECONDS": "50", "AI_AGENT_MAX_DURATION_SECONDS": "45"},
])
def test_invalid_configuration_rejected(env):
    with pytest.raises(AgentConfigError):
        load_agent_config(env)


def test_errors_never_echo_the_api_key():
    with pytest.raises(AgentConfigError) as info:
        load_agent_config({"OPENAI_API_KEY": SECRET, "AI_AGENT_MAX_TOOL_CALLS": "999"})
    assert SECRET not in str(info.value)
    assert "AI_AGENT_MAX_TOOL_CALLS" in str(info.value)


def test_api_key_is_masked_in_repr_and_dump():
    config = AgentConfig(enabled=True, openai_api_key=SECRET)
    assert SECRET not in repr(config) and SECRET not in str(config.model_dump()) and SECRET not in config.model_dump_json()


@pytest.mark.parametrize("config, available, reason", [
    (AgentConfig(), False, "disabled"),
    (AgentConfig(enabled=True), False, "OPENAI_API_KEY is missing"),
    (AgentConfig(enabled=True, openai_api_key="  "), False, "OPENAI_API_KEY is missing"),
    (AgentConfig(enabled=True, openai_api_key=SECRET), True, None),
])
def test_availability(config, available, reason):
    ok, message = config.availability()
    assert ok is available
    assert (message is None) if reason is None else (reason in message)


def test_config_is_immutable():
    with pytest.raises(Exception):
        AgentConfig().max_tool_calls = 100


def test_reasoning_effort_and_temperature_from_environment():
    config = load_agent_config({"AI_AGENT_REASONING_EFFORT": "unset", "AI_AGENT_TEMPERATURE": "0.3"})
    assert config.reasoning_effort is None and config.temperature == 0.3
    with pytest.raises(AgentConfigError):
        load_agent_config({"AI_AGENT_REASONING_EFFORT": "high"})  # tool calling on Chat Completions needs "none"
