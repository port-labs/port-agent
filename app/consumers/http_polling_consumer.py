import logging
import random
import signal
import time
from typing import Any, Callable

from consumers.base_consumer import BaseConsumer
from core.config import settings
from port_client import (
    ack_runs,
    ack_workflow_run,
    claim_pending_runs,
    claim_pending_workflow_runs,
    report_run_status,
    report_workflow_node_run_status,
)

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class HttpPollingConsumer(BaseConsumer):
    def __init__(
        self,
        msg_process: Callable[[dict], None],
        workflow_run_process: Callable[[dict], None] | None = None,
    ) -> None:
        self.running = False
        self.msg_process = msg_process
        self.workflow_run_process = workflow_run_process
        self.backoff_seconds = 0
        self.max_backoff = settings.POLLING_MAX_BACKOFF_SECONDS
        self.initial_backoff = settings.POLLING_INITIAL_BACKOFF_SECONDS
        self.backoff_factor = settings.POLLING_BACKOFF_FACTOR
        self.backoff_jitter_factor = settings.POLLING_BACKOFF_JITTER_FACTOR
        self.max_failure_duration = settings.POLLING_MAX_FAILURE_DURATION_SECONDS
        self.first_failure_time: float | None = None

        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def _exponential_backoff(self) -> None:
        if self.backoff_seconds == 0:
            self.backoff_seconds = self.initial_backoff
        else:
            self.backoff_seconds = min(
                self.backoff_seconds * self.backoff_factor, self.max_backoff
            )

        jitter = random.uniform(0, self.backoff_seconds * self.backoff_jitter_factor)
        sleep_time = self.backoff_seconds + jitter

        logger.info(
            "Backing off for %.1f seconds (base: %.1fs)",
            sleep_time,
            self.backoff_seconds,
        )
        time.sleep(sleep_time)

    def _reset_backoff(self) -> None:
        if self.backoff_seconds > 0:
            logger.info("Backoff reset, polling recovered")
            self.backoff_seconds = 0
        self.first_failure_time = None

    def _handle_error(self, error: Exception) -> None:
        logger.error("Error during HTTP polling: %s", str(error), exc_info=True)
        if self.first_failure_time is None:
            self.first_failure_time = time.time()
        elif time.time() - self.first_failure_time > self.max_failure_duration:
            logger.error(
                "Polling has been failing for %d seconds, exiting",
                self.max_failure_duration,
            )
            self.exit_gracefully()
            return
        self._exponential_backoff()

    def start(self) -> None:
        self.running = True

        while self.running:
            try:
                if settings.DETAILED_LOGGING:
                    logger.info("Polling for pending runs...")

                runs = claim_pending_runs(limit=settings.POLLING_RUNS_BATCH_SIZE)
                self._process_action_runs(runs)

                workflow_runs = []
                if self.workflow_run_process:
                    workflow_runs = claim_pending_workflow_runs(
                        limit=settings.POLLING_RUNS_BATCH_SIZE
                    )
                    self._process_workflow_runs(workflow_runs)

                self._reset_backoff()

                total_runs = len(runs) + len(workflow_runs)
                if total_runs == 0:
                    logger.debug("No pending runs found")

                if total_runs < settings.POLLING_RUNS_BATCH_SIZE and self.running:
                    time.sleep(settings.POLLING_INTERVAL_SECONDS)

            except Exception as error:
                self._handle_error(error)
                if not self.running:
                    break

    def _process_action_runs(self, runs: list[dict]) -> None:
        if not runs:
            return

        logger.info("Claimed %d pending action runs", len(runs))

        acked_runs = []
        for run in runs:
            run_id = run.get("id")
            if not run_id:
                logger.error("Action run missing id field: %s", run)
                continue

            try:
                acked_count = ack_runs([run_id])
                if acked_count == 0:
                    logger.warning("Failed to ack action run %s", run_id)
                    continue
                logger.info("Acked action run %s", run_id)
                acked_runs.append(run)
            except Exception as ack_error:
                logger.error(
                    "Failed to ack action run %s: %s",
                    run_id,
                    str(),
                    exc_iack_errornfo=True,
                )

        for run in acked_runs:
            run_id = run.get("id")
            try:
                logger.info("Processing action run %s", run_id)
                self.msg_process(run)
            except Exception as process_error:
                logger.error(
                    "Failed to process action run %s: %s",
                    run_id,
                    str(process_error),
                    exc_info=True,
                )
                try:
                    report_run_status(
                        run_id,
                        {
                            "status": "FAILURE",
                            "summary": "Agent failed to process the run",
                        },
                    )
                except Exception as report_error:
                    logger.error(
                        "Failed to report failure status for action run %s: %s",
                        run_id,
                        str(report_error),
                    )

    def _process_workflow_runs(self, workflow_runs: list[dict]) -> None:
        if not workflow_runs:
            return

        logger.info("Claimed %d pending workflow node runs", len(workflow_runs))

        acked_runs = []
        for run in workflow_runs:
            run_identifier = run.get("identifier")
            if not run_identifier:
                logger.error("Workflow node run missing identifier field: %s", run)
                continue

            try:
                acked = ack_workflow_run(run_identifier)
                if not acked:
                    logger.warning(
                        "Failed to ack workflow node run %s", run_identifier
                    )
                    continue
                logger.info("Acked workflow node run %s", run_identifier)
                acked_runs.append(run)
            except Exception as ack_error:
                logger.error(
                    "Failed to ack workflow node run %s: %s",
                    run_identifier,
                    str(ack_error),
                    exc_info=True,
                )

        for run in acked_runs:
            run_identifier = run.get("identifier")
            try:
                logger.info("Processing workflow node run %s", run_identifier)
                self.workflow_run_process(run)
            except Exception as process_error:
                logger.error(
                    "Failed to process workflow node run %s: %s",
                    run_identifier,
                    str(process_error),
                    exc_info=True,
                )
                try:
                    report_workflow_node_run_status(
                        run_identifier,
                        {
                            "status": "FAILED",
                            "result": "FAILURE",
                            "logs": [
                                {"message": "Agent failed to process the run"}
                            ],
                        },
                    )
                except Exception as report_error:
                    logger.error(
                        "Failed to report failure status for workflow node run %s: %s",
                        run_identifier,
                        str(report_error),
                    )

    def exit_gracefully(self, *_: Any) -> None:
        logger.info("Exiting gracefully...")
        self.running = False
