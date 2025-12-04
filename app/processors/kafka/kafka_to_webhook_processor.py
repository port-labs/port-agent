import json
import logging

from confluent_kafka import Message
from core.config import settings
from invokers.webhook_invoker import webhook_invoker
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

        webhook_invoker.invoke(msg_value, invocation_method)
        logger.info(
            "Successfully processed message from topic %s, partition %d, offset %d",
            topic,
            msg.partition(),
            msg.offset(),
        )
