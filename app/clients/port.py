import logging
import json
import requests
from typing import Literal, Union
from core.config import settings

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def get_port_api_token():
    """
    Get a Port API access token
    This function uses CLIENT_ID and CLIENT_SECRET from config
    """

    credentials = {'clientId': settings.PORT_CLIENT_ID, 'clientSecret': settings.PORT_CLIENT_SECRET}

    token_response = requests.post(f"{settings.PORT_API_URL}/auth/access_token", json=credentials)

    return token_response.json()['accessToken']

def update_action(run_id: str, message: str, status: Union[Literal['FAILURE'], Literal['SUCCESS']]):
    """
    Reports to Port on the status of an action run
    """

    token = get_port_api_token()
    headers = {
        'Authorization': f"Bearer {token}"
    }
    body = {
        'message': {
            'message': message
        },
        'status': status
    }

    logger.info(f"update action with: {json.dumps(body)}")
    response = requests.patch(f"{settings.PORT_API_URL}/actions/runs/{run_id}", json=body, headers=headers)
    logger.info(f"update action response - status: {response.status_code}, body: {json.dumps(response.json())}")

    return response.status_code