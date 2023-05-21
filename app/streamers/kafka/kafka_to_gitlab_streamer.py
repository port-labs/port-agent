import json
import logging

from confluent_kafka import Message
from core.config import settings
from core.consts import consts
from invokers.gitlab_pipeline_invoker import gitlab_pipeline_invoker
from streamers.kafka.base_kafka_streamer import BaseKafkaStreamer
import os

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaToGitLabStreamer(BaseKafkaStreamer):

    @staticmethod
    def msg_process(msg: Message) -> None:
        logger.info("Raw message value: %s", msg.value())
        msg_value = json.loads(msg.value().decode())
        topic = msg.topic()
        invocation_method = BaseKafkaStreamer.get_invocation_method(msg_value, topic)
        user_inputs = msg_value.get("payload", {}).get("properties", {})
        project_id = invocation_method.get("projectId", "")
        ref = user_inputs.get("ref")

        if invocation_method.pop("type", "") != consts.INVOCATION_TYPE_GITLAB_PIPELINE:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: not for GitLab Pipeline invoker",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        if not project_id:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: Project ID wasn't passed to agent",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        if not ref:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: Ref wasn't passed to agent",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        trigger_token = os.environ.get(project_id, "")

        if not trigger_token:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: no token found for project id %s",
                topic,
                msg.partition(),
                msg.offset(),
                project_id
            )
            return

        payload = {
            'token': trigger_token,
            'ref': ref,
            **{f"variables[{key}]": value for variable in user_inputs.get("variables", []) for key, value in
               variable.items()}
        }

        gitlab_pipeline_invoker.invoke(payload, f"{settings.GITLAB_URL}/api/v4/projects/{project_id}/trigger/pipeline")

        logger.info(
            "Successfully processed message from topic %s, partition %d, offset %d",
            topic,
            msg.partition(),
            msg.offset(),
        )
