import logging

import clients.port as port_client
import requests
from core.config import settings
from invokers.base_invoker import BaseInvoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class WebhookInvoker(BaseInvoker):
    def invoke(self, body: dict, destination: dict) -> None:
        logger.info("WebhookInvoker - start - destination: %s", destination)
        synchronized = destination.get("synchronized", False)
        method = destination.get("method", "POST")
        url = destination.get("url", "")

        if synchronized:
            run_id = body.get("context", {}).get("runId", "")
            port_client.send_run_log(
                run_id, f"Initiating action. Sending a POST request to - {url}"
            )

            try:
                res = requests.request(
                    method,
                    url,
                    json=body,
                    timeout=settings.WEBHOOK_SYNC_INVOKER_TIMEOUT,
                )
                logger.info(
                    "WebhookInvoker - done - destination: %s, status code: %s",
                    destination,
                    res.status_code,
                )

                port_client.send_run_log(
                    run_id,
                    f"Action finished with status: {res.reason} - {res.status_code}",
                )

                if res.headers.get("Content-Type", "").startswith("application/json"):
                    response_body = res.json()
                    summary = response_body.get("portSummary", "")
                else:
                    response_body = res.text
                    summary = ""

                port_client.update_run_response(run_id, response_body)

                res.raise_for_status()

                port_client.update_action_status(run_id, summary, "SUCCESS")

            except requests.exceptions.HTTPError as e:
                port_client.update_action_status(run_id, summary, "FAILURE")
                e.response.raise_for_status()
        else:
            res = requests.request(
                method, url, json=body, timeout=settings.WEBHOOK_ASYNC_INVOKER_TIMEOUT
            )

            logger.info(
                "WebhookInvoker - done - destination: %s, status code: %s",
                destination,
                res.status_code,
            )
            res.raise_for_status()


webhook_invoker = WebhookInvoker()
