import logging
from io import StringIO
from unittest import mock

import pytest

from app.core.logging import SanitizeLogFilter, configure_sanitized_logging
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


def test_sanitize_log_filter_redacts_format_args(secrets: None) -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event - id: %s, payload: %s",
        args=("run-1", {"clientSecret": "super-secret-value"}),
        exc_info=None,
    )

    SanitizeLogFilter().filter(record)
    message = record.getMessage()

    assert "super-secret-value" not in message
    assert REDACTED in message


def test_log_by_detail_level_sanitized_via_logging_filter(secrets: None) -> None:
    stream = StringIO()
    configure_sanitized_logging("DEBUG")

    root = logging.getLogger()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(SanitizeLogFilter())
    root.handlers = [handler]

    test_logger = logging.getLogger("test.detail")
    test_logger.setLevel(logging.DEBUG)

    log_by_detail_level(
        test_logger.info,
        "event - id: %s",
        ["run-1"],
        "payload",
        {"clientSecret": "super-secret-value"},
    )

    output = stream.getvalue()
    assert "super-secret-value" not in output
    assert REDACTED in output
