from unittest import mock
from invokers.webhook_invoker import WebhookInvoker

def inplace_decrypt_mock(payload, fields, key):
    for field in fields:
        if not field:
            continue
        # Remove leading dot for jq-style paths
        field_path = field[1:] if field.startswith('.') else field
        parts = field_path.split('.')
        d = payload
        for p in parts[:-1]:
            if p in d:
                d = d[p]
            else:
                d = None
                break
        if d is not None and parts[-1] in d:
            d[parts[-1]] = f"decrypted_{d[parts[-1]]}"
    return payload

@mock.patch.object(WebhookInvoker, "_apply_jq_on_field", side_effect=lambda fields, body: fields)
@mock.patch("invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock)
def test_decrypt_simple_fields(_mock_decrypt, _mock_jq):
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

@mock.patch.object(WebhookInvoker, "_apply_jq_on_field", side_effect=lambda fields, body: fields)
@mock.patch("invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock)
def test_decrypt_complex_fields(_mock_decrypt, _mock_jq):
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

@mock.patch.object(WebhookInvoker, "_apply_jq_on_field", side_effect=lambda fields, body: fields)
@mock.patch("invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock)
def test_partial_decryption(_mock_decrypt, _mock_jq):
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

@mock.patch.object(WebhookInvoker, "_apply_jq_on_field", side_effect=lambda fields, body: fields)
@mock.patch("invokers.webhook_invoker.decrypt_payload_fields", side_effect=inplace_decrypt_mock)
def test_decrypt_with_complex_jq(_mock_decrypt, _mock_jq):
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