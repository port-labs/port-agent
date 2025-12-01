import json
import logging

from confluent_kafka import Consumer, Message
from consumers.kafka_consumer import KafkaConsumer
from core.config import settings
from processors.kafka.kafka_to_webhook_processor import KafkaToWebhookProcessor
from streamers.base_streamer import BaseStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaStreamer(BaseStreamer):
    def __init__(self, consumer: Consumer = None) -> None:
        self.kafka_consumer = KafkaConsumer(self.msg_process, consumer)

    def msg_process(self, msg: Message) -> None:
        topic = msg.topic()
        if settings.VERBOSE_LOGGING:
            logger.info("Raw message value: %s", msg.value())
        logger.info(
            "Received message - topic: %s, partition: %d, offset: %d",
            topic,
            msg.partition(),
            msg.offset(),
        )
        msg_value = json.loads(msg.value().decode())
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
