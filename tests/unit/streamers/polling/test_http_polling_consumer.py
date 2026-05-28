from threading import Timer
from typing import Any, Dict, List

from consumers.http_polling_consumer import HttpPollingConsumer


def terminate_consumer(consumer: HttpPollingConsumer) -> None:
    consumer.exit_gracefully()


def test_http_polling_consumer_successful_poll(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_time_sleep: Any,
    sample_run: Dict[str, Any],
) -> None:
    mock_claim_pending_runs.return_value = [sample_run]
    mock_ack_runs.return_value = 1

    processed_runs: List[Any] = []

    def msg_process(run: Any) -> None:
        processed_runs.append(run)

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_runs) >= 1
    assert processed_runs[0]["_id"] == "run_123"
    mock_claim_pending_runs.assert_called()
    mock_ack_runs.assert_called_with(["run_123"])


def test_http_polling_consumer_no_pending_runs(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_time_sleep: Any,
) -> None:
    mock_claim_pending_runs.return_value = []

    processed_runs: List[Any] = []

    def msg_process(run: Any) -> None:
        processed_runs.append(run)

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_runs) == 0
    mock_claim_pending_runs.assert_called()
    mock_ack_runs.assert_not_called()


def test_http_polling_consumer_processing_error(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_time_sleep: Any,
    mock_report_run_status: Any,
    sample_run: Dict[str, Any],
) -> None:
    mock_claim_pending_runs.return_value = [sample_run]
    mock_ack_runs.return_value = 1

    def msg_process(run: Any) -> None:
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
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_time_sleep: Any,
) -> None:
    mock_claim_pending_runs.side_effect = Exception("API Error")

    consumer = HttpPollingConsumer(lambda run: None)

    Timer(0.2, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert consumer.backoff_seconds > 0


def test_http_polling_consumer_backoff_reset(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_time_sleep: Any,
    sample_run: Dict[str, Any],
) -> None:
    call_count = [0]

    def claim_side_effect(*args: Any, **kwargs: Any) -> List[Any]:
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
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_time_sleep: Any,
) -> None:
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

    def msg_process(run: Any) -> None:
        if run["_id"] == "run_2":
            raise Exception("Processing failed")

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert mock_ack_runs.call_count >= 2
    mock_ack_runs.assert_any_call(["run_1"])
    mock_ack_runs.assert_any_call(["run_2"])


def test_http_polling_consumer_ack_failure_skips_processing(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_time_sleep: Any,
    sample_run: Dict[str, Any],
) -> None:
    mock_claim_pending_runs.return_value = [sample_run]
    mock_ack_runs.side_effect = Exception("Ack failed")

    processed_runs: List[Any] = []

    def msg_process(run: Any) -> None:
        processed_runs.append(run)

    consumer = HttpPollingConsumer(msg_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_runs) == 0
    mock_claim_pending_runs.assert_called()
    mock_ack_runs.assert_called()


# --- Workflow node run tests ---


def test_http_polling_consumer_wf_node_run_successful_poll(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_ack_wf_node_run: Any,
    mock_time_sleep: Any,
    sample_wf_node_run: Dict[str, Any],
) -> None:
    mock_claim_pending_runs.return_value = []
    mock_claim_pending_wf_node_runs.return_value = [sample_wf_node_run]
    mock_ack_wf_node_run.return_value = True

    processed_node_runs: List[Any] = []

    def workflow_process(node_run: Any) -> None:
        processed_node_runs.append(node_run)

    consumer = HttpPollingConsumer(lambda r: None, workflow_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_node_runs) >= 1
    assert processed_node_runs[0]["identifier"] == "wfnr_abc123"
    mock_claim_pending_wf_node_runs.assert_called()
    mock_ack_wf_node_run.assert_called_with("wfnr_abc123")


def test_http_polling_consumer_workflow_no_pending_node_runs(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_ack_wf_node_run: Any,
    mock_time_sleep: Any,
) -> None:
    mock_claim_pending_runs.return_value = []
    mock_claim_pending_wf_node_runs.return_value = []

    processed_node_runs: List[Any] = []

    consumer = HttpPollingConsumer(
        lambda r: None, lambda nr: processed_node_runs.append(nr)
    )

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_node_runs) == 0
    mock_claim_pending_wf_node_runs.assert_called()
    mock_ack_wf_node_run.assert_not_called()


def test_http_polling_consumer_workflow_processing_error(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_ack_wf_node_run: Any,
    mock_report_wf_node_run_status: Any,
    mock_time_sleep: Any,
    sample_wf_node_run: Dict[str, Any],
) -> None:
    mock_claim_pending_runs.return_value = []
    mock_claim_pending_wf_node_runs.return_value = [sample_wf_node_run]
    mock_ack_wf_node_run.return_value = True

    def workflow_process(node_run: Any) -> None:
        raise Exception("Processing failed")

    consumer = HttpPollingConsumer(lambda r: None, workflow_process)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    mock_claim_pending_wf_node_runs.assert_called()
    mock_ack_wf_node_run.assert_called_with("wfnr_abc123")
    mock_report_wf_node_run_status.assert_called_with(
        "wfnr_abc123",
        {"status": "COMPLETED", "result": "FAILED"},
    )


def test_http_polling_consumer_workflow_ack_failure_skips_processing(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_ack_wf_node_run: Any,
    mock_time_sleep: Any,
    sample_wf_node_run: Dict[str, Any],
) -> None:
    mock_claim_pending_runs.return_value = []
    mock_claim_pending_wf_node_runs.return_value = [sample_wf_node_run]
    mock_ack_wf_node_run.side_effect = Exception("Ack failed")

    processed_node_runs: List[Any] = []

    consumer = HttpPollingConsumer(
        lambda r: None, lambda nr: processed_node_runs.append(nr)
    )

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_node_runs) == 0
    mock_claim_pending_wf_node_runs.assert_called()
    mock_ack_wf_node_run.assert_called()


def test_http_polling_consumer_workflow_skipped_without_callback(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_time_sleep: Any,
) -> None:
    mock_claim_pending_runs.return_value = []

    consumer = HttpPollingConsumer(lambda r: None)

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    mock_claim_pending_wf_node_runs.assert_not_called()


def test_http_polling_consumer_both_action_and_workflow_runs(
    mock_claim_pending_runs: Any,
    mock_ack_runs: Any,
    mock_claim_pending_wf_node_runs: Any,
    mock_ack_wf_node_run: Any,
    mock_time_sleep: Any,
    sample_run: Dict[str, Any],
    sample_wf_node_run: Dict[str, Any],
) -> None:
    mock_claim_pending_runs.return_value = [sample_run]
    mock_ack_runs.return_value = 1
    mock_claim_pending_wf_node_runs.return_value = [sample_wf_node_run]
    mock_ack_wf_node_run.return_value = True

    processed_runs: List[Any] = []
    processed_node_runs: List[Any] = []

    consumer = HttpPollingConsumer(
        lambda r: processed_runs.append(r),
        lambda nr: processed_node_runs.append(nr),
    )

    Timer(0.1, lambda: consumer.exit_gracefully()).start()
    consumer.start()

    assert len(processed_runs) >= 1
    assert processed_runs[0]["id"] == "run_123"
    assert len(processed_node_runs) >= 1
    assert processed_node_runs[0]["identifier"] == "wfnr_abc123"
