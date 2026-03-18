import logging
import random
import signal
import time
from dataclasses import dataclass
from typing import Any, Callable

from consumers.base_consumer import BaseConsumer
from core.config import settings
from port_client import (
    ack_runs,
    ack_wf_node_run,
    claim_pending_runs,
    claim_pending_wf_node_runs,
    report_run_status,
    report_wf_node_run_status,
)

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _RunConfig:
    label: str
    id_field: str
    claim_fn: Callable[..., list[dict]]
    ack_fn: Callable[[str], Any]
    process_fn: Callable[[dict], None]
    report_failure_fn: Callable[[str], None]


class HttpPollingConsumer(BaseConsumer):
    def __init__(
        self,
        msg_process: Callable[[dict], None],
        wf_node_run_process: Callable[[dict], None] | None = None,
    ) -> None:
        self.running = False
        self.msg_process = msg_process
        self.wf_node_run_process = wf_node_run_process
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

    def _build_run_configs(self) -> list[_RunConfig]:
        configs: list[_RunConfig] = [
            _RunConfig(
                label="action run",
                id_field="id",
                claim_fn=claim_pending_runs,
                ack_fn=lambda run_id: ack_runs([run_id]),
                process_fn=self.msg_process,
                report_failure_fn=lambda run_id: report_run_status(
                    run_id,
                    {
                        "status": "FAILURE",
                        "summary": "Agent failed to process the run",
                    },
                ),
            ),
        ]
        if self.wf_node_run_process:
            configs.append(
                _RunConfig(
                    label="workflow node run",
                    id_field="identifier",
                    claim_fn=claim_pending_wf_node_runs,
                    ack_fn=ack_wf_node_run,
                    process_fn=self.wf_node_run_process,
                    report_failure_fn=lambda run_id: report_wf_node_run_status(
                        run_id,
                        {"status": "COMPLETED", "result": "FAILURE"},
                    ),
                )
            )
        return configs

    def _poll_runs(self, config: _RunConfig) -> int:
        if settings.DETAILED_LOGGING:
            logger.info("Polling for pending %ss...", config.label)
        runs = config.claim_fn(limit=settings.POLLING_RUNS_BATCH_SIZE)

        if runs:
            logger.info("Claimed %d pending %ss", len(runs), config.label)

            acked_runs = []
            for run in runs:
                run_id = run.get(config.id_field)
                if not run_id:
                    logger.error(
                        "%s missing %s field: %s",
                        config.label.capitalize(),
                        config.id_field,
                        run,
                    )
                    continue

                try:
                    if not config.ack_fn(run_id):
                        logger.warning(
                            "Failed to ack %s %s", config.label, run_id
                        )
                        continue
                    logger.info("Acked %s %s", config.label, run_id)
                    acked_runs.append(run)
                except Exception as ack_error:
                    logger.error(
                        "Failed to ack %s %s: %s",
                        config.label,
                        run_id,
                        str(ack_error),
                        exc_info=True,
                    )

            for run in acked_runs:
                run_id = run.get(config.id_field)
                try:
                    logger.info("Processing %s %s", config.label, run_id)
                    config.process_fn(run)
                except Exception as process_error:
                    logger.error(
                        "Failed to process %s %s: %s",
                        config.label,
                        run_id,
                        str(process_error),
                        exc_info=True,
                    )
                    try:
                        config.report_failure_fn(run_id)
                    except Exception as report_error:
                        logger.error(
                            "Failed to report failure status for %s %s: %s",
                            config.label,
                            run_id,
                            str(report_error),
                        )
        else:
            logger.debug("No pending %ss found", config.label)

        return len(runs)

    def start(self) -> None:
        self.running = True
        run_configs = self._build_run_configs()

        while self.running:
            has_more = False
            errored = False
            for config in run_configs:
                if not self.running:
                    break
                try:
                    count = self._poll_runs(config)
                    if count >= settings.POLLING_RUNS_BATCH_SIZE:
                        has_more = True
                except Exception as error:
                    errored = True
                    self._handle_error(error)
                    if not self.running:
                        break

            if errored:
                continue

            self._reset_backoff()

            if not has_more and self.running:
                time.sleep(settings.POLLING_INTERVAL_SECONDS)

    def exit_gracefully(self, *_: Any) -> None:
        logger.info("Exiting gracefully...")
        self.running = False
