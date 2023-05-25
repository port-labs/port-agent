import logging

import requests
from core.config import settings
from invokers.base_invoker import BaseInvoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class WebhookInvoker(BaseInvoker):
    def invoke(self, body: dict, destination: dict):
        logger.info("WebhookInvoker - start - destination: %s", destination)
        res = requests.post(
            destination.get("url", ""),
            json=body,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )
        logger.info(
            "WebhookInvoker - done - destination: %s, status code: %s",
            destination,
            res.status_code,
        )
        res.raise_for_status()

        return res


webhook_invoker = WebhookInvoker()
