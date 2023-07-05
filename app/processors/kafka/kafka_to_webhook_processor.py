import json
import logging

from confluent_kafka import Message
from core.config import settings
from invokers.webhook_invoker import webhook_invoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaToWebhookProcessor:
    @staticmethod
    def msg_process(msg: Message, invocation_method: dict, topic: str) -> None:
        logger.info("Raw message value: %s", msg.value())
        msg_value = json.loads(msg.value().decode())

        if invocation_method.get("method", "POST") not in [
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
        ]:
            logger.info(
                "Skip process message" " from topic %s, partition %d, offset %d: %s",
                topic,
                msg.partition(),
                msg.offset(),
                "HTTP method not supported",
            )
            return

        webhook_invoker.invoke(msg_value, invocation_method)
        logger.info(
            "Successfully processed message from topic %s, partition %d, offset %d",
            topic,
            msg.partition(),
            msg.offset(),
        )