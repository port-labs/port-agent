import logging
from typing import Any

import pyjq as jq
import requests
from core.config import control_the_payload_config, settings
from core.consts import consts
from invokers.base_invoker import BaseInvoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class WebhookInvoker(BaseInvoker):
    def _jq_exec(self, expression: str, context: dict) -> dict | None:
        try:
            return jq.first(expression, context)
        except Exception as e:
            logger.warning(
                "WebhookInvoker - jq error - expression: %s, error: %s", expression, e
            )
            return None

    def _apply_jq_on_field(
        self, mapping: dict[str, str] | str | None, body: dict, default: Any
    ) -> Any:
        if mapping is None:
            return default

        if isinstance(mapping, dict):
            return {key: self._jq_exec(value, body) for key, value in mapping.items()}
        else:
            return self._jq_exec(mapping, body)

    def _prepare_payload(self, body: dict) -> tuple[str, str | None, dict, dict, dict]:
        default_payload: tuple[str, None, dict, dict, dict] = (
            consts.DEFAULT_HTTP_METHOD,
            None,
            body,
            {},
            {},
        )

        action = next(
            (
                action_mapping
                for action_mapping in control_the_payload_config
                if (
                    type(action_mapping.enabled) != bool
                    and self._jq_exec(action_mapping.enabled, body) is True
                )
                or action_mapping.enabled is True
            ),
            None,
        )

        if not action:
            return default_payload

        method = self._apply_jq_on_field(action.method, body, default_payload[0])
        url = self._apply_jq_on_field(action.url, body, default_payload[1])
        compiled_body = self._apply_jq_on_field(action.body, body, default_payload[2])
        headers = self._apply_jq_on_field(action.headers, body, default_payload[3])
        query = self._apply_jq_on_field(action.query, body, default_payload[4])

        return method, url, compiled_body, headers, query

    def invoke(self, body: dict, invocation_method: dict) -> None:
        logger.info("WebhookInvoker - start - destination: %s", invocation_method)
        method, url, compiled_body, headers, query = self._prepare_payload(body)
        logger.info(
            "WebhookInvoker - request - method: %s, url: %s, body: %s, headers: %s, query: %s",
            method,
            url,
            compiled_body,
            headers,
            query,
        )
        res = requests.request(
            method,
            url or str(invocation_method.get("url", "")),
            json=compiled_body,
            headers=headers,
            params=query,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )
        logger.info(
            "WebhookInvoker - done - destination: %s, status code: %s",
            invocation_method,
            res.status_code,
        )
        res.raise_for_status()


webhook_invoker = WebhookInvoker()
