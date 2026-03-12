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


@pytest.fixture
def sample_workflow_node_run():
    return {
        "identifier": "wfnr_abc123",
        "status": "IN_PROGRESS",
        "config": {
            "type": "WEBHOOK",
            "url": "https://httpbin.org/post",
            "method": "POST",
            "agent": True,
            "headers": {"Content-Type": "application/json"},
        },
        "pendingExecution": True,
        "claimedUntil": "2026-03-05T12:00:00Z",
        "installationId": "_PORT_EXEC_AGENT",
    }


@pytest.fixture
def webhook_invocation_method():
    return {
        "type": "WEBHOOK",
        "url": "https://httpbin.org/post",
        "synchronized": False,
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
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


# --- Workflow node run processor tests ---


@patch(
    "processors.polling.polling_to_webhook_processor"
    ".report_workflow_node_run_status"
)
@patch("processors.polling.polling_to_webhook_processor.webhook_invoker")
def test_process_workflow_node_run_success(
    mock_invoker, mock_report, sample_workflow_node_run, webhook_invocation_method
):
    processor = PollingToWebhookProcessor()
    processor.process_workflow_node_run(
        sample_workflow_node_run, webhook_invocation_method
    )

    mock_invoker.invoke.assert_called_once()
    call_args = mock_invoker.invoke.call_args
    msg_value = call_args[0][0]

    assert msg_value["context"]["nodeRunIdentifier"] == "wfnr_abc123"
    assert msg_value["context"]["nodeConfig"]["type"] == "WEBHOOK"
    assert msg_value["payload"]["action"]["invocationMethod"] == (
        webhook_invocation_method
    )

    mock_report.assert_called_once_with(
        "wfnr_abc123",
        {"status": "COMPLETED", "result": "SUCCESS"},
    )


@patch(
    "processors.polling.polling_to_webhook_processor"
    ".report_workflow_node_run_status"
)
@patch("processors.polling.polling_to_webhook_processor.webhook_invoker")
def test_process_workflow_node_run_webhook_failure_reports_failure(
    mock_invoker, mock_report, sample_workflow_node_run, webhook_invocation_method
):
    mock_invoker.invoke.side_effect = Exception("Connection refused")

    processor = PollingToWebhookProcessor()
    with pytest.raises(Exception, match="Connection refused"):
        processor.process_workflow_node_run(
            sample_workflow_node_run, webhook_invocation_method
        )

    mock_report.assert_called_once_with(
        "wfnr_abc123",
        {"status": "COMPLETED", "result": "FAILURE"},
    )


@patch(
    "processors.polling.polling_to_webhook_processor"
    ".report_workflow_node_run_status"
)
@patch("processors.polling.polling_to_webhook_processor.webhook_invoker")
def test_process_workflow_node_run_missing_identifier(
    mock_invoker, mock_report
):
    processor = PollingToWebhookProcessor()
    processor.process_workflow_node_run(
        {"status": "IN_PROGRESS"},
        {"type": "WEBHOOK", "url": "https://httpbin.org/post"},
    )

    mock_invoker.invoke.assert_not_called()
    mock_report.assert_not_called()


@patch(
    "processors.polling.polling_to_webhook_processor"
    ".report_workflow_node_run_status"
)
@patch("processors.polling.polling_to_webhook_processor.webhook_invoker")
def test_process_workflow_node_run_empty_config(
    mock_invoker, mock_report
):
    node_run = {
        "identifier": "wfnr_empty_config",
        "status": "IN_PROGRESS",
        "config": None,
    }
    invocation_method = {
        "type": "WEBHOOK",
        "url": "https://httpbin.org/post",
        "synchronized": False,
        "method": "POST",
        "headers": {},
    }

    processor = PollingToWebhookProcessor()
    processor.process_workflow_node_run(node_run, invocation_method)

    mock_invoker.invoke.assert_called_once()
    call_args = mock_invoker.invoke.call_args
    msg_value = call_args[0][0]
    assert msg_value["context"]["nodeConfig"] == {}

    mock_report.assert_called_once_with(
        "wfnr_empty_config",
        {"status": "COMPLETED", "result": "SUCCESS"},
    )
