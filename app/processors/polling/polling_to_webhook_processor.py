import logging

from core.config import settings
from invokers.webhook_invoker import webhook_invoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class PollingToWebhookProcessor:
    @staticmethod
    def process_run(run: dict, invocation_method: dict) -> None:
        run_id = run.get("id")
        if not run_id:
            logger.error("Run missing id field: %s", run)
            return
        logger.info("Processing action run: %s", run_id)

        payload = run["payload"]
        msg_value = payload["body"].copy()

        msg_value["headers"] = invocation_method.get("headers", {})

        if "payload" not in msg_value:
            msg_value["payload"] = {}
        if "action" not in msg_value["payload"]:
            msg_value["payload"]["action"] = {}
        msg_value["payload"]["action"]["invocationMethod"] = invocation_method

        if "context" not in msg_value:
            msg_value["context"] = {}
        msg_value["context"]["runId"] = run_id

        webhook_invoker.invoke(msg_value, invocation_method)

        logger.info("Successfully processed run %s", run_id)
