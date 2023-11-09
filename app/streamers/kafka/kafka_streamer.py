import json
import logging

from confluent_kafka import Consumer, Message
from consumers.kafka_consumer import KafkaConsumer
from core.config import settings
from core.consts import consts
from processors.kafka.kafka_to_gitlab_processor import KafkaToGitLabProcessor
from processors.kafka.kafka_to_webhook_processor import KafkaToWebhookProcessor
from streamers.base_streamer import BaseStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

KAFKA_INVOCATIONS = {
    "WEBHOOK": KafkaToWebhookProcessor,
    "GITLAB": KafkaToGitLabProcessor,
}


class KafkaStreamer(BaseStreamer):
    def __init__(self, consumer: Consumer = None) -> None:
        self.kafka_consumer = KafkaConsumer(self.msg_process, consumer)

    def msg_process(self, msg: Message) -> None:
        logger.info("Raw message value: %s", msg.value())
        msg_value = json.loads(msg.value().decode())
        topic = msg.topic()
        invocation_method = self.get_invocation_method(msg_value, topic)

        invocation_method_error = self.validate_invocation_method(invocation_method)
        if invocation_method_error != "":
            logger.info(
                "Skip process message" " from topic %s, partition %d, offset %d: %s",
                topic,
                msg.partition(),
                msg.offset(),
                invocation_method_error,
            )
            return

        kafka_processor = KAFKA_INVOCATIONS[invocation_method.get("type")]
        kafka_processor.msg_process(msg, invocation_method, topic)

    @staticmethod
    def validate_invocation_method(invocation_method: dict) -> str:
        if not invocation_method.pop("agent", False):
            return "not for agent"

        if invocation_method.get("type", "") not in KAFKA_INVOCATIONS.keys():
            return "Invocation type not found / not supported"

        return ""

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
