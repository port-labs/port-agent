import json
import logging
from typing import Literal, Union

import requests
from typing import Dict
from core.config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def get_port_api_headers() -> Dict[str, str]:
    """
    Get a Port API access token
    This function uses CLIENT_ID and CLIENT_SECRET from config
    """

    credentials = {
        "clientId": settings.PORT_CLIENT_ID,
        "clientSecret": settings.PORT_CLIENT_SECRET,
    }

    token_response = requests.post(
        f"{settings.PORT_API_URL}/auth/access_token", json=credentials
    )

    return {"Authorization": f"Bearer {token_response.json()['accessToken']}",
            "User-Agent": "port-agent"}


def update_action_status(
    run_id: str, summary: str, status: Union[Literal["FAILURE"], Literal["SUCCESS"]]
) -> None:
    """
    Reports to Port on the status of an action run
    """

    headers = get_port_api_headers()
    body = {"summary": summary, "status": status}

    logger.info(f"update action with: {json.dumps(body)}")
    response = requests.patch(
        f"{settings.PORT_API_URL}/actions/runs/{run_id}", json=body, headers=headers
    )
    logger.info(
        f"update action response - status: {response.status_code}, "
        f"body: {json.dumps(response.json())}"
    )


def update_run_response(run_id: str, response: Union[str, dict]) -> None:
    headers = get_port_api_headers()
    body = {"response": response}

    logger.info(f"update run response with: {response}")
    patch_response = requests.patch(
        f"{settings.PORT_API_URL}/actions/runs/{run_id}/response",
        json=body,
        headers=headers,
    )
    logger.info(
        f"update action response - status: {patch_response.status_code}, "
        f"body: {json.dumps(patch_response.json())}"
    )


def send_run_log(run_id: str, message: str) -> None:
    headers = get_port_api_headers()

    body = {"message": message}

    # Create run log
    res = requests.post(
        f"{settings.PORT_API_URL}/actions/runs/{run_id}/logs",
        json=body,
        headers=headers,
    )

    logger.info(
        f"Send action run logs - status: {res.status_code}, "
        f"body: {json.dumps(res.json())}"
    )
