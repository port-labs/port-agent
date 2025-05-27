import pytest
from unittest import mock
import app.utils as utils
from app.utils import decrypt_payload_fields, decrypt_field
from invokers.webhook_invoker import WebhookInvoker
from typing import Any, Dict, List


def inplace_decrypt_mock(
    payload: Dict[str, Any], fields: List[str], key: str
) -> Dict[str, Any]:
    for field in fields:
        if not field:
            continue
        parts = field.split(".")
        d = payload
        valid = True
        for p in parts[:-1]:
            if isinstance(d, dict) and p in d:
                d = d[p]
            else:
                valid = False
                break
        if valid and d is not None and isinstance(d, dict) and parts[-1] in d:
            d[parts[-1]] = f"decrypted_{d[parts[-1]]}"
    return payload


@mock.patch(
    "invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock
)
def test_decrypt_simple_fields(_mock_decrypt: object) -> None:
    invoker = WebhookInvoker()
    msg: Dict[str, Any] = {"field1": "encrypted_value1", "field2": "encrypted_value2"}
    mapping = {"fieldsToDecryptPaths": ["field1", "field2"]}
    invoker._replace_encrypted_fields(msg, mapping)
    assert msg["field1"] == "decrypted_encrypted_value1"
    assert msg["field2"] == "decrypted_encrypted_value2"


@mock.patch(
    "invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock
)
def test_decrypt_complex_fields(_mock_decrypt: object) -> None:
    invoker = WebhookInvoker()
    msg: Dict[str, Any] = {
        "nested": {"field1": "encrypted_value1", "field2": "encrypted_value2"},
        "field3": "encrypted_value3",
    }
    mapping = {"fieldsToDecryptPaths": ["nested.field1", "nested.field2", "field3"]}
    invoker._replace_encrypted_fields(msg, mapping)
    assert msg["nested"]["field1"] == "decrypted_encrypted_value1"
    assert msg["nested"]["field2"] == "decrypted_encrypted_value2"
    assert msg["field3"] == "decrypted_encrypted_value3"


@mock.patch(
    "invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock
)
def test_partial_decryption(_mock_decrypt: object) -> None:
    invoker = WebhookInvoker()
    msg: Dict[str, Any] = {
        "field1": "encrypted_value1",
        "field2": "encrypted_value2",
        "field3": "plain_value3",
    }
    mapping = {"fieldsToDecryptPaths": ["field1", "field2"]}
    invoker._replace_encrypted_fields(msg, mapping)
    assert msg["field1"] == "decrypted_encrypted_value1"
    assert msg["field2"] == "decrypted_encrypted_value2"
    assert msg["field3"] == "plain_value3"


@mock.patch(
    "invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock
)
def test_decrypt_with_complex_jq(_mock_decrypt: object) -> None:
    invoker = WebhookInvoker()
    msg: Dict[str, Any] = {
        "field1": "encrypted_value1",
        "nested": {"field2": "encrypted_value2"},
        "field3": "plain_value3",
    }
    mapping = {"fieldsToDecryptPaths": ["field1", "nested.field2"]}
    invoker._replace_encrypted_fields(msg, mapping)
    assert msg["field1"] == "decrypted_encrypted_value1"
    assert msg["nested"]["field2"] == "decrypted_encrypted_value2"
    assert msg["field3"] == "plain_value3"
    assert msg == {
        "field1": "decrypted_encrypted_value1",
        "nested": {"field2": "decrypted_encrypted_value2"},
        "field3": "plain_value3",
    }


def test_decrypt_payload_fields_complex() -> None:
    # Simulate a nested payload with encrypted fields
    encrypted_value = (
        "U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+"
        "U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+"
        "U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+"
        "U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+"
        "U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+"
        "U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+U2FsdGVkX1+"
        "U2FsdGVkX1+U2FsdGVkX1+"
    )
    payload = {
        "level1": {
            "level2": {"secret": encrypted_value, "other": "not encrypted"},
            "list": [
                {"deep": {"secret": encrypted_value}},
                {"deep": {"not_secret": "foo"}},
            ],
        },
        "top_secret": encrypted_value,
    }
    fields_to_decrypt = [
        "level1.level2.secret",
        "top_secret",
        "level1.list.0.deep.secret",
    ]
    key = "a" * 32
    original_decrypt_field = utils.decrypt_field
    utils.decrypt_field = lambda v, k: "decrypted"
    try:
        result = decrypt_payload_fields(payload, fields_to_decrypt, key)
        assert result["level1"]["level2"]["secret"] == "decrypted"
        assert result["top_secret"] == "decrypted"
        assert result["level1"]["list"][0]["deep"]["secret"] == "decrypted"
        assert result["level1"]["level2"]["other"] == "not encrypted"
        assert result["level1"]["list"][1]["deep"]["not_secret"] == "foo"
    finally:
        utils.decrypt_field = original_decrypt_field


def test_decrypt_field_too_short() -> None:
    with pytest.raises(ValueError, match="Encrypted data is too short"):
        decrypt_field("aGVsbG8=", "a" * 32)


def test_decrypt_field_key_too_short() -> None:
    import base64
    # 32 bytes of data
    data = base64.b64encode(b"a" * 32).decode()
    with pytest.raises(ValueError, match="Encryption key must be at least 32 bytes"):
        decrypt_field(data, "short")


def test_decrypt_field_decrypt_failure() -> None:
    import base64
    # 48 bytes: 16 IV + 16 ciphertext + 16 tag
    data = base64.b64encode(b"a" * 48).decode()
    with pytest.raises(Exception):
        decrypt_field(data, "a" * 32)


def test_decrypt_payload_fields_decrypt_exception() -> None:
    payload = {"a": "encrypted"}

    def bad_decrypt_field(val: str, key: str) -> None:
        raise Exception("fail")

    with mock.patch("app.utils.decrypt_field", bad_decrypt_field):
        result = decrypt_payload_fields(payload, ["a"], "key")
        assert result["a"] == "encrypted"
