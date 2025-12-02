import base64
import hashlib
import hmac
import logging
from typing import Any, Callable, Dict, List, Optional

from core.config import settings
from Crypto.Cipher import AES
from glom import assign, glom
from requests import Response

logger = logging.getLogger(__name__)


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
        base_format_args.append(optional_field_value)
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
