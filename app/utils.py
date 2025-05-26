import base64
import hashlib
import hmac
import logging
from typing import Dict, Any, Optional, List, Union

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


def get_nested(obj: Union[Dict, List], path: str) -> Optional[Any]:
    parts = path.split(".")
    for part in parts:
        if isinstance(obj, dict):
            if part not in obj:
                return None
            obj = obj[part]
        elif isinstance(obj, list):
            try:
                idx = int(part)
                obj = obj[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return obj


def set_nested(obj: Union[Dict, List], path: str, value: Any) -> None:
    parts = path.split(".")
    for part in parts[:-1]:
        if isinstance(obj, dict):
            if part not in obj or not isinstance(obj[part], (dict, list)):
                return
            obj = obj[part]
        elif isinstance(obj, list):
            try:
                idx = int(part)
                obj = obj[idx]
            except (ValueError, IndexError):
                return
        else:
            return

    last = parts[-1]
    if isinstance(obj, dict) and last in obj:
        obj[last] = value
    elif isinstance(obj, list):
        try:
            idx = int(last)
            if 0 <= idx < len(obj):
                obj[idx] = value
        except ValueError:
            return


def decrypt_payload_fields(payload: Dict[str, Any], fields_to_decrypt: List[str], key: str) -> Dict[str, Any]:
    for path in fields_to_decrypt:
        encrypted_value = get_nested(payload, path)
        if encrypted_value is not None:
            try:
                decrypted_value = decrypt_field(encrypted_value, key)
                set_nested(payload, path, decrypted_value)
            except Exception as e:
                logger.warning(f"Decryption failed for '{path}': {e}")
    return payload