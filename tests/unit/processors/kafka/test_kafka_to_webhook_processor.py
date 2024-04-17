import json
import time
from copy import deepcopy
from threading import Timer
from unittest import mock
from unittest.mock import ANY, call

import pytest
from _pytest.monkeypatch import MonkeyPatch
from consumers.kafka_consumer import logger as consumer_logger
from core.config import Mapping, settings
from pytest_mock import MockFixture
from streamers.kafka.kafka_streamer import KafkaStreamer

from app.utils import sign_sha_256
from tests.unit.processors.kafka.conftest import Consumer, terminate_consumer


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_webhook_change_log_message", None, settings.KAFKA_CHANGE_LOG_TOPIC),
        ("mock_webhook_run_message", None, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_single_stream_success(
    mock_requests: None, mock_kafka: dict, mock_timestamp: None
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
        ("mock_webhook_change_log_message", None, settings.KAFKA_CHANGE_LOG_TOPIC),
        ("mock_webhook_run_message", None, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_single_stream_failed(
    mock_requests: None, mock_kafka: dict, mock_timestamp: None
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
    "mock_requests",
    [{"status_code": 200}],
    indirect=True,
)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_webhook_change_log_message", None, settings.KAFKA_CHANGE_LOG_TOPIC),
        ("mock_webhook_run_message", None, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_single_stream_success_control_the_payload(
    monkeypatch: MonkeyPatch,
    mocker: MockFixture,
    mock_requests: None,
    mock_kafka: dict,
    mock_timestamp: None,
    mock_control_the_payload_config: list[Mapping],
) -> None:
    expected_body = deepcopy(mock_kafka)
    expected_headers = {"MY-HEADER": mock_kafka["resourceType"]}
    expected_query: dict[str, ANY] = {}
    if "changelogDestination" not in mock_kafka:
        del expected_body["headers"]["X-Port-Signature"]
        del expected_body["headers"]["X-Port-Timestamp"]

    expected_headers["X-Port-Timestamp"] = ANY
    expected_headers["X-Port-Signature"] = ANY
    Timer(0.01, terminate_consumer).start()
    request_mock = mocker.patch("requests.request")
    request_mock.return_value.headers = {}
    request_mock.return_value.text = "test"
    request_mock.return_value.status_code = 200
    request_mock.return_value.json.return_value = {}
    mocker.patch("pathlib.Path.is_file", side_effect=(True,))

    with mock.patch.object(consumer_logger, "error") as mock_error:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()
        request_mock.assert_called_once_with(
            "POST",
            ANY,
            json=expected_body,
            headers=expected_headers,
            params=expected_query,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )

        mock_error.assert_not_called()


@pytest.mark.parametrize(
    "mock_requests",
    [{"status_code": 200}],
    indirect=True,
)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_webhook_run_message",
            {
                "type": "WEBHOOK",
                "agent": True,
                "url": "http://localhost:80/api/test",
                "synchronized": True,
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_invocation_method_synchronized(
    monkeypatch: MonkeyPatch,
    mocker: MockFixture,
    mock_requests: None,
    mock_kafka: dict,
    mock_timestamp: None,
    mock_control_the_payload_config: list[Mapping],
    webhook_run_payload: dict,
) -> None:
    expected_body = deepcopy(webhook_run_payload)
    expected_headers = {"MY-HEADER": mock_kafka["resourceType"]}

    expected_query: dict[str, ANY] = {}
    Timer(0.01, terminate_consumer).start()
    request_mock = mocker.patch("requests.request")
    request_patch_mock = mocker.patch("requests.patch")
    mocker.patch("pathlib.Path.is_file", side_effect=(True,))

    del expected_body["headers"]["X-Port-Signature"]
    del expected_body["headers"]["X-Port-Timestamp"]

    expected_headers["X-Port-Timestamp"] = ANY
    expected_headers["X-Port-Signature"] = ANY
    with mock.patch.object(consumer_logger, "error") as mock_error:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()
        request_mock.assert_called_once_with(
            "POST",
            ANY,
            json=expected_body,
            headers=expected_headers,
            params=expected_query,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )

        request_patch_mock.assert_has_calls(
            calls=[
                call(
                    f"{settings.PORT_API_BASE_URL}/v1/actions/runs/"
                    f"{webhook_run_payload['context']['runId']}/response",
                    json=ANY,
                    headers={},
                ),
                call().ok.__bool__(),
                call(
                    f"{settings.PORT_API_BASE_URL}/v1/actions/runs/"
                    f"{webhook_run_payload['context']['runId']}",
                    json={"status": "SUCCESS"},
                    headers={},
                ),
                call().ok.__bool__(),
            ]
        )

        mock_error.assert_not_called()


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_webhook_change_log_message",
            {
                "type": "WEBHOOK",
                "agent": True,
                "url": "http://localhost:80/api/test",
                "method": "GET",
            },
            settings.KAFKA_CHANGE_LOG_TOPIC,
        ),
        (
            "mock_webhook_run_message",
            {
                "type": "WEBHOOK",
                "agent": True,
                "url": "http://localhost:80/api/test",
                "method": "GET",
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_invocation_method_method_override(
    monkeypatch: MonkeyPatch,
    mocker: MockFixture,
    mock_requests: None,
    mock_kafka: dict,
    mock_timestamp: None,
    mock_control_the_payload_config: list[Mapping],
) -> None:
    expected_body = mock_kafka
    expected_headers = {
        "MY-HEADER": mock_kafka["resourceType"],
    }

    if "changelogDestination" not in mock_kafka:
        del expected_body["headers"]["X-Port-Signature"]
        del expected_body["headers"]["X-Port-Timestamp"]

    expected_headers["X-Port-Timestamp"] = str(time.time())
    expected_headers["X-Port-Signature"] = sign_sha_256(
        json.dumps(expected_body, separators=(",", ":")), "test", time.time()
    )

    expected_query: dict[str, ANY] = {}
    Timer(0.01, terminate_consumer).start()
    request_mock = mocker.patch("requests.request")
    mocker.patch("pathlib.Path.is_file", side_effect=(True,))
    with mock.patch.object(consumer_logger, "error") as mock_error:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()
        request_mock.assert_called_once_with(
            "GET",
            ANY,
            json=expected_body,
            # we are removing the signature headers from the
            # body is it shouldn't concern the invoked webhook
            headers=expected_headers,
            params=expected_query,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )

        mock_error.assert_not_called()
