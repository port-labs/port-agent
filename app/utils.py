import base64
import hashlib
import hmac
import logging
from typing import Any, Callable, Dict, List, Optional

from Crypto.Cipher import AES
from glom import assign, glom
from requests import Response

from core.config import settings

logger = logging.getLogger(__name__)


def log_with_verbose(
    log_fn: Callable,
    base_msg: str,
    base_args: list,
    verbose_field: Optional[str] = None,
    verbose_value: Any = None,
) -> None:
    """Add verbose field to logs based on VERBOSE_LOGGING."""
    msg = base_msg
    if settings.VERBOSE_LOGGING and verbose_field and verbose_value is not None:
        msg += f", {verbose_field}: %s"
        base_args.append(verbose_value)
    log_fn(msg, *base_args)


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
