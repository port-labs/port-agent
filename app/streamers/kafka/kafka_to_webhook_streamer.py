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

        if not invocation_method.pop("agent", False):
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: not for agent",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        if invocation_method.pop("type", "") != consts.INVOCATION_TYPE_WEBHOOK:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: not for webhook invoker",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        webhook_invoker.invoke(msg_value, invocation_method)
        logger.info(
            "Successfully processed message from topic %s, partition %d, offset %d",
            topic,
            msg.partition(),
            msg.offset(),
        )
