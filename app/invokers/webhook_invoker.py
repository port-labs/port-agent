import logging
from dataclasses import dataclass
from typing import Any

import pyjq as jq
import requests
from core.config import Mapping, control_the_payload_config, settings
from core.consts import consts
from flatten_dict import flatten, unflatten
from invokers.base_invoker import BaseInvoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@dataclass
class RequestPayload:
    method: str
    url: str
    body: dict
    headers: dict
    query: dict


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
        self, mapping: dict[str, str] | str | None, body: dict
    ) -> Any:
        if isinstance(mapping, dict):
            flatten_dict = flatten(mapping)
            parsed_jq = {
                key: self._jq_exec(value, body) if type(value) == str else value
                for key, value in flatten_dict.items()
            }
            return unflatten(parsed_jq)
        else:
            return self._jq_exec(mapping, body)

    def _prepare_payload(self, body: dict, invocation_method: dict) -> RequestPayload:
        request_payload: RequestPayload = RequestPayload(
            consts.DEFAULT_HTTP_METHOD,
            invocation_method.get("url", ""),
            body,
            {},
            {},
        )

        mapping: Mapping | None = next(
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

        if not mapping:
            return request_payload

        raw_mapping: dict = mapping.dict(exclude_none=True)
        raw_mapping.pop("enabled")
        for key, value in raw_mapping.items():
            result = self._apply_jq_on_field(value, body)
            setattr(request_payload, key, result)

        return request_payload

    def invoke(self, body: dict, invocation_method: dict) -> None:
        logger.info("WebhookInvoker - start - destination: %s", invocation_method)
        request_payload = self._prepare_payload(body, invocation_method)
        logger.info(
            "WebhookInvoker - request - " "method: %s, url: %s",
            request_payload.method,
            request_payload.url,
        )
        res = requests.request(
            request_payload.method,
            request_payload.url,
            json=request_payload.body,
            headers=request_payload.headers,
            params=request_payload.query,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )
        logger.info(
            "WebhookInvoker - done - destination: %s, status code: %s",
            invocation_method,
            res.status_code,
        )
        res.raise_for_status()


webhook_invoker = WebhookInvoker()
