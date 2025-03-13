import base64
import hashlib
import hmac
import logging
from cryptography.fernet import Fernet
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
    fernet = Fernet(key)
    decrypted_value = fernet.decrypt(encrypted_value.encode()).decode()
    return decrypted_value

def decrypt_payload_fields(payload: dict, fields_to_decrypt: list, key: str) -> dict:
    for field in fields_to_decrypt:
        if field in payload:
            payload[field] = decrypt_field(payload[field], key)
    return payload