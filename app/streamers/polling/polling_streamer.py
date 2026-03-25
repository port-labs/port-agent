import logging

from consumers.http_polling_consumer import HttpPollingConsumer
from core.config import settings
from processors.polling.polling_to_webhook_processor import PollingToWebhookProcessor
from streamers.base_streamer import BaseStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class PollingStreamer(BaseStreamer):
    def __init__(self) -> None:
        self.http_polling_consumer = HttpPollingConsumer(
            self.process_run, self.process_wf_node_run
        )
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
            logger.warning("Skip process run %s: not for agent", run_id)
            return

        self.processor.process_run(run, invocation_method)

    def process_wf_node_run(self, node_run: dict) -> None:
        node_run_id = node_run.get("identifier")
        if not node_run_id:
            logger.error("Workflow node run missing identifier: %s", node_run)
            return
        logger.info("Processing workflow node run: %s", node_run_id)

        config = node_run.get("config") or {}
        invocation_method = {
            "type": config.get("type"),
            "url": config.get("url"),
            "agent": config.get("agent"),
            "synchronized": config.get("synchronized", False),
            "method": config.get("method", "POST"),
            "headers": config.get("headers", {}),
        }

        if not invocation_method.pop("agent", False):
            logger.warning("Skip workflow node run %s: not for agent", node_run_id)
            return

        self.processor.process_wf_node_run(node_run, invocation_method)

    def stream(self) -> None:
        logger.info("Starting polling streamer")
        self.http_polling_consumer.start()
