import logging
import random
import signal
import time
from typing import Any, Callable

from consumers.base_consumer import BaseConsumer
from core.config import settings
from port_client import ack_runs, claim_pending_runs

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class HttpPollingConsumer(BaseConsumer):
    def __init__(self, msg_process: Callable[[dict], None]) -> None:
        self.running = False
        self.msg_process = msg_process
        self.backoff_seconds = 0
        self.max_backoff = settings.POLLING_MAX_BACKOFF_SECONDS
        self.initial_backoff = settings.POLLING_INITIAL_BACKOFF_SECONDS
        self.backoff_factor = settings.POLLING_BACKOFF_FACTOR
        self.backoff_jitter_factor = settings.POLLING_BACKOFF_JITTER_FACTOR

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

        time.sleep(sleep_time)

    def _reset_backoff(self) -> None:
        if self.backoff_seconds > 0:
            self.backoff_seconds = 0

    def start(self) -> None:
        self.running = True

        while self.running:
            try:
                runs = claim_pending_runs(limit=settings.POLLING_RUNS_BATCH_SIZE)
                self._reset_backoff()
                if runs:
                    logger.info("Claimed %d pending runs", len(runs))

                    for run in runs:
                        run_id = run.get("_id") or run.get("id")

                        try:
                            acked_count = ack_runs([run_id])
                            if acked_count == 0:
                                logger.warning("Failed to ack run %s", run_id)
                                continue
                            logger.info("Acked run %s", run_id)
                        except Exception as ack_error:
                            logger.error(
                                "Failed to ack run %s: %s",
                                run_id,
                                str(ack_error),
                                exc_info=True,
                            )
                            continue

                        try:
                            logger.info("Processing run %s", run_id)
                            self.msg_process(run)
                        except Exception as process_error:
                            logger.error(
                                "Failed to process run %s: %s",
                                run_id,
                                str(process_error),
                                exc_info=True,
                            )
                else:
                    logger.debug("No pending runs found")

                if self.running:
                    time.sleep(settings.POLLING_INTERVAL_SECONDS)

            except Exception as error:
                logger.error(
                    "Error during HTTP polling: %s", str(error), exc_info=True
                )
                self._exponential_backoff()

    def exit_gracefully(self, *_: Any) -> None:
        logger.info("Exiting gracefully...")
        self.running = False

