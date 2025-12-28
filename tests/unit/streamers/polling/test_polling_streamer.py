from threading import Timer
from unittest.mock import MagicMock, patch

from streamers.polling.polling_streamer import PollingStreamer


def test_polling_streamer_initialization():
    streamer = PollingStreamer()

    assert streamer.https_consumer is not None
    assert streamer.processor is not None


@patch("streamers.polling.polling_streamer.HttpsConsumer")
@patch("streamers.polling.polling_streamer.HttpsToWebhookProcessor")
def test_polling_streamer_stream(mock_processor_class, mock_consumer_class):
    mock_consumer = MagicMock()
    mock_consumer_class.return_value = mock_consumer
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    streamer = PollingStreamer()

    def stop_consumer():
        mock_consumer.running = False

    Timer(0.1, stop_consumer).start()

    streamer.stream()

    mock_consumer.start.assert_called_once()


@patch("streamers.polling.polling_streamer.HttpsToWebhookProcessor")
def test_polling_streamer_process_run(mock_processor_class):
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    sample_run = {
        "_id": "run_123",
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

    with patch("streamers.polling.polling_streamer.HttpsConsumer"):
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


@patch("streamers.polling.polling_streamer.HttpsToWebhookProcessor")
def test_polling_streamer_process_run_skips_non_agent(mock_processor_class):
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

    with patch("streamers.polling.polling_streamer.HttpsConsumer"):
        streamer = PollingStreamer()

        streamer.process_run(sample_run)

        mock_processor.process_run.assert_not_called()
