"""Boundary guard that blocks credential-shaped content before it reaches a provider."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.workflow.schemas import DEFAULT_INCIDENT
from app.workflow.security import contains_likely_secret


@pytest.mark.parametrize(
    "value",
    [
        "sk-" + "a" * 16,
        "sk-" + "A1b2C3d4E5f6G7h8i9",
        "token sk-abcdefghijklmnop embedded in prose",
        "sk-abc_def-ghi_jkl-mno1",
    ],
    ids=["min-length", "mixed-case", "embedded", "with-separators"],
)
def test_openai_style_keys_are_detected(value: str) -> None:
    assert contains_likely_secret({"note": value}) is True


@pytest.mark.parametrize(
    "value",
    ["sk-short", "sk-", "risk-assessment-completed-today", "ask-the-team-for-details"],
)
def test_short_or_incidental_sk_sequences_are_not_flagged(value: str) -> None:
    assert contains_likely_secret({"note": value}) is False


@pytest.mark.parametrize(
    "header",
    [
        # These are PEM header markers used as detection fixtures, not real key material.
        "-----BEGIN PRIVATE KEY-----",  # gitleaks:allow
        "-----BEGIN RSA PRIVATE KEY-----",  # gitleaks:allow
        "-----BEGIN EC PRIVATE KEY-----",  # gitleaks:allow
        "-----BEGIN OPENSSH PRIVATE KEY-----",  # gitleaks:allow
    ],
)
def test_private_key_blocks_are_detected(header: str) -> None:
    assert (
        contains_likely_secret({"description": f"{header}\nMIIEvQIBADAN"}) is True
    )  # gitleaks:allow


@pytest.mark.parametrize(
    "value",
    [
        "api_key=abc123",
        "apikey: abc123",
        "api-key = abc123",
        "API_KEY=abc123",
        "access_token=abc123",
        "accesstoken:abc123",
        "access-token = abc123",
        "client_secret=abc123",
        "clientsecret: abc123",
    ],
)
def test_credential_assignments_are_detected(value: str) -> None:
    assert contains_likely_secret({"note": value}) is True


@pytest.mark.parametrize(
    "value",
    [
        "The team rotated every api key after the incident",
        "Access tokens expired during the outage",
        "client secret rotation is scheduled",
        "api_key",
    ],
    ids=["prose-api-key", "prose-token", "prose-secret", "no-delimiter"],
)
def test_prose_without_an_assigned_value_is_not_flagged(value: str) -> None:
    assert contains_likely_secret({"description": value}) is False


def test_an_empty_assignment_still_fails_closed() -> None:
    """`api_key=` carries no secret, but the guard deliberately errs toward blocking."""
    assert contains_likely_secret({"description": "api_key="}) is True


def test_the_default_incident_is_not_flagged() -> None:
    assert contains_likely_secret(DEFAULT_INCIDENT.model_dump(mode="json")) is False


def test_secrets_are_found_inside_nested_structures() -> None:
    payload = {
        "incident": {"signals": ["latency high", {"deep": ["api_key=leaked-value"]}]},
    }
    assert contains_likely_secret(payload) is True


def test_non_json_serializable_values_do_not_raise() -> None:
    payload = {"observed_at": datetime(2026, 8, 25, tzinfo=UTC)}
    assert contains_likely_secret(payload) is False


def test_plain_strings_and_empty_payloads_are_supported() -> None:
    assert contains_likely_secret("api_key=leaked-value") is True
    assert contains_likely_secret({}) is False
    assert contains_likely_secret([]) is False
    assert contains_likely_secret(None) is False
