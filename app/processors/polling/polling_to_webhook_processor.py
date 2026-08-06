import logging
from copy import deepcopy

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
        msg_value = deepcopy(payload["body"])

        msg_value.setdefault("headers", {})
        if headers := invocation_method.get("headers"):
            msg_value["headers"] = headers

        if "payload" not in msg_value:
            msg_value["payload"] = {}
        if "action" not in msg_value["payload"]:
            msg_value["payload"]["action"] = {}

        msg_value["payload"]["action"]["invocationMethod"] = invocation_method

        if "context" not in msg_value:
            msg_value["context"] = {}
        msg_value["context"]["runId"] = run_id

        webhook_invoker.invoke(
            msg_value, invocation_method, skip_signature_validation=True
        )

        logger.info("Successfully processed run %s", run_id)

    @staticmethod
    def process_wf_node_run(node_run: dict, invocation_method: dict) -> None:
        node_run_id = node_run.get("identifier")
        if not node_run_id:
            logger.error("Workflow node run missing identifier: %s", node_run)
            return
        logger.info("Processing workflow node run: %s", node_run_id)

        msg_value = {
            **deepcopy(invocation_method.get("body") or {}),
            "headers": invocation_method.get("headers") or {},
            "payload": {
                "action": {"invocationMethod": invocation_method},
            },
            "context": {
                "runId": node_run_id,
            },
        }

        if webhook_invoker.invoke(
            msg_value, invocation_method, skip_signature_validation=True
        ):
            logger.info("Successfully processed workflow node run %s", node_run_id)
