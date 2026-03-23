import json
import logging

from confluent_kafka import Message
from core.config import settings
from invokers.webhook_invoker import webhook_invoker
from port_client import report_wf_node_run_status
from utils import log_by_detail_level

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaToWebhookProcessor:
    @staticmethod
    def msg_process(msg: Message, invocation_method: dict, topic: str) -> None:
        log_by_detail_level(
            logger.info,
            "Processing message - topic: %s, partition: %d, offset: %d",
            [topic, msg.partition(), msg.offset()],
            "raw_value",
            msg.value(),
        )
        msg_value = json.loads(msg.value().decode())

        if topic == settings.KAFKA_WF_NODE_RUNS_TOPIC:
            KafkaToWebhookProcessor._process_wf_node_run(
                msg_value, invocation_method
            )
            return

        webhook_invoker.invoke(msg_value, invocation_method)
        logger.info(
            "Successfully processed message from topic %s, partition %d, offset %d",
            topic,
            msg.partition(),
            msg.offset(),
        )

    @staticmethod
    def _process_wf_node_run(
        node_run: dict, invocation_method: dict
    ) -> None:
        node_run_id = node_run.get("identifier")
        if not node_run_id:
            logger.error("Workflow node run missing identifier: %s", node_run)
            return
        logger.info("Processing workflow node run: %s", node_run_id)

        config = node_run.get("config") or {}
        msg_value = {
            "headers": invocation_method.get("headers", {}),
            "payload": {
                "action": {"invocationMethod": invocation_method},
            },
            "context": {
                "nodeRunIdentifier": node_run_id,
                "nodeConfig": config,
            },
        }

        try:
            webhook_invoker.invoke(msg_value, invocation_method)
            report_wf_node_run_status(
                node_run_id,
                {"status": "COMPLETED", "result": "SUCCESS"},
            )
            logger.info(
                "Successfully processed workflow node run %s",
                node_run_id,
            )
        except Exception:
            logger.error(
                "Webhook failed for workflow node run %s",
                node_run_id,
                exc_info=True,
            )
            try:
                report_wf_node_run_status(
                    node_run_id,
                    {"status": "COMPLETED", "result": "FAILURE"},
                )
            except Exception:
                logger.error(
                    "Failed to report failure status for workflow node run %s",
                    node_run_id,
                    exc_info=True,
                )
            raise
