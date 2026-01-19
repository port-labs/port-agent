from threading import Timer

from consumers.http_polling_consumer import HttpPollingConsumer


def terminate_consumer(consumer):
    consumer.exit_gracefully()


def test_http_polling_consumer_successful_poll(
    mock_claim_pending_runs, mock_ack_runs, mock_time_sleep, sample_run
):
    mock_claim_pending_runs.return_value = [sample_run]
    mock_ack_runs.return_value = 1

    processed_runs = []

    def msg_process(run):
        processed_runs.append(run)

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_runs) >= 1
    assert processed_runs[0]["_id"] == "run_123"
    mock_claim_pending_runs.assert_called()
    mock_ack_runs.assert_called_with(["run_123"])


def test_http_polling_consumer_no_pending_runs(
    mock_claim_pending_runs, mock_ack_runs, mock_time_sleep
):
    mock_claim_pending_runs.return_value = []

    processed_runs = []

    def msg_process(run):
        processed_runs.append(run)

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_runs) == 0
    mock_claim_pending_runs.assert_called()
    mock_ack_runs.assert_not_called()


def test_http_polling_consumer_processing_error(
    mock_claim_pending_runs,
    mock_ack_runs,
    mock_time_sleep,
    mock_report_run_status,
    sample_run,
):
    mock_claim_pending_runs.return_value = [sample_run]
    mock_ack_runs.return_value = 1

    def msg_process(run):
        raise Exception("Processing failed")

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    mock_claim_pending_runs.assert_called()
    mock_ack_runs.assert_called_with(["run_123"])
    mock_report_run_status.assert_called_with(
        "run_123",
        {
            "status": "FAILURE",
            "summary": "Agent failed to process the run",
        },
    )


def test_http_polling_consumer_exponential_backoff(
    mock_claim_pending_runs, mock_ack_runs, mock_time_sleep
):
    mock_claim_pending_runs.side_effect = Exception("API Error")

    consumer = HttpPollingConsumer(lambda run: None)

    Timer(0.2, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert consumer.backoff_seconds > 0


def test_http_polling_consumer_backoff_reset(
    mock_claim_pending_runs, mock_ack_runs, mock_time_sleep, sample_run
):
    call_count = [0]

    def claim_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("API Error")
        return [sample_run]

    mock_claim_pending_runs.side_effect = claim_side_effect
    mock_ack_runs.return_value = 1

    consumer = HttpPollingConsumer(lambda run: None)

    Timer(0.3, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert consumer.backoff_seconds == 0


def test_http_polling_consumer_ack_all_claimed_runs(
    mock_claim_pending_runs, mock_ack_runs, mock_time_sleep
):
    run1 = {
        "_id": "run_1",
        "id": "run_1",
        "payload": {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "body": {},
        },
    }
    run2 = {
        "_id": "run_2",
        "id": "run_2",
        "payload": {
            "type": "WEBHOOK",
            "url": "http://localhost:8080/webhook",
            "agent": True,
            "body": {},
        },
    }

    mock_claim_pending_runs.return_value = [run1, run2]
    mock_ack_runs.return_value = 1

    def msg_process(run):
        if run["_id"] == "run_2":
            raise Exception("Processing failed")

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert mock_ack_runs.call_count >= 2
    mock_ack_runs.assert_any_call(["run_1"])
    mock_ack_runs.assert_any_call(["run_2"])


def test_http_polling_consumer_ack_failure_skips_processing(
    mock_claim_pending_runs, mock_ack_runs, mock_time_sleep, sample_run
):
    mock_claim_pending_runs.return_value = [sample_run]
    mock_ack_runs.side_effect = Exception("Ack failed")

    processed_runs = []

    def msg_process(run):
        processed_runs.append(run)

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_runs) == 0
    mock_claim_pending_runs.assert_called()
    mock_ack_runs.assert_called()
