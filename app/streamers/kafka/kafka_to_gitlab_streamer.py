import json
import logging
import time

from confluent_kafka import Message
from core.config import settings
from core.consts import consts
import clients.port as port_client
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

        user_inputs = msg_value.get("payload", {}).get("properties", {})

        gitlab_group = invocation_method.get("groupName", "")
        gitlab_project = invocation_method.get("projectName", "")

        if not gitlab_project or not gitlab_group:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: GitLab project path is missing",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return

        ref = user_inputs.pop("ref")
        if not ref:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: Ref wasn't passed to agent",
                topic,
                msg.partition(),
                msg.offset(),
            )
            return
        project_env = f'{gitlab_group}_{gitlab_project}'
        trigger_token = os.environ.get(f'{gitlab_group}_{gitlab_project}', "")

        if not trigger_token:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: no token found for project %s/%s",
                topic,
                msg.partition(),
                msg.offset(),
                gitlab_project
            )
            return

        body = {
            'token': trigger_token,
            'ref': ref,
            **{f'variables[{key}]': value for key, value in user_inputs.items()}
        }

        if not user_inputs.get("omitPayload"):
            body["port_payload"] = msg_value.copy()

        if not user_inputs.get("omitUserInputs"):
            body["user_inputs"] = user_inputs.copy()

        try:
            project_url = f'{gitlab_group}%2F{gitlab_project}'
            res = gitlab_pipeline_invoker.invoke(body, project_url)

            if user_inputs.get("reportWorkflowStatus", True):

                start_time = time.time()
                elapsed_time = 0
                while elapsed_time < settings.GITLAB_PIPELINE_REPORT_TIMEOUT:
                    pipeline = gitlab_pipeline_invoker\
                        .get_running_pipeline(project_url,
                                              res.get("id", ""),
                                              os.environ.get(f'{project_env}_access', ""))

                    # Check if pipeline is stopped
                    if pipeline.get("finished_at", ""):
                        gitlab_status = pipeline.get("status", "")
                        if gitlab_status == "success":
                            port_status = "SUCCESS"
                            message = "Pipeline was completed successfully"
                        else:
                            port_status = "FAILURE"
                            message = f"GitLab Pipeline finished with status: {gitlab_status}"

                        port_client.update_action(msg_value.get("context", {}).get("runId", ""),
                                                  message,
                                                  port_status)
                        break

                    elapsed_time = time.time() - start_time
                    time.sleep(settings.GITLAB_PIPELINE_REPORT_INTERVAL)

        except Exception as e:
            logger.info(
                "Skip process message"
                " from topic %s, partition %d, offset %d: Failed to trigger GitLab Pipeline: %s",
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