import logging
import os
from typing import Any

import pyjq as jq
import requests
from core.config import load_control_the_payload_config, settings
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

    def _apply_jq_on_field(self, mapping: dict[str, str] | str, body: dict) -> Any:
        if isinstance(mapping, dict):
            return {key: self._jq_exec(value, body) for key, value in mapping.items()}
        else:
            return self._jq_exec(mapping, body)

    def _prepare_payload(
            self, body: dict, invocation_method: dict
    ) -> tuple[str, str, dict, dict, dict]:
        control_the_payload_config = load_control_the_payload_config() or []
        context = {"body": body, "env": dict(os.environ)}

        action = next(
            (
                action_mapping
                for action_mapping in control_the_payload_config
                if (
                           type(action_mapping.mapping.enabled) != bool
                           and self._jq_exec(action_mapping.mapping.enabled, context) is True
                   )
                   or action_mapping.mapping.enabled is True
            ),
            None,
        )

        url = invocation_method.get("url", "")

        if not action:
            return consts.DEFAULT_HTTP_METHOD, url, body, {}, {}

        method = (
            self._apply_jq_on_field(action.mapping.method, context)
            if action.mapping.method
            else consts.DEFAULT_HTTP_METHOD
        )
        url = (
            self._apply_jq_on_field(action.mapping.url, context)
            if action.mapping.url
            else url
        )
        compiled_body = (
            self._apply_jq_on_field(action.mapping.body, context)
            if action.mapping.body
            else body
        )
        headers = (
            self._apply_jq_on_field(action.mapping.headers, context)
            if action.mapping.headers
            else {}
        )
        query = (
            self._apply_jq_on_field(action.mapping.query, context)
            if action.mapping.query
            else {}
        )

        return method, url, compiled_body, headers, query

    def invoke(self, body: dict, destination: dict) -> None:
        logger.info("WebhookInvoker - start - destination: %s", destination)
        method, url, compiled_body, headers, query = self._prepare_payload(
            body, destination
        )
        res = requests.request(
            method,
            url,
            json=compiled_body,
            headers=headers,
            params=query,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )
        logger.info(
            "WebhookInvoker - done - destination: %s, status code: %s",
            destination,
            res.status_code,
        )
        res.raise_for_status()


webhook_invoker = WebhookInvoker()
