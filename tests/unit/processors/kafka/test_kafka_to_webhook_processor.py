from threading import Timer
from unittest import mock
from unittest.mock import ANY, call

import pytest
from consumers.kafka_consumer import logger as consumer_logger
from core.config import settings
from processors.kafka.kafka_to_webhook_processor import (
    logger as webhook_processor_logger,
)
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
    "mock_kafka",
    [
        (
            "mock_webhook_run_message",
            {
                "type": "WEBHOOK",
                "agent": True,
                "url": "https://example.com",
                "method": "GET",
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
def test_single_stream_skipped_due_to_not_supported_http_method(
    mock_kafka: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
        webhook_processor_logger, "info"
    ) as mock_info:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_error.assert_not_called()
        mock_info.assert_has_calls(
            [
                call(ANY, ANY),
                call(
                    "Skip process message"
                    " from topic %s, partition %d, offset %d: %s",
                    ANY,
                    0,
                    0,
                    "HTTP method not supported",
                ),
            ]
        )


@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_webhook_run_message",
            {
                "type": "WEBHOOK",
                "agent": True,
                "method": "GET",
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
def test_single_stream_skipped_due_to_not_url_not_provided(
    mock_kafka: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
        webhook_processor_logger, "info"
    ) as mock_info:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_error.assert_not_called()
        mock_info.assert_has_calls(
            [
                call(ANY, ANY),
                call(
                    "Skip process message"
                    " from topic %s, partition %d, offset %d: %s",
                    ANY,
                    0,
                    0,
                    "Webhook URL wasn't provided",
                ),
            ]
        )


@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_synchronized_webhook_run_message",
            {
                "invocationMethod": {
                    "type": "WEBHOOK",
                    "agent": True,
                    "synchronized": True,
                    "method": "POST",
                    "url": "https://example.com",
                },
                "runId": ""
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
def test_single_stream_skipped_due_to_no_run_id_in_synchronized(
    mock_kafka: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
        webhook_processor_logger, "info"
    ) as mock_info:
        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_error.assert_not_called()
        mock_info.assert_has_calls(
            [
                call(ANY, ANY),
                call(
                    "Skip process message"
                    " from topic %s, partition %d, offset %d: %s",
                    ANY,
                    0,
                    0,
                    "Run id was not provided for synchronized webhook invocation",
                ),
            ]
        )
