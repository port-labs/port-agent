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
            self.process_action_run, self.process_workflow_run
        )
        self.processor = PollingToWebhookProcessor()

    def process_action_run(self, run: dict) -> None:
        run_id = run.get("id")
        if not run_id:
            logger.error("Action run missing id field: %s", run)
            return
        logger.info("Processing action run: %s", run_id)

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
            logger.warning("Skip process action run %s: not for agent", run_id)
            return

        self.processor.process_run(run, invocation_method)

    def process_workflow_run(self, node_run: dict) -> None:
        node_run_identifier = node_run.get("identifier")
        if not node_run_identifier:
            logger.error("Workflow node run missing identifier field: %s", node_run)
            return
        logger.info("Processing workflow node run: %s", node_run_identifier)

        node = node_run.get("node")
        if not node:
            logger.error(
                "Workflow node run %s missing node data", node_run_identifier
            )
            return

        node_config = node.get("config", {})
        node_type = node_config.get("type")

        if node_type != "WEBHOOK":
            logger.warning(
                "Skip process workflow node run %s: unsupported node type %s",
                node_run_identifier,
                node_type,
            )
            return

        invocation_method = {
            "type": node_type,
            "url": node_config.get("url", ""),
            "agent": node_config.get("agent", False),
            "synchronized": node_config.get("synchronized", False),
            "method": node_config.get("method", "POST"),
            "headers": node_config.get("headers", {}),
        }

        if not invocation_method.pop("agent", False):
            logger.warning(
                "Skip process workflow node run %s: not for agent", node_run_identifier
            )
            return

        self.processor.process_workflow_run(node_run, invocation_method)

    def stream(self) -> None:
        logger.info("Starting polling streamer")
        self.http_polling_consumer.start()
