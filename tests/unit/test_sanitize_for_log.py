from unittest import mock

import pytest

from app.utils import REDACTED, log_by_detail_level, sanitize_for_log


@pytest.fixture
def secrets() -> None:
    with mock.patch("app.utils.settings") as settings:
        settings.PORT_CLIENT_SECRET = "super-secret-value"
        settings.PORT_CLIENT_ID = "client-id-value"
        settings.DETAILED_LOGGING = True
        yield


def test_redacts_sensitive_dict_keys(secrets: None) -> None:
    payload = {
        "authorization": "Bearer abc.def.ghi",
        "body": {"token": "nested-token", "name": "safe"},
    }
    sanitized = sanitize_for_log(payload)
    assert sanitized["authorization"] == REDACTED
    assert sanitized["body"]["token"] == REDACTED
    assert sanitized["body"]["name"] == "safe"


def test_redacts_bearer_tokens_in_strings(secrets: None) -> None:
    value = "Auth failed: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig"
    sanitized = sanitize_for_log(value)
    assert "Bearer" in sanitized
    assert "eyJhbGci" not in sanitized
    assert REDACTED in sanitized


def test_redacts_configured_secret_substrings(secrets: None) -> None:
    sanitized = sanitize_for_log("Error: super-secret-value leaked")
    assert "super-secret-value" not in sanitized
    assert REDACTED in sanitized


def test_parses_json_strings(secrets: None) -> None:
    raw = '{"accessToken": "token-value", "ok": true}'
    sanitized = sanitize_for_log(raw)
    assert sanitized["accessToken"] == REDACTED
    assert sanitized["ok"] is True


def test_log_by_detail_level_sanitizes_optional_field(secrets: None) -> None:
    messages: list[str] = []

    def capture(message: str, *args: object) -> None:
        messages.append(message % args)

    log_by_detail_level(
        capture,
        "event - id: %s",
        ["run-1"],
        "payload",
        {"clientSecret": "super-secret-value"},
    )

    assert len(messages) == 1
    assert "super-secret-value" not in messages[0]
    assert REDACTED in messages[0]
