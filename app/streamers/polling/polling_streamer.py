import logging

from consumers.http_polling_consumer import HttpPollingConsumer
from core.config import settings
from processors.polling.polling_to_webhook_processor import PollingToWebhookProcessor
from streamers.base_streamer import BaseStreamer
from utils import get_invocation_method_object

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# The polling API sends the invocation method flattened on the run payload, while
# the event kept in payload.body carries the complete object. Only keys actually
# present in the flattened payload may override the ones from the event.
FLATTENED_INVOCATION_METHOD_KEYS = (
    "type",
    "url",
    "agent",
    "synchronized",
    "method",
    "headers",
)
PORT_EVENT_KEYS = ("context", "payload", "trigger")


def _looks_like_port_event(body: dict) -> bool:
    return any(key in body for key in PORT_EVENT_KEYS)


def _with_defaults(invocation_method: dict) -> dict:
    defaults = {"synchronized": False, "method": "POST", "headers": {}}
    for key, default in defaults.items():
        invocation_method.setdefault(key, default)
    return invocation_method


class PollingStreamer(BaseStreamer):
    def __init__(self) -> None:
        self.http_polling_consumer = HttpPollingConsumer(
            self.process_run, self.process_wf_node_run
        )
        self.processor = PollingToWebhookProcessor()

    def process_run(self, run: dict) -> None:
        run_id = run.get("id")
        if not run_id:
            logger.error("Run missing id field: %s", run)
            return
        logger.info("Processing run: %s", run_id)

        payload = run["payload"]
        body = payload.get("body") or {}
        if not _looks_like_port_event(body):
            logger.warning(
                "Run %s: payload.body does not look like a Port event, keys: %s",
                run_id,
                sorted(body),
            )

        invocation_method = _with_defaults(
            {
                **get_invocation_method_object(body),
                **{
                    key: payload[key]
                    for key in FLATTENED_INVOCATION_METHOD_KEYS
                    if key in payload
                },
            }
        )

        if not invocation_method.get("type") or not invocation_method.get("url"):
            raise ValueError(f"Run {run_id} has no invocation method type or url")

        if not invocation_method.pop("agent", False):
            logger.warning("Skip process run %s: not for agent", run_id)
            return

        self.processor.process_run(run, invocation_method)

    def process_wf_node_run(self, node_run: dict) -> None:
        node_run_id = node_run.get("identifier")
        if not node_run_id:
            logger.error("Workflow node run missing identifier: %s", node_run)
            return
        logger.info("Processing workflow node run: %s", node_run_id)

        invocation_method = {**(node_run.get("config") or {})}

        if not invocation_method.pop("agent", False):
            logger.warning("Skip workflow node run %s: not for agent", node_run_id)
            return

        self.processor.process_wf_node_run(node_run, invocation_method)

    def stream(self) -> None:
        logger.info("Starting polling streamer")
        self.http_polling_consumer.start()
