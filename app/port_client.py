import json
from logging import getLogger

import requests
from core.config import settings
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
            f"Failed to get Port API access token - status: {token_response.status_code}, "
            f"response: {token_response.text}"
        )

    token_response.raise_for_status()

    return {
        "Authorization": f"Bearer {token_response.json()['accessToken']}",
        "User-Agent": "port-agent",
    }


def send_run_log(run_id: str, message: str) -> None:
    headers = get_port_api_headers()

    res = requests.post(
        f"{settings.PORT_API_BASE_URL}/actions/runs/{run_id}/logs",
        json={"message": message},
        headers=headers,
    )

    logger.info(
        f"Send action run logs - status: {res.status_code}, "
        f"body: {json.dumps(res.json())}"
    )


def report_run_status(run_id: str, data_to_patch: dict) -> Response:
    headers = get_port_api_headers()
    res = requests.patch(
        f"{settings.PORT_API_BASE_URL}/v1/actions/runs/{run_id}",
        json=data_to_patch,
        headers=headers,
    )
    return res
