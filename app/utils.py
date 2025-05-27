import base64
import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional, Union

from Crypto.Cipher import AES
from requests import Response

logger = logging.getLogger(__name__)


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


def _traverse_path(
    data: Union[Dict[Any, Any], List[Any]], path: str
):
    parts = path.split(".")
    cur = data
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        yield cur, part, is_last
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                cur = None
        else:
            cur = None
        if cur is None and not is_last:
            break


def get_nested(
    data: Union[Dict[Any, Any], List[Any]], path: str
) -> Optional[Any]:
    cur = data
    for _, part, _ in _traverse_path(data, path):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def set_nested(
    data: Union[Dict[Any, Any], List[Any]], path: str, value: Any
) -> bool:
    for parent, part, is_last in _traverse_path(data, path):
        if is_last:
            if isinstance(parent, dict):
                parent[part] = value
                return True
            elif isinstance(parent, list):
                try:
                    parent[int(part)] = value
                    return True
                except (ValueError, IndexError):
                    return False
            else:
                return False
    return False


def decrypt_payload_fields(
    payload: Dict[str, Any], fields: List[str], key: str
) -> Dict[str, Any]:
    for path in fields:
        encrypted = get_nested(payload, path)
        if encrypted is not None:
            try:
                decrypted = decrypt_field(encrypted, key)
                set_nested(payload, path, decrypted)
            except Exception as e:
                logger.warning(f"Decryption failed for '{path}': {e}")
    return payload
