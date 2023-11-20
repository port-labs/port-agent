from threading import Timer
from unittest import mock
from unittest.mock import ANY

import pytest
from _pytest.monkeypatch import MonkeyPatch
from consumers.kafka_consumer import logger as consumer_logger
from core.config import Mapping, settings
from pytest_mock import MockFixture
from streamers.kafka.kafka_streamer import KafkaStreamer

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
def test_single_stream_success(mock_requests: None, mock_kafka: None) -> None:
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
def test_single_stream_failed(mock_requests: None, mock_kafka: None) -> None:
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
        ("mock_webhook_run_message", None, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
def test_single_stream_success_control_the_payload(
    monkeypatch: MonkeyPatch,
    mocker: MockFixture,
    mock_requests: None,
    mock_kafka: None,
    mock_control_the_payload_config: list[Mapping],
    webhook_run_payload: dict,
) -> None:
    expected_body = webhook_run_payload
    expected_headers = {
        "MY-HEADER": webhook_run_payload["payload"]["action"]["identifier"]
    }
    expected_query: dict[str, ANY] = {}
    Timer(0.01, terminate_consumer).start()
    request_mock = mocker.patch("requests.request")
    request_mock.return_value.headers = {}
    request_mock.return_value.text = "test"
    request_mock.return_value.status_code = 200
    request_mock.return_value.json.return_value = {}
    request_patch_mock = mocker.patch("requests.patch")
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

        request_patch_mock.assert_called_once_with(
            f"{settings.PORT_API_BASE_URL}/v1/actions/runs/"
            f"{webhook_run_payload['context']['runId']}",
            headers={},
            json={"link": "http://test.com"},
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
def test_invocation_method_synchronized(
    monkeypatch: MonkeyPatch,
    mocker: MockFixture,
    mock_requests: None,
    mock_kafka: None,
    mock_control_the_payload_config: list[Mapping],
    webhook_run_payload: dict,
) -> None:
    expected_body = webhook_run_payload
    expected_headers = {
        "MY-HEADER": webhook_run_payload["payload"]["action"]["identifier"]
    }
    expected_query: dict[str, ANY] = {}
    Timer(0.01, terminate_consumer).start()
    request_mock = mocker.patch("requests.request")
    request_patch_mock = mocker.patch("requests.patch")
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
        request_patch_mock.assert_called_once_with(
            f"{settings.PORT_API_BASE_URL}/v1/actions/runs/"
            f"{webhook_run_payload['context']['runId']}",
            headers={},
            json={"status": "SUCCESS"},
        )

        mock_error.assert_not_called()


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
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
def test_invocation_method_method_override(
    monkeypatch: MonkeyPatch,
    mocker: MockFixture,
    mock_requests: None,
    mock_kafka: None,
    mock_control_the_payload_config: list[Mapping],
    webhook_run_payload: dict,
) -> None:
    expected_body = webhook_run_payload
    expected_headers = {
        "MY-HEADER": webhook_run_payload["payload"]["action"]["identifier"]
    }
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
            headers=expected_headers,
            params=expected_query,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )

        mock_error.assert_not_called()
