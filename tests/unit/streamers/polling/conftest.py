from unittest.mock import patch

import pytest


@pytest.fixture
def mock_claim_pending_runs():
    with patch("consumers.http_polling_consumer.claim_pending_runs") as mock:
        yield mock


@pytest.fixture
def mock_ack_runs():
    with patch("consumers.http_polling_consumer.ack_runs") as mock:
        yield mock


@pytest.fixture
def mock_time_sleep():
    with patch("consumers.http_polling_consumer.time.sleep") as mock:
        yield mock


@pytest.fixture
def mock_report_run_status():
    with patch("consumers.http_polling_consumer.report_run_status") as mock:
        yield mock


@pytest.fixture
def mock_claim_pending_workflow_node_runs():
    with patch(
        "consumers.http_polling_consumer.claim_pending_workflow_node_runs"
    ) as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_ack_workflow_node_run():
    with patch(
        "consumers.http_polling_consumer.ack_workflow_node_run"
    ) as mock:
        yield mock


@pytest.fixture
def mock_report_workflow_node_run_status():
    with patch(
        "consumers.http_polling_consumer.report_workflow_node_run_status"
    ) as mock:
        yield mock


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
                "context": {
                    "runId": "run_123",
                    "entity": "entity_123",
                    "blueprint": "microservice",
                },
                "payload": {"action": {"identifier": "deploy"}},
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
            "url": "http://localhost:8080/webhook",
            "method": "POST",
            "agent": True,
        },
        "pendingExecution": True,
        "claimedUntil": "2026-03-05T12:00:00Z",
        "installationId": "_PORT_EXEC_AGENT",
    }
