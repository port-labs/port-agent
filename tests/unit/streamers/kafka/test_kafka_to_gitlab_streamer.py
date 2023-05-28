#
# from threading import Timer
# from unittest import mock
# from unittest.mock import ANY, call
#
# import pytest
# from consumers.kafka_consumer import logger as consumer_logger
# from core.config import settings
# from streamers.kafka.kafka_to_gitlab_streamer import KafkaToGitLabStreamer
#
# from streamers.kafka.kafka_to_webhook_streamer import logger as streamer_logger
#
# from tests.unit.streamers.kafka.conftest import Consumer, terminate_consumer
#
#
# @pytest.mark.parametrize("mock_requests", [{"status_code": 200}], indirect=True)
# @pytest.mark.parametrize(
#     "mock_kafka",
#     [
#         ("mock_gitlab_run_message", None, settings.KAFKA_RUNS_TOPIC),
#     ],
#     indirect=True,
# )
# def test_single_stream_success(mock_requests: None, mock_kafka: None) -> None:
#     Timer(0.01, terminate_consumer).start()
#
#     with mock.patch.object(consumer_logger, "error") as mock_error:
#         streamer = KafkaToGitLabStreamer(Consumer())
#         streamer.stream()
#
#         mock_error.assert_not_called()
#
#
# @pytest.mark.parametrize("mock_requests", [{"status_code": 500}], indirect=True)
# @pytest.mark.parametrize(
#     "mock_kafka",
#     [
#         ("mock_gitlab_run_message", None, settings.KAFKA_RUNS_TOPIC),
#     ],
#     indirect=True,
# )
# def test_single_stream_failed(mock_requests: None, mock_kafka: None, mock_gitlab_token) -> None:
#     Timer(0.01, terminate_consumer).start()
#
#     with mock.patch.object(consumer_logger, "error") as mock_error:
#         streamer = KafkaToGitLabStreamer(Consumer())
#         streamer.stream()
#
#         mock_error.assert_called_once_with(
#             "Failed process message from topic %s, partition %d, offset %d: %s",
#             ANY,
#             0,
#             0,
#             "Invoker failed with status code: 500",
#         )
#
#
# @pytest.mark.parametrize(
#     "mock_kafka",
#     [
#         ("mock_gitlab_run_message", {"agent": False}, settings.KAFKA_RUNS_TOPIC),
#     ],
#     indirect=True,
# )
# def test_single_stream_skipped_due_to_agentless(mock_kafka: None, mock_gitlab_token) -> None:
#     Timer(0.01, terminate_consumer).start()
#
#     with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
#         streamer_logger, "info"
#     ) as mock_info:
#         streamer = KafkaToGitLabStreamer(Consumer())
#         streamer.stream()
#
#         mock_error.assert_not_called()
#         mock_info.assert_has_calls(
#             [
#                 call(ANY, ANY),
#                 call(
#                     "Skip process message"
#                     " from topic %s, partition %d, offset %d: %s",
#                     ANY,
#                     0,
#                     0,
#                     "not for agent"
#                 ),
#             ]
#         )
# #
# #
# # @pytest.mark.parametrize(
# #     "mock_kafka",
# #     [
# #         (
# #             "mock_run_message",
# #             {"agent": True, "type": "UNSUPPORTED"},
# #             settings.KAFKA_RUNS_TOPIC,
# #         ),
# #     ],
# #     indirect=True,
# # )
# # def test_single_stream_skipped_due_to_not_gitlab_invoker(mock_kafka: None) -> None:
# #     Timer(0.01, terminate_consumer).start()
# #
# #     with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
# #         streamer_logger, "info"
# #     ) as mock_info:
# #         streamer = KafkaToGitLabStreamer(Consumer())
# #         streamer.stream()
# #
# #         mock_error.assert_not_called()
# #         mock_info.assert_has_calls(
# #             [
# #                 call(ANY, ANY),
# #                 call(
# #                     "Skip process message"
# #                     " from topic %s, partition %d, offset %d: %s",
# #                     ANY,
# #                     0,
# #                     0,
# #                     "Invocation type not found / not supported"
# #                 ),
# #             ]
# #         )
# #
# #
# # @pytest.mark.parametrize(
# #     "mock_kafka",
# #     [
# #         (
# #             "mock_run_message",
# #             {"agent": True, "type": "GITLAB", "ref": "main", "groupName": None},
# #             settings.KAFKA_RUNS_TOPIC,
# #         ),
# #     ],
# #     indirect=True,
# # )
# # def test_single_stream_skipped_due_to_no_group_name(mock_kafka: None) -> None:
# #     Timer(0.01, terminate_consumer).start()
# #
# #     with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
# #         streamer_logger, "info"
# #     ) as mock_info:
# #         streamer = KafkaToGitLabStreamer(Consumer())
# #         streamer.stream()
# #
# #         mock_error.assert_not_called()
# #         mock_info.assert_has_calls(
# #             [
# #                 call(ANY, ANY),
# #                 call(
# #                     "Skip process message"
# #                     " from topic %s, partition %d, offset %d: GitLab project path is missing",
# #                     ANY,
# #                     0,
# #                     0
# #                 ),
# #             ]
# #         )
# #
# # @pytest.mark.parametrize(
# #     "mock_kafka",
# #     [
# #         (
# #             "mock_run_message",
# #             {"agent": True, "type": "GITLAB", "ref": "main", "groupName": "group", "projectName": None},
# #             settings.KAFKA_RUNS_TOPIC,
# #         ),
# #     ],
# #     indirect=True,
# # )
# # def test_single_stream_skipped_due_to_no_project_name(mock_kafka: None) -> None:
# #     Timer(0.01, terminate_consumer).start()
# #
# #     with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
# #         streamer_logger, "info"
# #     ) as mock_info:
# #         streamer = KafkaToGitLabStreamer(Consumer())
# #         streamer.stream()
# #
# #         mock_error.assert_not_called()
# #         mock_info.assert_has_calls(
# #             [
# #                 call(ANY, ANY),
# #                 call(
# #                     "Skip process message"
# #                     " from topic %s, partition %d, offset %d: GitLab project path is missing",
# #                     ANY,
# #                     0,
# #                     0
# #                 ),
# #             ]
# #         )
# #
# #
# # @pytest.mark.parametrize(
# #     "mock_kafka",
# #     [
# #         (
# #             "mock_run_message",
# #             {"agent": True, "type": "GITLAB", "ref": None},
# #             settings.KAFKA_RUNS_TOPIC,
# #         ),
# #     ],
# #     indirect=True,
# # )
# # def test_single_stream_skipped_due_to_no_ref(mock_kafka: None) -> None:
# #     Timer(0.01, terminate_consumer).start()
# #
# #     with mock.patch.object(consumer_logger, "error") as mock_error, mock.patch.object(
# #         streamer_logger, "info"
# #     ) as mock_info:
# #         streamer = KafkaToGitLabStreamer(Consumer())
# #         streamer.stream()
# #
# #         mock_error.assert_not_called()
# #         mock_info.assert_has_calls(
# #             [
# #                 call(ANY, ANY),
# #                 call(
# #                     "Skip process message"
# #                     " from topic %s, partition %d, offset %d: Ref wasn't passed to agent",
# #                     ANY,
# #                     0,
# #                     0
# #                 ),
# #             ]
# #         )
