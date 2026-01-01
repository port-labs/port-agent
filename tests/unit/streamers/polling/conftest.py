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
