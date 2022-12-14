import logging
from abc import abstractmethod

from confluent_kafka import Consumer, Message
from consumers.kafka_consumer import KafkaConsumer
from core.config import settings
from streamers.base_streamer import BaseStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class BaseKafkaStreamer(BaseStreamer):
    def __init__(self, consumer: Consumer = None) -> None:
        self.kafka_consumer = KafkaConsumer(self.msg_process, consumer)

    @staticmethod
    @abstractmethod
    def msg_process(msg: Message) -> None:
        pass

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
