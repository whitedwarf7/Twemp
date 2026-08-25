"""Environment-driven settings and provider selection."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.workflow.demo_provider import DemoAgentProvider
from app.workflow.provider_factory import build_agent_provider


@pytest.fixture(autouse=True)
def clear_twemp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings read the process environment, so isolate each test from the real one."""
    for name in (
        "AGENT_PROVIDER",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_AGENTS_TRACING",
        "CORS_ALLOW_ORIGINS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_keep_the_app_credential_free() -> None:
    settings = Settings()

    assert settings.agent_provider == "demo"
    assert settings.openai_api_key == ""
    assert settings.openai_agents_tracing is False
    assert "http://localhost:3000" in settings.cors_allow_origins


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("OPENAI_AGENTS_TRACING", "true")

    settings = Settings()

    assert settings.agent_provider == "openai"
    assert settings.openai_model == "gpt-test"
    assert settings.openai_agents_tracing is True


def test_setting_names_are_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("agent_provider", "openai")
    assert Settings().agent_provider == "openai"


def test_unsupported_provider_values_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_PROVIDER", "anthropic")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://a.test", ["http://a.test"]),
        ("http://a.test,http://b.test", ["http://a.test", "http://b.test"]),
        ("  http://a.test ,  http://b.test  ", ["http://a.test", "http://b.test"]),
        ("http://a.test,,", ["http://a.test"]),
    ],
    ids=["single", "multiple", "padded", "trailing-separator"],
)
def test_cors_origins_are_parsed_from_a_comma_separated_string(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", raw)
    assert Settings().cors_allow_origins == expected


def test_cors_origins_accept_a_list_unchanged() -> None:
    origins = ["http://a.test", "http://b.test"]
    assert Settings(cors_allow_origins=origins).cors_allow_origins == origins


def test_settings_are_cached_for_the_process() -> None:
    assert get_settings() is get_settings()


def test_demo_mode_builds_the_deterministic_provider() -> None:
    provider = build_agent_provider(Settings(agent_provider="demo"))

    assert isinstance(provider, DemoAgentProvider)
    assert provider.mode == "demo"


def test_openai_mode_requires_a_server_side_key() -> None:
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is required"):
        build_agent_provider(Settings(agent_provider="openai", openai_api_key=""))
