import logging

from consumers.http_polling_consumer import HttpPollingConsumer
from core.config import settings
from processors.polling.polling_to_webhook_processor import PollingToWebhookProcessor
from streamers.base_streamer import BaseStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class PollingStreamer(BaseStreamer):
    def __init__(self) -> None:
        self.http_polling_consumer = HttpPollingConsumer(self.process_run)
        self.processor = PollingToWebhookProcessor()

    def process_run(self, run: dict) -> None:
        run_id = run.get("id")
        if not run_id:
            logger.error("Run missing id field: %s", run)
            return
        logger.info("Processing run: %s", run_id)

        payload = run["payload"]
        invocation_method = {
            "type": payload["type"],
            "url": payload["url"],
            "agent": payload["agent"],
            "synchronized": payload.get("synchronized", False),
            "method": payload.get("method", "POST"),
            "headers": payload.get("headers", {}),
        }

        if not invocation_method.pop("agent", False):
            logger.info("Skip process run %s: not for agent", run_id)
            return

        self.processor.process_run(run, invocation_method)

    def stream(self) -> None:
        logger.info("Starting polling streamer")
        self.http_polling_consumer.start()
