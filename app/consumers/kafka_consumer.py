import logging
import signal
from typing import Any, Callable

from confluent_kafka import Consumer, KafkaException, Message
from consumers.base_consumer import BaseConsumer
from core.config import settings
from core.consts import consts
from port_client import get_kafka_credentials

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaConsumer(BaseConsumer):
    def __init__(
            self, msg_process: Callable[[Message], None], consumer: Consumer = None
    ) -> None:
        self.running = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

        self.msg_process = msg_process

        if consumer:
            self.consumer = consumer
        else:
            logger.info("Getting Kafka credentials")
            username, password = get_kafka_credentials()
            conf = {
                "bootstrap.servers": settings.KAFKA_CONSUMER_BROKERS,
                "client.id": consts.KAFKA_CONSUMER_CLIENT_ID,
                "security.protocol": settings.KAFKA_CONSUMER_SECURITY_PROTOCOL,
                "sasl.mechanism": settings.KAFKA_CONSUMER_AUTHENTICATION_MECHANISM,
                "sasl.username": username,
                "sasl.password": password,
                "group.id": settings.KAFKA_CONSUMER_GROUP_ID,
                "session.timeout.ms": settings.KAFKA_CONSUMER_SESSION_TIMEOUT_MS,
                "auto.offset.reset": settings.KAFKA_CONSUMER_AUTO_OFFSET_RESET,
                "enable.auto.commit": "false",
            }
            self.consumer = Consumer(conf)

    def _on_assign(self, consumer: Consumer, partitions: Any) -> None:
        logger.info("Assignment: %s", partitions)
        if not partitions:
            logger.error(
                "No partitions assigned. This usually means that there is already a consumer"
                " with the same group id running. Closing this consumer...")
            self.exit_gracefully()

    def start(self) -> None:
        try:
            self.consumer.subscribe(
                [settings.KAFKA_RUNS_TOPIC, settings.KAFKA_CHANGE_LOG_TOPIC],
                on_assign=lambda _, partitions: logger.info(
                    "Assignment: %s", partitions
                ),
            )
            self.running = True
            while self.running:
                try:
                    msg = self.consumer.poll(timeout=1.0)
                    if msg is None:
                        continue
                    if msg.error():
                        raise KafkaException(msg.error())
                    else:
                        try:
                            logger.info(
                                "Process message"
                                " from topic %s, partition %d, offset %d",
                                msg.topic(),
                                msg.partition(),
                                msg.offset(),
                            )
                            self.msg_process(msg)
                        except Exception as process_error:
                            logger.error(
                                "Failed process message"
                                " from topic %s, partition %d, offset %d: %s",
                                msg.topic(),
                                msg.partition(),
                                msg.offset(),
                                str(process_error),
                            )
                        finally:
                            self.consumer.commit(asynchronous=False)
                except Exception as message_error:
                    logger.error(str(message_error))
        finally:
            self.consumer.close()

    def exit_gracefully(self, *_: Any) -> None:
        logger.info("Exiting gracefully...")
        self.running = False
