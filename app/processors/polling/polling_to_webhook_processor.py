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

        webhook_invoker.invoke(
            msg_value, invocation_method, skip_signature_validation=True
        )

        logger.info("Successfully processed action run %s", run_id)

    @staticmethod
    def process_workflow_run(node_run: dict, invocation_method: dict) -> None:
        node_run_identifier = node_run.get("identifier")
        if not node_run_identifier:
            logger.error("Workflow node run missing identifier field: %s", node_run)
            return
        logger.info("Processing workflow node run: %s", node_run_identifier)

        node_config = node_run.get("node", {}).get("config", {})
        workflow_run = node_run.get("workflowRun", {})

        base_body = node_config.get("body", {})
        msg_value = base_body.copy() if isinstance(base_body, dict) else {}

        msg_value["headers"] = invocation_method.get("headers", {})

        if "payload" not in msg_value:
            msg_value["payload"] = {}
        msg_value["payload"]["nodeRunIdentifier"] = node_run_identifier
        msg_value["payload"]["workflowRunIdentifier"] = workflow_run.get("identifier")
        msg_value["payload"]["nodeConfig"] = node_config
        msg_value["payload"]["output"] = node_run.get("output", {})

        if "context" not in msg_value:
            msg_value["context"] = {}
        msg_value["context"]["nodeRunIdentifier"] = node_run_identifier
        msg_value["context"]["workflowRunIdentifier"] = workflow_run.get("identifier")

        webhook_invoker.invoke(
            msg_value, invocation_method, skip_signature_validation=True
        )

        logger.info("Successfully processed workflow node run %s", node_run_identifier)
