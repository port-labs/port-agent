from unittest.mock import patch

import pytest
from processors.polling.polling_to_webhook_processor import PollingToWebhookProcessor


@pytest.fixture
def sample_run():
    return {
        "_id": "run_123",
        "id": "run_123",
        "payload": {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "synchronized": False,
            "method": "POST",
            "headers": {},
            "body": {
                "context": {"entity": "entity_123", "blueprint": "microservice"},
                "payload": {
                    "action": {"identifier": "deploy"},
                    "properties": {"environment": "production"},
                },
                "trigger": {"by": {"userId": "user_123"}},
            },
        },
    }


@patch("processors.polling.polling_to_webhook_processor.webhook_invoker")
def test_process_run_success(mock_invoker, sample_run):
    processor = PollingToWebhookProcessor()

    invocation_method = {
        "type": "WEBHOOK",
        "url": "http://localhost:8080/webhook",
        "synchronized": False,
        "method": "POST",
        "headers": {},
    }

    processor.process_run(sample_run, invocation_method)

    mock_invoker.invoke.assert_called_once()

    call_args = mock_invoker.invoke.call_args
    msg_value = call_args[0][0]
    invocation_method_arg = call_args[0][1]

    assert "context" in msg_value
    assert "payload" in msg_value
    assert "trigger" in msg_value
    assert msg_value["context"]["runId"] == "run_123"
    assert msg_value["payload"]["action"]["invocationMethod"]["type"] == "WEBHOOK"

    assert invocation_method_arg["type"] == "WEBHOOK"
    assert invocation_method_arg["url"] == "http://localhost:8080/webhook"


@patch("processors.polling.polling_to_webhook_processor.webhook_invoker")
def test_process_run_without_invocation_method(mock_invoker):
    run = {"_id": "run_789", "id": "run_789", "payload": {"body": {}}}

    invocation_method = {
        "type": "WEBHOOK",
        "url": "http://localhost:8080/webhook",
        "synchronized": False,
        "method": "POST",
        "headers": {},
    }

    processor = PollingToWebhookProcessor()
    processor.process_run(run, invocation_method)

    mock_invoker.invoke.assert_called_once()


@patch("processors.polling.polling_to_webhook_processor.webhook_invoker")
def test_process_run_adds_run_id_to_context(mock_invoker):
    run = {
        "_id": "run_999",
        "id": "run_999",
        "payload": {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "body": {},
        },
    }

    invocation_method = {
        "type": "WEBHOOK",
        "url": "http://localhost:8080/webhook",
        "synchronized": False,
        "method": "POST",
        "headers": {},
    }

    processor = PollingToWebhookProcessor()
    processor.process_run(run, invocation_method)

    call_args = mock_invoker.invoke.call_args
    msg_value = call_args[0][0]

    assert msg_value["context"]["runId"] == "run_999"


@patch("processors.polling.polling_to_webhook_processor.webhook_invoker")
def test_process_run_preserves_existing_run_id(mock_invoker):
    run = {
        "_id": "run_888",
        "id": "run_888",
        "payload": {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "body": {"context": {"runId": "existing_run_id"}},
        },
    }

    invocation_method = {
        "type": "WEBHOOK",
        "url": "http://localhost:8080/webhook",
        "synchronized": False,
        "method": "POST",
        "headers": {},
    }

    processor = PollingToWebhookProcessor()
    processor.process_run(run, invocation_method)

    call_args = mock_invoker.invoke.call_args
    msg_value = call_args[0][0]

    assert msg_value["context"]["runId"] == "run_888"
