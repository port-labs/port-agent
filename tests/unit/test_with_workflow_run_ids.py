from typing import Any, Dict, Iterator, Optional
from unittest import mock

import pytest

from app.utils import with_workflow_run_ids

PORT_API = "https://api.getport.io"
RUN_IDS = "run_id=wfr_9&node_run_identifier=wfnr_1"


@pytest.fixture(autouse=True)
def port_api_base_url() -> Iterator[None]:
    with mock.patch("app.utils.settings") as settings:
        settings.PORT_API_BASE_URL = PORT_API
        yield


def _tie(
    url: Any,
    method: str = "POST",
    query: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
) -> Any:
    return with_workflow_run_ids(
        url, method, query or {}, headers or {}, "wfr_9", "wfnr_1"
    )


@pytest.mark.parametrize(
    "method, path",
    [
        ("POST", "/v1/blueprints/service/entities"),
        ("POST", "/v1/blueprints/service/entities/bulk"),
        ("PUT", "/v1/blueprints/service/entities/payments"),
        ("PATCH", "/v1/blueprints/service/entities/payments"),
        ("DELETE", "/v1/blueprints/service/entities/payments"),
        ("DELETE", "/v1/blueprints/service/bulk/entities"),
        ("POST", "/v1/blueprints/service/bulk/entities/delete"),
    ],
)
def test_adds_the_ids_to_entity_writes(method: str, path: str) -> None:
    assert _tie(f"{PORT_API}{path}", method) == f"{PORT_API}{path}?{RUN_IDS}"


@pytest.mark.parametrize(
    "method, path",
    [
        ("POST", "/v1/blueprints/service/entities/search"),
        ("POST", "/v1/blueprints/service/entities/search/count"),
        ("POST", "/v1/blueprints/service/entities/group"),
        ("GET", "/v1/blueprints/service/entities/payments"),
        ("DELETE", "/v1/blueprints/service/all-entities"),
    ],
)
def test_leaves_other_routes_alone(method: str, path: str) -> None:
    url = f"{PORT_API}{path}"
    assert _tie(url, method) == url


def test_leaves_other_hosts_alone() -> None:
    url = "https://example.com/v1/blueprints/service/entities"
    assert _tie(url) == url


def test_keeps_the_query_params_already_in_the_url() -> None:
    url = f"{PORT_API}/v1/blueprints/service/entities?upsert=true"
    assert _tie(url) == f"{url}&{RUN_IDS}"


@pytest.mark.parametrize("existing", ["run_id=wfr_user", "node_run_identifier=wfnr_user"])
def test_keeps_ids_the_user_put_in_the_url(existing: str) -> None:
    url = f"{PORT_API}/v1/blueprints/service/entities?{existing}"
    assert _tie(url) == url


def test_keeps_ids_the_user_put_in_the_query_mapping() -> None:
    url = f"{PORT_API}/v1/blueprints/service/entities"
    assert _tie(url, query={"run_id": "wfr_user"}) == url


@pytest.mark.parametrize("header", ["Authorization", "authorization"])
def test_leaves_a_write_made_as_a_user_untied(header: str) -> None:
    url = f"{PORT_API}/v1/blueprints/service/entities"
    assert _tie(url, headers={header: "Bearer user-token"}) == url


def test_returns_a_url_that_is_not_a_string_as_is() -> None:
    assert _tie(None) is None
