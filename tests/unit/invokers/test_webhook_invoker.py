import pytest
from unittest import mock
from invokers.webhook_invoker import WebhookInvoker
from utils import decrypt_payload_fields

@pytest.fixture
def mock_decrypt_payload_fields(monkeypatch):
    def mock_decrypt(payload, fields, key):
        return {field: f"decrypted_{payload[field]}" for field in fields if field in payload}
    monkeypatch.setattr("utils.decrypt_payload_fields", mock_decrypt)

def test_decrypt_simple_fields(mock_decrypt_payload_fields):
    invoker = WebhookInvoker()
    msg = {
        "field1": "encrypted_value1",
        "field2": "encrypted_value2"
    }
    mapping = {
        "fieldsToDecryptJQExpressions": [".field1", ".field2"]
    }

    invoker._replace_encrypted_fields(msg, mapping)

    assert msg["field1"] == "decrypted_encrypted_value1"
    assert msg["field2"] == "decrypted_encrypted_value2"

def test_decrypt_complex_fields(mock_decrypt_payload_fields):
    invoker = WebhookInvoker()
    msg = {
        "nested": {
            "field1": "encrypted_value1",
            "field2": "encrypted_value2"
        },
        "field3": "encrypted_value3"
    }
    mapping = {
        "fieldsToDecryptJQExpressions": [".nested.field1", ".nested.field2", ".field3"]
    }

    invoker._replace_encrypted_fields(msg, mapping)

    assert msg["nested"]["field1"] == "decrypted_encrypted_value1"
    assert msg["nested"]["field2"] == "decrypted_encrypted_value2"
    assert msg["field3"] == "decrypted_encrypted_value3"

def test_partial_decryption(mock_decrypt_payload_fields):
    invoker = WebhookInvoker()
    msg = {
        "field1": "encrypted_value1",
        "field2": "encrypted_value2",
        "field3": "plain_value3"
    }
    mapping = {
        "fieldsToDecryptJQExpressions": [".field1", ".field2"]
    }

    invoker._replace_encrypted_fields(msg, mapping)

    assert msg["field1"] == "decrypted_encrypted_value1"
    assert msg["field2"] == "decrypted_encrypted_value2"
    assert msg["field3"] == "plain_value3"

def test_decrypt_with_complex_jq(mock_decrypt_payload_fields):
    invoker = WebhookInvoker()
    msg = {
        "field1": "encrypted_value1",
        "nested": {
            "field2": "encrypted_value2"
        },
        "field3": "plain_value3"
    }
    mapping = {
        "fieldsToDecryptJQExpressions": [".field1", ".nested.field2"]
    }

    invoker._replace_encrypted_fields(msg, mapping)

    assert msg["field1"] == "decrypted_encrypted_value1"
    assert msg["nested"]["field2"] == "decrypted_encrypted_value2"
    assert msg["field3"] == "plain_value3"
    assert msg == {
        "field1": "decrypted_encrypted_value1",
        "nested": {
            "field2": "decrypted_encrypted_value2"
        },
        "field3": "plain_value3"
    }