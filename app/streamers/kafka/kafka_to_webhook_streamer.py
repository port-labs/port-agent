import json
import logging

from confluent_kafka import Message
from core.config import settings
from core.consts import consts
from invokers.webhook_invoker import webhook_invoker
from streamers.kafka.base_kafka_streamer import BaseKafkaStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaToWebhookStreamer(BaseKafkaStreamer):
    @staticmethod
    def msg_process(msg: Message) -> None:
        logger.info("Raw message value: %s", msg.value())
        msg_value = json.loads(msg.value().decode())
        topic = msg.topic()
        invocation_method = BaseKafkaStreamer.get_invocation_method(msg_value, topic)

        invocation_method_error = BaseKafkaStreamer.validate_invocation_method(invocation_method)
        if invocation_method_error != "":
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: %s",
                topic,
                msg.partition(),
                msg.offset(),
                invocation_method_error
            )
            return

        webhook_invoker.invoke(msg_value, invocation_method)
        logger.info(
            "Successfully processed message from topic %s, partition %d, offset %d",
            topic,
            msg.partition(),
            msg.offset(),
        )
