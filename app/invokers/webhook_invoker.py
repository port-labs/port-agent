import logging
from typing import Any

import pyjq as jq
import requests
from core.config import Mapping, control_the_payload_config, settings
from core.consts import consts
from flatten_dict import flatten, unflatten
from invokers.base_invoker import BaseInvoker
from port_client import report_run_status
from pydantic import BaseModel, Field
from requests import Response
from utils import get_invocation_method_object, response_to_dict

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class RequestPayload(BaseModel):
    method: str
    url: str
    body: dict
    headers: dict
    query: dict


class ReportPayload(BaseModel):
    status: Any | None = None
    link: Any | None = None
    summary: Any | None = None
    external_run_id: Any | None = Field(None, alias="externalRunId")


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
            flatten_dict = flatten(mapping)
            parsed_jq = {
                key: self._jq_exec(value, body) if type(value) == str else value
                for key, value in flatten_dict.items()
            }
            return unflatten(parsed_jq)
        else:
            return self._jq_exec(mapping, body)

    def _prepare_payload(
        self, mapping: Mapping | None, body: dict, invocation_method: dict
    ) -> RequestPayload:
        request_payload: RequestPayload = RequestPayload(
            method=invocation_method.get("method", consts.DEFAULT_HTTP_METHOD),
            url=invocation_method.get("url", ""),
            body=body,
            headers={},
            query={},
        )
        if not mapping:
            return request_payload

        raw_mapping: dict = mapping.dict(exclude_none=True)
        raw_mapping.pop("enabled")
        raw_mapping.pop("report", None)
        for key, value in raw_mapping.items():
            result = self._apply_jq_on_field(value, body)
            setattr(request_payload, key, result)

        return request_payload

    def _prepare_report(
        self,
        mapping: Mapping | None,
        response_context: Response,
        request_context: dict,
        body_context: dict,
    ) -> ReportPayload:
        default_status = (
            ("SUCCESS" if response_context.ok else "FAILURE")
            if get_invocation_method_object(body_context).get("synchronized")
            else None
        )
        report_payload: ReportPayload = ReportPayload(status=default_status)
        if not mapping or not mapping.report:
            return report_payload

        context = {
            "body": body_context,
            "request": request_context,
            "response": response_to_dict(response_context),
        }

        raw_mapping: dict = mapping.report.dict(exclude_none=True)
        for key, value in raw_mapping.items():
            result = self._apply_jq_on_field(value, context)
            setattr(report_payload, key, result)

        return report_payload

    def _find_mapping(self, body: dict) -> Mapping:
        return next(
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

    def request(self, request_payload: RequestPayload) -> Response:
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
        return res

    def invoke(self, body: dict, invocation_method: dict) -> None:
        logger.info("WebhookInvoker - start - destination: %s", invocation_method)
        mapping = self._find_mapping(body)

        request_payload = self._prepare_payload(mapping, body, invocation_method)
        res = self.request(request_payload)
        logger.info(
            "WebhookInvoker - request - destination: %s, status code: %s",
            invocation_method,
            res.status_code,
        )

        run_id = body["context"]["runId"]
        report_payload = self._prepare_report(
            mapping, res, request_payload.dict(), body
        )
        if report_dict := report_payload.dict(exclude_none=True, by_alias=True):
            report_run_status(run_id, report_dict)

        res.raise_for_status()


webhook_invoker = WebhookInvoker()
