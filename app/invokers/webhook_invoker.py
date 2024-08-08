import json
import logging
import time
from typing import Any, Callable

import pyjq as jq
import requests
from core.config import Mapping, control_the_payload_config, settings
from core.consts import consts
from flatten_dict import flatten, unflatten
from invokers.base_invoker import BaseInvoker
from port_client import report_run_response, report_run_status, run_logger_factory
from pydantic import BaseModel, Field
from requests import Response
from utils import (
    get_invocation_method_object,
    get_response_body,
    response_to_dict,
    sign_sha_256,
)

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

    def _apply_jq_on_field(self, mapping: Any, body: dict) -> Any:
        if isinstance(mapping, dict):
            flatten_dict = flatten(mapping)
            parsed_jq = {
                key: self._apply_jq_on_field(value, body)
                for key, value in flatten_dict.items()
            }
            return unflatten(parsed_jq)
        elif isinstance(mapping, list):
            return [self._apply_jq_on_field(item, body) for item in mapping]
        elif isinstance(mapping, str):
            return self._jq_exec(mapping, body)
        return mapping

    def _prepare_payload(
        self, mapping: Mapping, body: dict, invocation_method: dict
    ) -> RequestPayload:
        request_payload: RequestPayload = RequestPayload(
            method=invocation_method.get("method", consts.DEFAULT_HTTP_METHOD),
            url=invocation_method.get("url", ""),
            body=body,
            headers={},
            query={},
        )

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
        # We don't want to update the run status if the request succeeded and the
        # invocation method is synchronized
        is_sync = get_invocation_method_object(body_context).get("synchronized")
        success_status = "SUCCESS" if is_sync else None
        default_status = success_status if response_context.ok else "FAILURE"

        failure_summary = (
            f"Failed to invoke the webhook with status code: "
            f"{response_context.status_code}. Response: {response_context.text}."
        )
        default_summary = None if response_context.ok else failure_summary
        report_payload: ReportPayload = ReportPayload(
            status=default_status, summary=default_summary
        )
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

    def _find_mapping(self, body: dict) -> Mapping | None:
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

    @staticmethod
    def _request(
        request_payload: RequestPayload, run_logger: Callable[[str], None]
    ) -> Response:
        logger.info(
            "WebhookInvoker - request - " "method: %s, url: %s, body: %s",
            request_payload.method,
            request_payload.url,
            request_payload.body,
        )
        run_logger("Sending the request")
        request_payload.headers["X-Port-Timestamp"] = str(int(time.time()))
        request_payload.headers["X-Port-Signature"] = sign_sha_256(
            json.dumps(request_payload.body, separators=(",", ":")),
            settings.PORT_CLIENT_SECRET,
            request_payload.headers["X-Port-Timestamp"],
        )

        res = requests.request(
            request_payload.method,
            request_payload.url,
            json=request_payload.body,
            headers=request_payload.headers,
            params=request_payload.query,
            timeout=settings.WEBHOOK_INVOKER_TIMEOUT,
        )

        if res.ok:
            logger.info(
                "WebhookInvoker - request - status_code: %s, body: %s",
                res.status_code,
                res.text,
            )
            run_logger(
                f"The request was successful with status code: {res.status_code}"
            )
        else:
            logger.warning(
                "WebhookInvoker - request - status_code: %s, response: %s",
                res.status_code,
                res.text,
            )
            run_logger(
                f"The request failed with status code: {res.status_code} "
                f"and response: {res.text}"
            )

        return res

    @staticmethod
    def _report_run_status(
        run_id: str, data_to_patch: dict, run_logger: Callable[[str], None]
    ) -> Response:
        res = report_run_status(run_id, data_to_patch)

        if res.ok:
            logger.info(
                "WebhookInvoker - report run - run_id: %s, status_code: %s",
                run_id,
                res.status_code,
            )
        else:
            logger.warning(
                "WebhookInvoker - report run - "
                "run_id: %s, status_code: %s, response: %s",
                run_id,
                res.status_code,
                res.text,
            )
            run_logger(
                f"The run state failed to be reported "
                f"with status code: {res.status_code} and response: {res.text}"
            )

        return res

    @staticmethod
    def _report_run_response(
        run_id: str, response_body: dict | str | None, run_logger: Callable[[str], None]
    ) -> Response:
        logger.info(
            "WebhookInvoker - report run response - run_id: %s, response: %s",
            run_id,
            response_body,
        )
        run_logger("Reporting the run response")

        res = report_run_response(run_id, response_body)

        if res.ok:
            logger.info(
                "WebhookInvoker - report run response - " "run_id: %s, status_code: %s",
                run_id,
                res.status_code,
            )
            run_logger("The run response was reported successfully ")
        else:
            logger.warning(
                "WebhookInvoker - report run response - "
                "run_id: %s, status_code: %s, response: %s",
                run_id,
                res.status_code,
                res.text,
            )
            run_logger(
                f"The run response failed to be reported "
                f"with status code: {res.status_code} and response: {res.text}"
            )

        return res

    def _invoke_run(
        self, run_id: str, mapping: Mapping, body: dict, invocation_method: dict
    ) -> None:
        run_logger = run_logger_factory(run_id)
        run_logger("An action message has been received")

        logger.info(
            "WebhookInvoker - mapping - mapping: %s",
            mapping.dict() if mapping else None,
        )
        run_logger("Preparing the payload for the request")
        request_payload = self._prepare_payload(mapping, body, invocation_method)
        res = self._request(request_payload, run_logger)

        response_body = get_response_body(res)
        if invocation_method.get("synchronized") and response_body:
            self._report_run_response(run_id, response_body, run_logger)

        report_payload = self._prepare_report(
            mapping, res, request_payload.dict(), body
        )
        if report_dict := report_payload.dict(exclude_none=True, by_alias=True):
            logger.info(
                "WebhookInvoker - report mapping - report_payload: %s",
                report_payload.dict(exclude_none=True, by_alias=True),
            )
            self._report_run_status(run_id, report_dict, run_logger)
        else:
            logger.info(
                "WebhookInvoker - report mapping "
                "- no report mapping found - run_id: %s",
                run_id,
            )
        res.raise_for_status()
        run_logger("Port agent finished processing the action run")

    def validate_incoming_signature(self,
                                    msg: dict,
                                    invocation_method_name: str) -> bool:
        if "changelogDestination" in msg:
            return True

        port_signature = msg.get("headers", {}).get("X-Port-Signature")
        port_timestamp = msg.get("headers", {}).get("X-Port-Timestamp")

        if not port_signature or not port_timestamp:
            logger.warning(
                "WebhookInvoker - Could not find the required headers, skipping the"
                " event invocation method for the event"
            )
            return False

        # Remove Port's generated headers to avoid them being
        # used in the signature verification
        if invocation_method_name == 'GITLAB':
            del msg["headers"]
        else:
            del msg["headers"]["X-Port-Signature"]
            del msg["headers"]["X-Port-Timestamp"]

        expected_sig = sign_sha_256(
            json.dumps(msg, separators=(",", ":"), ensure_ascii=False),
            settings.PORT_CLIENT_SECRET,
            port_timestamp,
        )
        if expected_sig != port_signature:
            logger.warning(
                "WebhookInvoker - Could not verify signature, skipping the event"
            )
            return False
        return True

    def invoke(self, msg: dict, invocation_method: dict) -> None:
        logger.info("WebhookInvoker - start - destination: %s", invocation_method)
        run_id = msg["context"].get("runId")

        invocation_method_name = invocation_method.get('type', 'WEBHOOK')
        if not self.validate_incoming_signature(msg, invocation_method_name):
            return

        logger.info("WebhookInvoker - validating signature")

        mapping = self._find_mapping(msg)
        if mapping is None:
            logger.info(
                "WebhookInvoker - Could not find suitable mapping for the event"
                f" - msg: {msg} {', run_id: ' + run_id if run_id else ''}",
            )
            return

        if run_id:
            self._invoke_run(run_id, mapping, msg, invocation_method)
        # Used for changelog destination event trigger
        elif invocation_method.get("url"):
            request_payload = self._prepare_payload(mapping, msg, invocation_method)
            res = self._request(request_payload, lambda _: None)
            res.raise_for_status()
        else:
            logger.warning(
                "WebhookInvoker - Could not find suitable "
                "invocation method for the event"
            )
        logger.info("Finished processing the event")


webhook_invoker = WebhookInvoker()
