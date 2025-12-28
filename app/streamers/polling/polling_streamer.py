import logging

from consumers.http_polling_consumer import HttpPollingConsumer
from core.config import settings
from processors.https.https_to_webhook_processor import HttpsToWebhookProcessor
from streamers.base_streamer import BaseStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class PollingStreamer(BaseStreamer):
    def __init__(self) -> None:
        self.http_polling_consumer = HttpPollingConsumer(self.process_run)
        self.processor = HttpsToWebhookProcessor()

    def process_run(self, run: dict) -> None:
        logger.info("Processing run: %s", run.get("_id") or run.get("id"))

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
            logger.info(
                "Skip process run %s: not for agent",
                run.get("_id") or run.get("id"),
            )
            return

        self.processor.process_run(run, invocation_method)

    def stream(self) -> None:
        logger.info("Starting polling streamer")
        self.http_polling_consumer.start()
