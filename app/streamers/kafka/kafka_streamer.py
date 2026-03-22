import json
import logging

from confluent_kafka import Consumer, Message
from consumers.kafka_consumer import KafkaConsumer
from core.config import settings
from processors.kafka.kafka_to_webhook_processor import KafkaToWebhookProcessor
from streamers.base_streamer import BaseStreamer
from utils import log_by_detail_level

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaStreamer(BaseStreamer):
    def __init__(self, consumer: Consumer = None) -> None:
        self.kafka_consumer = KafkaConsumer(self.msg_process, consumer)

    def msg_process(self, msg: Message) -> None:
        topic = msg.topic()
        log_by_detail_level(
            logger.info,
            "Received message - topic: %s, partition: %d, offset: %d",
            [topic, msg.partition(), msg.offset()],
            "raw_value",
            msg.value(),
        )
        msg_value = json.loads(msg.value().decode())

        if topic == settings.KAFKA_WF_NODE_RUNS_TOPIC:
            self.process_wf_node_run(msg_value)
            return

        invocation_method = self.get_invocation_method(msg_value, topic)

        if not invocation_method.pop("agent", False):
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: not for agent",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        KafkaToWebhookProcessor.msg_process(msg, invocation_method, topic)

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
            logger.warning(
                "Skip workflow node run %s: not for agent", node_run_id
            )
            return

        KafkaToWebhookProcessor.process_wf_node_run(node_run, invocation_method)

    @staticmethod
    def get_invocation_method(msg_value: dict, topic: str) -> dict:
        if topic == settings.KAFKA_RUNS_TOPIC:
            return (
                msg_value.get("payload", {})
                .get("action", {})
                .get("invocationMethod", {})
            )

        if topic == settings.KAFKA_CHANGE_LOG_TOPIC:
            return msg_value.get("changelogDestination", {})

        return {}

    def stream(self) -> None:
        self.kafka_consumer.start()
