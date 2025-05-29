from typing import Any, Dict, List
from unittest import mock

import pytest
from glom import assign, glom
from glom.core import PathAssignError
from invokers.webhook_invoker import WebhookInvoker

from app.core.config import Mapping
from app.utils import decrypt_field, decrypt_payload_fields


def inplace_decrypt_mock(
    payload: Dict[str, Any], fields: List[str], key: str
) -> Dict[str, Any]:
    for field_path in fields:
        if not field_path:
            continue
        try:
            assign(payload, field_path, f"decrypted_{glom(payload, field_path)}")
        except Exception:
            # If the path does not exist, skip
            continue
    return payload


@mock.patch(
    "invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock
)
def test_decrypt_simple_fields(_mock_decrypt: object) -> None:
    invoker = WebhookInvoker()
    message: Dict[str, Any] = {
        "field1": "encrypted_value1",
        "field2": "encrypted_value2",
    }
    mapping = Mapping.construct()
    object.__setattr__(mapping, "fieldsToDecryptPaths", ["field1", "field2"])
    invoker._replace_encrypted_fields(message, mapping)
    assert message["field1"] == "decrypted_encrypted_value1"
    assert message["field2"] == "decrypted_encrypted_value2"


@mock.patch(
    "invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock
)
def test_decrypt_complex_fields(_mock_decrypt: object) -> None:
    invoker = WebhookInvoker()
    msg: Dict[str, Any] = {
        "nested": {"field1": "encrypted_value1", "field2": "encrypted_value2"},
        "field3": "encrypted_value3",
    }
    mapping = Mapping.construct()
    object.__setattr__(
        mapping, "fieldsToDecryptPaths", ["nested.field1", "nested.field2", "field3"]
    )
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
    mapping = Mapping.construct()
    object.__setattr__(mapping, "fieldsToDecryptPaths", ["field1", "field2"])
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
    mapping = Mapping.construct()
    object.__setattr__(mapping, "fieldsToDecryptPaths", ["field1", "nested.field2"])
    invoker._replace_encrypted_fields(msg, mapping)
    assert msg["field1"] == "decrypted_encrypted_value1"
    assert msg["nested"]["field2"] == "decrypted_encrypted_value2"
    assert msg["field3"] == "plain_value3"
    assert msg == {
        "field1": "decrypted_encrypted_value1",
        "nested": {"field2": "decrypted_encrypted_value2"},
        "field3": "plain_value3",
    }


def encrypt_field(plain_text: str, key: str) -> str:
    import base64
    import os

    from Crypto.Cipher import AES

    key_bytes = key.encode("utf-8")
    if len(key_bytes) < 32:
        raise ValueError("Encryption key must be at least 32 bytes")
    key_bytes = key_bytes[:32]
    iv = os.urandom(16)
    cipher = AES.new(key_bytes, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(plain_text.encode("utf-8"))
    encrypted_data = iv + ciphertext + tag
    return base64.b64encode(encrypted_data).decode("utf-8")


def test_decrypt_payload_fields_complex() -> None:
    # Simulate a nested payload with encrypted fields
    key = "a" * 32
    encrypted_value = encrypt_field("secret_value", key)
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
    result = decrypt_payload_fields(payload, fields_to_decrypt, key)
    assert result["level1"]["level2"]["secret"] == "secret_value"
    assert result["top_secret"] == "secret_value"
    assert result["level1"]["list"][0]["deep"]["secret"] == "secret_value"
    assert result["level1"]["level2"]["other"] == "not encrypted"
    assert result["level1"]["list"][1]["deep"]["not_secret"] == "foo"


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


def test_get_nested_and_set_nested() -> None:
    data = {
        "a": {"b": [1, {"c": "value"}]},
        "x": [0, {"y": "z"}],
    }
    # Test glom (get_nested)
    assert glom(data, "a.b.1.c") == "value"
    assert glom(data, "x.1.y") == "z"
    assert glom(data, "a.b.2", default=None) is None
    assert glom(data, "a.b.1.d", default=None) is None
    # Test assign (set_nested)
    assign(data, "a.b.1.c", 42)
    assert dict(data["a"]["b"][1])["c"] == 42
    assign(data, "x.1.y", "changed")
    assert dict(data["x"][1])["y"] == "changed"
    # assign will create missing keys in dicts, but not in lists
    with pytest.raises(PathAssignError):
        assign(data, "a.b.2", "fail")
    assign(data, "a.b.1.d", "fail")
    assert dict(data["a"]["b"][1])["d"] == "fail"
