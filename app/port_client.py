from logging import getLogger
from typing import Callable

import requests
from core.config import settings
from core.consts import consts
from requests import Response

logger = getLogger(__name__)


def get_port_api_headers() -> dict[str, str]:
    credentials = {
        "clientId": settings.PORT_CLIENT_ID,
        "clientSecret": settings.PORT_CLIENT_SECRET,
    }

    token_response = requests.post(
        f"{settings.PORT_API_BASE_URL}/v1/auth/access_token", json=credentials
    )

    if not token_response.ok:
        logger.error(
            f"Failed to get Port API access token - "
            f"status: {token_response.status_code}, "
            f"response: {token_response.text}"
        )

    token_response.raise_for_status()

    return {
        "Authorization": f"Bearer {token_response.json()['accessToken']}",
        "User-Agent": "port-agent",
    }


def run_logger_factory(run_id: str) -> Callable[[str], None]:
    def send_run_log(message: str) -> None:
        headers = get_port_api_headers()

        requests.post(
            f"{settings.PORT_API_BASE_URL}/v1/actions/runs/{run_id}/logs",
            json={"message": message},
            headers=headers,
        )

    return send_run_log


def report_run_status(run_id: str, data_to_patch: dict) -> Response:
    headers = get_port_api_headers()
    res = requests.patch(
        f"{settings.PORT_API_BASE_URL}/v1/actions/runs/{run_id}",
        json=data_to_patch,
        headers=headers,
    )
    return res


def report_run_response(run_id: str, response: dict | str | None) -> Response:
    headers = get_port_api_headers()
    res = requests.patch(
        f"{settings.PORT_API_BASE_URL}/v1/actions/runs/{run_id}/response",
        json={"response": response},
        headers=headers,
    )
    return res


def get_kafka_credentials() -> tuple[list[str], str, str]:
    headers = get_port_api_headers()
    res = requests.get(
        f"{settings.PORT_API_BASE_URL}/v1/kafka-credentials", headers=headers
    )
    res.raise_for_status()
    data = res.json()["credentials"]
    return data["brokers"], data["username"], data["password"]


def claim_pending_runs(limit: int) -> list[dict]:
    headers = get_port_api_headers()
    headers["x-port-reserved-usage"] = "true"

    body = {
        "installationId": settings.PORT_ORG_ID,
        "limit": limit,
        "invocationMethod": "WEBHOOK",
    }

    res = requests.post(
        f"{settings.PORT_API_BASE_URL}/v1/actions/runs/claim-pending",
        json=body,
        headers=headers,
    )
    res.raise_for_status()
    return res.json().get("runs", [])


def ack_runs(run_ids: list[str]) -> int:
    if not run_ids:
        return 0

    headers = get_port_api_headers()
    headers["x-port-reserved-usage"] = "true"

    body = {"runIds": run_ids}

    res = requests.patch(
        f"{settings.PORT_API_BASE_URL}/v1/actions/runs/ack",
        json=body,
        headers=headers,
    )
    res.raise_for_status()
    return res.json().get("ackedCount", 0)


def patch_org_streamer_setting(streamer_type: str) -> None:
    if streamer_type not in consts.VALID_STREAMER_TYPES:
        logger.warning(
            "Unknown streamer type %s, skipping org setting update", streamer_type
        )
        return

    headers = get_port_api_headers()

    res = requests.patch(
        f"{settings.PORT_API_BASE_URL}/v1/organization",
        json={"settings": {"portAgentStreamerName": streamer_type}},
        headers=headers,
    )

    if not res.ok:
        logger.error(
            "Failed to update org streamer setting - "
            f"status: {res.status_code}, "
            f"response: {res.text}"
        )
        res.raise_for_status()

    logger.info("Successfully updated org streamer setting to %s", streamer_type)
