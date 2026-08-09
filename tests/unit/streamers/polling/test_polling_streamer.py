import logging
from threading import Timer
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from streamers.polling.polling_streamer import PollingStreamer


def build_run(payload: dict) -> dict:
    return {"_id": "run_nested", "id": "run_nested", "payload": payload}


def event_with_invocation_method(invocation_method: dict) -> dict:
    return {
        "context": {"runId": "run_nested"},
        "payload": {"action": {"invocationMethod": invocation_method}},
        "trigger": {"by": {"userId": "user_123"}},
    }


def test_polling_streamer_initialization() -> None:
    streamer = PollingStreamer()

    assert streamer.http_polling_consumer is not None
    assert streamer.processor is not None


@patch("streamers.polling.polling_streamer.HttpPollingConsumer")
@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_stream(
    mock_processor_class: Any, mock_consumer_class: Any
) -> None:
    mock_consumer = MagicMock()
    mock_consumer_class.return_value = mock_consumer
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    streamer = PollingStreamer()

    def stop_consumer() -> None:
        mock_consumer.running = False

    Timer(0.1, stop_consumer).start()

    streamer.stream()

    mock_consumer.start.assert_called_once()


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_run(mock_processor_class: Any) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    sample_run = {
        "_id": "run_123",
        "id": "run_123",
        "payload": {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "synchronized": False,
            "method": "POST",
            "headers": {},
            "body": {},
        },
    }

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        streamer = PollingStreamer()

        streamer.process_run(sample_run)

        mock_processor.process_run.assert_called_once()
        call_args = mock_processor.process_run.call_args
        assert (
            len(call_args[0]) == 2
        ), f"Expected 2 args, got {len(call_args[0])}: {call_args}"
        assert call_args[0][0] == sample_run
        invocation_method = call_args[0][1]
        assert invocation_method["type"] == "WEBHOOK"
        assert invocation_method["url"] == "http://localhost:8080/webhook"
        assert "agent" not in invocation_method


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_run_skips_non_agent(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    sample_run = {
        "_id": "run_456",
        "payload": {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": False,
            "body": {},
        },
    }

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        streamer = PollingStreamer()

        streamer.process_run(sample_run)

        mock_processor.process_run.assert_not_called()


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_run_keeps_fields_only_in_the_event(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    run = build_run(
        {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "synchronized": False,
            "method": "POST",
            "headers": {},
            "body": event_with_invocation_method(
                {
                    "type": "WEBHOOK",
                    "url": "http://stale.example.com",
                    "agent": True,
                    "body": {"foo": "bar"},
                    "omitPayload": True,
                }
            ),
        }
    )

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        PollingStreamer().process_run(run)

    invocation_method = mock_processor.process_run.call_args[0][1]
    assert invocation_method["body"] == {"foo": "bar"}
    assert invocation_method["omitPayload"] is True
    assert invocation_method["url"] == "http://localhost:8080/webhook"
    assert "agent" not in invocation_method


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_run_defaults_do_not_override_the_event(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    run = build_run(
        {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "body": event_with_invocation_method(
                {
                    "synchronized": True,
                    "method": "PUT",
                    "headers": {"X-Custom": "1"},
                }
            ),
        }
    )

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        PollingStreamer().process_run(run)

    invocation_method = mock_processor.process_run.call_args[0][1]
    assert invocation_method["synchronized"] is True
    assert invocation_method["method"] == "PUT"
    assert invocation_method["headers"] == {"X-Custom": "1"}


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_run_honors_agent_from_the_event(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    run = build_run(
        {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "body": event_with_invocation_method({"agent": True}),
        }
    )

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        PollingStreamer().process_run(run)

    mock_processor.process_run.assert_called_once()
    assert "agent" not in mock_processor.process_run.call_args[0][1]


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_run_warns_when_body_is_not_a_port_event(
    mock_processor_class: Any, caplog: pytest.LogCaptureFixture
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    run = build_run(
        {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "body": {"custom": "body"},
        }
    )

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        with caplog.at_level(
            logging.WARNING, logger="streamers.polling.polling_streamer"
        ):
            PollingStreamer().process_run(run)

    assert "does not look like a Port event" in caplog.text
    assert "['custom']" in caplog.text


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_run_raises_when_url_is_missing(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    run = build_run(
        {
            "type": "WEBHOOK",
            "agent": True,
            "body": event_with_invocation_method({}),
        }
    )

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        with pytest.raises(ValueError, match="no invocation method type or url"):
            PollingStreamer().process_run(run)

    mock_processor.process_run.assert_not_called()


# --- Workflow node run streamer tests ---


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_wf_node_run(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    node_run = {
        "identifier": "wfnr_abc123",
        "status": "IN_PROGRESS",
        "config": {
            "type": "WEBHOOK",
            "url": "https://httpbin.org/post",
            "agent": True,
            "synchronized": True,
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
        },
    }

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        streamer = PollingStreamer()
        streamer.process_wf_node_run(node_run)

        mock_processor.process_wf_node_run.assert_called_once()
        call_args = mock_processor.process_wf_node_run.call_args
        assert call_args[0][0] == node_run
        invocation_method = call_args[0][1]
        assert invocation_method["type"] == "WEBHOOK"
        assert invocation_method["url"] == "https://httpbin.org/post"
        assert invocation_method["synchronized"] is True
        assert "agent" not in invocation_method


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_wf_node_run_passes_the_whole_config(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    node_run = {
        "identifier": "wfnr_abc123",
        "config": {
            "type": "WEBHOOK",
            "url": "https://httpbin.org/post",
            "agent": True,
            "body": {"service": "payments"},
            "onTimeout": "continue",
        },
    }

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        PollingStreamer().process_wf_node_run(node_run)

    invocation_method = mock_processor.process_wf_node_run.call_args[0][1]
    assert invocation_method["body"] == {"service": "payments"}
    assert invocation_method["onTimeout"] == "continue"
    assert invocation_method["method"] == "POST"
    assert invocation_method["synchronized"] is False
    assert "agent" not in invocation_method


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_wf_node_run_skips_non_agent(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    node_run = {
        "identifier": "wfnr_skip",
        "config": {
            "type": "WEBHOOK",
            "url": "https://httpbin.org/post",
            "agent": False,
            "method": "POST",
        },
    }

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        streamer = PollingStreamer()
        streamer.process_wf_node_run(node_run)

        mock_processor.process_wf_node_run.assert_not_called()


@patch("streamers.polling.polling_streamer.PollingToWebhookProcessor")
def test_polling_streamer_process_wf_node_run_missing_identifier(
    mock_processor_class: Any,
) -> None:
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    node_run = {"config": {"type": "WEBHOOK", "url": "https://httpbin.org/post"}}

    with patch("streamers.polling.polling_streamer.HttpPollingConsumer"):
        streamer = PollingStreamer()
        streamer.process_wf_node_run(node_run)

        mock_processor.process_wf_node_run.assert_not_called()
