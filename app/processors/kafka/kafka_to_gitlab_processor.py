import json
import logging
import os

from confluent_kafka import Message
from core.config import settings
from invokers.gitlab_pipeline_invoker import gitlab_pipeline_invoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class KafkaToGitLabProcessor:
    @staticmethod
    def msg_process(msg: Message, invocation_method: dict, topic: str) -> None:
        logger.info("Raw message value: %s", msg.value())
        msg_value = json.loads(msg.value().decode())
        user_inputs = msg_value.get("payload", {}).get("properties", {})
        gitlab_group = invocation_method.get("groupName", "")
        gitlab_project = invocation_method.get("projectName", "")

        if not gitlab_project or not gitlab_group:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: %s",
                topic,
                msg.partition(),
                msg.offset(),
                "GitLab project path is missing"
            )
            return

        ref = user_inputs.get("ref", invocation_method.get("defaultRef", "main"))

        trigger_token = os.environ.get(f'{gitlab_group}_{gitlab_project.replace("/", "_")}', "")

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
            body.update({'variables': {key: str(value) for key,
                                       value in user_inputs.items()}})

        if not invocation_method.get("omitPayload"):
            body["port_payload"] = msg_value.copy()

        gitlab_pipeline_invoker.invoke(body, f'{gitlab_group}%2F{gitlab_project}')

        logger.info(
            "Successfully processed message from topic %s, partition %d, offset %d",
            topic,
            msg.partition(),
            msg.offset(),
        )
