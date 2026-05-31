import base64
import hashlib
import hmac
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from core.config import settings
from Crypto.Cipher import AES
from glom import assign, glom
from requests import Response

logger = logging.getLogger(__name__)

REDACTED = "***REDACTED***"
_MAX_LOG_DEPTH = 20

_SENSITIVE_KEY_NAMES = frozenset(
    {
        "authorization",
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "accesstoken",
        "refresh_token",
        "id_token",
        "client_secret",
        "clientsecret",
        "client_id",
        "clientid",
        "api_key",
        "apikey",
        "x_api_key",
        "cookie",
        "set_cookie",
        "x_port_signature",
        "private_key",
        "credential",
        "credentials",
    }
)

_SENSITIVE_KEY_SUFFIXES = ("_secret", "_token", "_password", "_api_key")

_BEARER_TOKEN_PATTERN = re.compile(r"(?i)(Bearer\s+)[^\s,;]+")
_JWT_PATTERN = re.compile(
    r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in _SENSITIVE_KEY_NAMES:
        return True
    return any(normalized.endswith(suffix) for suffix in _SENSITIVE_KEY_SUFFIXES)


def _known_secret_values() -> list[str]:
    values: list[str] = []
    for value in (settings.PORT_CLIENT_SECRET, settings.PORT_CLIENT_ID):
        if value:
            values.append(value)
    return sorted(values, key=len, reverse=True)


def _redact_string(value: str) -> str:
    redacted = value
    for secret in _known_secret_values():
        redacted = redacted.replace(secret, REDACTED)
    redacted = _BEARER_TOKEN_PATTERN.sub(r"\1" + REDACTED, redacted)
    redacted = _JWT_PATTERN.sub(REDACTED, redacted)
    return redacted


def sanitize_for_log(value: Any, *, _depth: int = 0) -> Any:
    """Return a copy of value safe for logging (secrets and tokens redacted)."""
    if _depth > _MAX_LOG_DEPTH:
        return REDACTED

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, bytes):
        try:
            return sanitize_for_log(value.decode("utf-8"), _depth=_depth + 1)
        except UnicodeDecodeError:
            return REDACTED

    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                sanitized = sanitize_for_log(json.loads(value), _depth=_depth + 1)
                return json.dumps(sanitized)
            except (json.JSONDecodeError, TypeError):
                pass
        return _redact_string(value)

    if isinstance(value, dict):
        return {
            key: REDACTED
            if _is_sensitive_key(str(key))
            else sanitize_for_log(item, _depth=_depth + 1)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        sanitized = [sanitize_for_log(item, _depth=_depth + 1) for item in value]
        if isinstance(value, tuple):
            return tuple(sanitized)
        if isinstance(value, set):
            return set(sanitized)
        return sanitized

    return _redact_string(str(value))


def log_by_detail_level(
    log_fn: Callable,
    base_message_format: str,
    base_format_args: list,
    optional_field_name: Optional[str] = None,
    optional_field_value: Any = None,
) -> None:
    """Log with detail level based on DETAILED_LOGGING config.

    Logs concisely (base message only) when DETAILED_LOGGING=False, or with one
    additional optional field when DETAILED_LOGGING=True.
    """
    msg = base_message_format
    if (
        settings.DETAILED_LOGGING
        and optional_field_name
        and optional_field_value is not None
    ):
        msg += f", {optional_field_name}: %s"
        log_fn(msg, *base_format_args, optional_field_value)
    else:
        log_fn(msg, *base_format_args)


def response_to_dict(response: Response) -> dict:
    response_dict = {
        "statusCode": response.status_code,
        "headers": dict(response.headers),
        "text": response.text,
        "json": None,
    }

    try:
        response_dict["json"] = response.json()
    except ValueError:
        logger.debug(
            "Failed to parse response body as JSON: Response is not JSON serializable"
        )

    return response_dict


def get_invocation_method_object(body: dict) -> dict:
    return body.get("payload", {}).get("action", {}).get("invocationMethod", {})


def get_response_body(response: Response) -> dict | str | None:
    try:
        return response.json()
    except ValueError:
        return response.text


def sign_sha_256(input: str, secret: str, timestamp: str) -> str:
    to_sign = f"{timestamp}.{input}"
    new_hmac = hmac.new(bytes(secret, "utf-8"), digestmod=hashlib.sha256)
    new_hmac.update(bytes(to_sign, "utf-8"))
    signed = base64.b64encode(new_hmac.digest()).decode("utf-8")
    return f"v1,{signed}"


def decrypt_field(encrypted_value: str, key: str) -> str:
    encrypted_data = base64.b64decode(encrypted_value)
    if len(encrypted_data) < 32:
        raise ValueError("Encrypted data is too short")

    iv = encrypted_data[:16]
    ciphertext = encrypted_data[16:-16]
    tag = encrypted_data[-16:]

    key_bytes = key.encode("utf-8")
    if len(key_bytes) < 32:
        raise ValueError("Encryption key must be at least 32 bytes")
    key_bytes = key_bytes[:32]

    cipher = AES.new(key_bytes, AES.MODE_GCM, nonce=iv)
    decrypted = cipher.decrypt_and_verify(ciphertext, tag)
    return decrypted.decode("utf-8")


def decrypt_payload_fields(
    payload: Dict[str, Any], fields: List[str], key: str
) -> Dict[str, Any]:
    for path in fields:
        encrypted = glom(payload, path, default=None)
        if encrypted is not None:
            try:
                decrypted = decrypt_field(encrypted, key)
                assign(payload, path, decrypted)
            except Exception as e:
                logger.warning("Decryption failed for '%s': %s", path, e)
    return payload
