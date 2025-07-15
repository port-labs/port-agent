from threading import Timer
from unittest import mock
from unittest.mock import ANY, call

import pytest
from consumers.kafka_consumer import logger as consumer_logger
from core.config import settings
from streamers.kafka.kafka_streamer import KafkaStreamer
from streamers.kafka.kafka_streamer import logger as streamer_logger

from tests.unit.streamers.kafka.conftest import Consumer, terminate_consumer


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
                call(ANY, ANY),
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
        ("mock_webhook_run_message", {"environment": "production"}, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_stream_with_matching_environment(
    mock_requests: None, mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()
    
    # Set agent environments to include production
    with mock.patch.object(settings, "AGENT_ENVIRONMENTS", ["production", "staging"]):
        with mock.patch.object(consumer_logger, "error") as mock_error:
            streamer = KafkaStreamer(Consumer())
            streamer.stream()
            
            mock_error.assert_not_called()


@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_webhook_run_message", {"environment": "development"}, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_stream_skipped_due_to_non_matching_environment(
    mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()
    
    # Set agent environments to production only
    with mock.patch.object(settings, "AGENT_ENVIRONMENTS", ["production"]):
        with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
            streamer_logger, "info"
        ) as mock_info:
            streamer = KafkaStreamer(Consumer())
            streamer.stream()
            
            mock_error.assert_not_called()
            
            mock_info.assert_has_calls(
                [
                    call(ANY, ANY),
                    call(
                        "Skip process message"
                        " from topic %s, partition %d, offset %d:"
                        " message environments %s not in allowed environments %s",
                        ANY,
                        0,
                        0,
                        ["development"],
                        ["production"],
                    ),
                ]
            )


@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_webhook_run_message", {}, settings.KAFKA_RUNS_TOPIC),  # No environment field
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_stream_skipped_due_to_missing_environment(
    mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()
    
    # Set agent environments filter
    with mock.patch.object(settings, "AGENT_ENVIRONMENTS", ["production"]):
        with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
            streamer_logger, "info"
        ) as mock_info:
            streamer = KafkaStreamer(Consumer())
            streamer.stream()
            
            mock_error.assert_not_called()
            
            mock_info.assert_has_calls(
                [
                    call(ANY, ANY),
                    call(
                        "Skip process message"
                        " from topic %s, partition %d, offset %d:"
                        " no environment specified and agent has environment filter",
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
        ("mock_webhook_run_message", {"environment": ["production", "staging"]}, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_stream_with_multiple_environments(
    mock_requests: None, mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()
    
    # Set agent environments to match one of the message environments
    with mock.patch.object(settings, "AGENT_ENVIRONMENTS", ["staging"]):
        with mock.patch.object(consumer_logger, "error") as mock_error:
            streamer = KafkaStreamer(Consumer())
            streamer.stream()
            
            mock_error.assert_not_called()


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_webhook_run_message", {"environment": "production"}, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
@pytest.mark.parametrize("mock_timestamp", [{}], indirect=True)
def test_stream_without_environment_filter(
    mock_requests: None, mock_kafka: None, mock_timestamp: None
) -> None:
    Timer(0.01, terminate_consumer).start()
    
    # No agent environments set (empty list)
    with mock.patch.object(settings, "AGENT_ENVIRONMENTS", []):
        with mock.patch.object(consumer_logger, "error") as mock_error:
            streamer = KafkaStreamer(Consumer())
            streamer.stream()
            
            # Should process message normally when no environment filter is set
            mock_error.assert_not_called()
