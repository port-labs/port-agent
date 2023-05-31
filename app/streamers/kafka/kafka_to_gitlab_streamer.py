import json
import logging
import os

from confluent_kafka import Message
from core.config import settings
from invokers.gitlab_pipeline_invoker import gitlab_pipeline_invoker
from streamers.kafka.base_kafka_streamer import BaseKafkaStreamer

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaToGitLabStreamer(BaseKafkaStreamer):
    @staticmethod
    def msg_process(msg: Message) -> None:
        logger.info("Raw message value: %s", msg.value())
        msg_value = json.loads(msg.value().decode())
        topic = msg.topic()
        invocation_method = BaseKafkaStreamer.get_invocation_method(msg_value, topic)

        invocation_method_error = BaseKafkaStreamer \
            .validate_invocation_method(invocation_method)
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

        user_inputs = msg_value.get("payload", {}).get("properties", {})

        gitlab_group = invocation_method.get("groupName", "")
        gitlab_project = invocation_method.get("projectName", "")

        if not gitlab_project or not gitlab_group:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d:"
                " GitLab project path is missing",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        ref = user_inputs.get("ref", invocation_method.get("defaultRef", "main"))

        trigger_token = os.environ.get(f'{gitlab_group}_{gitlab_project}', "")

        if not trigger_token:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d:"
                " no token env variable found for project %s/%s",
                topic,
                msg.partition(),
                msg.offset(),
                gitlab_group,
                gitlab_project
            )
            return

        body = {
            'token': trigger_token,
            'ref': ref,
        }

        if not invocation_method.get("omitUserInputs"):
            # GitLab variables must be strings, to be sent to a GitLab pipeline
            body.update({'variables': {key: str(value) for key, value in user_inputs.items()}})

        if not invocation_method.get("omitPayload"):
            body["port_payload"] = msg_value.copy()

        try:
            gitlab_pipeline_invoker\
                .invoke(body, f'{gitlab_group}%2F{gitlab_project}')

        except Exception as e:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d:"
                " Failed to trigger GitLab Pipeline: %s",
                topic,
                msg.partition(),
                msg.offset(),
                e,
            )
            return

        logger.info(
            "Successfully processed message from topic %s, partition %d, offset %d",
            topic,
            msg.partition(),
            msg.offset(),
        )
