from threading import Timer
from unittest import mock
from unittest.mock import ANY, call

import pytest
from consumers.kafka_consumer import logger as consumer_logger
from core.config import settings
from processors.kafka.kafka_to_gitlab_processor import logger as gitlab_processor_logger
from streamers.kafka.kafka_streamer import KafkaStreamer

from tests.unit.processors.kafka.conftest import Consumer, terminate_consumer


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        ("mock_gitlab_run_message", None, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
def test_single_stream_success(
    mock_requests: None, mock_kafka: None, mock_gitlab_token: None
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
        ("mock_gitlab_run_message", None, settings.KAFKA_RUNS_TOPIC),
    ],
    indirect=True,
)
def test_single_stream_failed(
    mock_requests: None, mock_kafka: None, mock_gitlab_token: None
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
        (
            "mock_gitlab_run_message",
            {
                "type": "GITLAB",
                "agent": True,
                "projectName": "project",
                "groupName": "",
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
def test_single_stream_skipped_due_to_missing_group_name(
    mock_kafka: None, mock_gitlab_token: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
        gitlab_processor_logger, "info"
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
                    "GitLab project path is missing",
                ),
            ]
        )


@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_gitlab_run_message",
            {"type": "GITLAB", "agent": True, "groupName": "group", "projectName": ""},
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
def test_single_stream_skipped_due_to_missing_project_name(
    mock_kafka: None, mock_gitlab_token: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
        gitlab_processor_logger, "info"
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
                    "GitLab project path is missing",
                ),
            ]
        )


@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_gitlab_run_message",
            {
                "type": "GITLAB",
                "agent": True,
                "groupName": "notgroup",
                "projectName": "notproject",
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
def test_single_stream_skipped_due_to_wrong_token(
    mock_kafka: None, mock_gitlab_token: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
        gitlab_processor_logger, "info"
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
                    " no token env variable found for project %s/%s",
                    ANY,
                    0,
                    0,
                    ANY,
                    ANY,
                ),
            ]
        )


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_gitlab_run_message",
            {
                "type": "GITLAB",
                "agent": True,
                "groupName": "group",
                "projectName": "subgroup/sub2/project",
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
def test_single_stream_with_subgroup_in_project_name(
    mock_requests: None, mock_kafka: None, mock_gitlab_token_subgroup: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(gitlab_processor_logger, "info") as mock_info:

        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        call_of_missing_token = call(
            "Skip process message"
            " from topic %s, partition %d, offset %d:"
            " no token env variable found for project %s/%s",
            ANY,
            0,
            0,
            ANY,
            ANY,
        )

        # Check if the expected calls were not made
        assert call_of_missing_token not in mock_info.call_args_list


@pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
@pytest.mark.parametrize(
    "mock_kafka",
    [
        (
            "mock_gitlab_run_message",
            {
                "type": "GITLAB",
                "agent": True,
                "groupName": "group",
                "projectName": "wrong/sub2/project",
            },
            settings.KAFKA_RUNS_TOPIC,
        ),
    ],
    indirect=True,
)
def test_single_stream_with_subgroup_in_project_name_failure(
    mock_requests: None, mock_kafka: None, mock_gitlab_token_subgroup: None
) -> None:
    Timer(0.01, terminate_consumer).start()

    with mock.patch.object(gitlab_processor_logger, "info") as mock_info:

        streamer = KafkaStreamer(Consumer())
        streamer.stream()

        mock_info.assert_has_calls(
            [
                call(ANY, ANY),
                call(
                    "Skip process message"
                    " from topic %s, partition %d, offset %d:"
                    " no token env variable found for project %s/%s",
                    ANY,
                    0,
                    0,
                    ANY,
                    ANY,
                ),
            ]
        )
