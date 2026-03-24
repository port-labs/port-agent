import json
from copy import deepcopy
from threading import Timer
from typing import Callable
from unittest import mock
from unittest.mock import ANY, call

import pytest
from consumers.kafka_consumer import logger as consumer_logger
from core.config import settings
from pytest_mock import MockFixture
from streamers.kafka.kafka_streamer import KafkaStreamer
from streamers.kafka.kafka_streamer import logger as streamer_logger

from tests.unit.streamers.kafka.conftest import Consumer, terminate_consumer


def _patch_requests_patch_ok(mocker: MockFixture) -> None:
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_resp.text = ""
    mock_resp.json.return_value = {}
    mock_resp.raise_for_status = mock.Mock()
    mocker.patch("requests.patch", return_value=mock_resp)


@pytest.fixture(scope="module")
def mock_wf_node_run_message() -> Callable[[dict | None], bytes]:
    node_run_message: dict = {
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
    }

    def get_node_run_message(config_override: dict | None) -> bytes:
        msg = deepcopy(node_run_message)
        if config_override is not None:
            msg["config"] = config_override
        return json.dumps(msg).encode()

    return get_node_run_message


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_webhook_run_message", None, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_single_stream_success(
    mock_requests: None, mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_error.assert_not_called()


@pytest.mark.parametrize("mock_requests", [{"status_code": 500}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_webhook_run_message", None, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_single_stream_failed(
    mock_requests: None, mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_error.assert_called_once_with(
            "Failed process message from topic %s, partition %d, offset %d: %s",
            ANY,
            0,
            0,
            "Invoker failed with status code: 500",
        )


@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_webhook_run_message", {"agent": False}, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_single_stream_skipped_due_to_agentless(
    mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()
    with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
        streamer_logger, "info"
    ) as mock_info:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_error.assert_not_called()

        mock_info.assert_has_calls(
            [
                call(
                    (
                        "Received message - topic: %s, partition: %d, "
                        "offset: %d, raw_value: %s"
                    ),
                    ANY,
                    0,
                    0,
                    ANY,
                ),
                call(
                    "Skip process message"
                    " from topic %s, partition %d, offset %d: not for agent",
                    ANY,
                    0,
                    0,
                ),
            ]
        )


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_wf_node_run_message", None, settings.KAFKA_WF_NODE_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_wf_node_run_stream_success(
    mock_requests: None,
    mock_kafka: None,
    mock_timestamp: None,
    mocker: MockFixture,
) -> None:
    _patch_requests_patch_ok(mocker)
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_error.assert_not_called()


@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_wf_node_run_message",
            {"type": "WEBHOOK", "url": "https://httpbin.org/post", "agent": False},
            settings.KAFKA_WF_NODE_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_wf_node_run_stream_skips_non_agent(
    mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
        streamer_logger, "info"
    ) as mock_info:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_error.assert_not_called()
        mock_info.assert_any_call(
            "Skip process message"
            " from topic %s, partition %d, offset %d: not for agent",
            ANY,
            0,
            0,
        )
