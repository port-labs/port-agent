import json
import os
from signal import SIGINT
from typing import Any, Callable, Generator, Optional

import pytest
import requests
from _pytest.monkeypatch import MonkeyPatch
from confluent_kafka import Consumer as _Consumer


@pytest.fixture
def mock_requests(monkeypatch: MonkeyPatch, request: Any) -> None:
    class MockResponse:
        status_code = request.param.get("status_code")
        text = "Invoker failed with status code: %d" % status_code

        def raise_for_status(self) -> None:
            if 400 <= self.status_code <= 599:
                raise Exception(self.text)

    def mock_request(*args: Any, **kwargs: Any) -> MockResponse:
        return MockResponse()

    monkeypatch.setattr(requests, "request", mock_request)


def terminate_consumer() -> None:
    os.kill(os.getpid(), SIGINT)


class Consumer(_Consumer):
    def __init__(self) -> None:
        pass

    def subscribe(
        self, topics: Any, on_assign: Any = None, *args: Any, **kwargs: Any
    ) -> None:
        pass

    def poll(self, timeout: Any = None) -> None:
        pass

    def commit(self, message: Any = None, *args: Any, **kwargs: Any) -> None:
        pass

    def close(self, *args: Any, **kwargs: Any) -> None:
        pass


@pytest.fixture
def mock_kafka(monkeypatch: MonkeyPatch, request: Any) -> None:
    class MockKafkaMessage:
        def error(self) -> None:
            return None

        def topic(self, *args: Any, **kwargs: Any) -> str:
            return request.param[2]

        def partition(self, *args: Any, **kwargs: Any) -> int:
            return 0

        def offset(self, *args: Any, **kwargs: Any) -> int:
            return 0

        def value(self) -> bytes:
            return request.getfixturevalue(request.param[0])(request.param[1])

    def mock_subscribe(
        self: Any, topics: Any, on_assign: Any = None, *args: Any, **kwargs: Any
    ) -> None:
        pass

    def generate_kafka_messages() -> Generator[Optional[MockKafkaMessage], None, None]:
        yield MockKafkaMessage()
        while True:
            yield None

    kafka_messages_generator = generate_kafka_messages()

    def mock_poll(self: Any, timeout: Any = None) -> Optional[MockKafkaMessage]:
        return next(kafka_messages_generator)

    def mock_commit(self: Any, message: Any = None, *args: Any, **kwargs: Any) -> None:
        return None

    def mock_close(self: Any, *args: Any, **kwargs: Any) -> None:
        pass

    monkeypatch.setattr(Consumer, "subscribe", mock_subscribe)
    monkeypatch.setattr(Consumer, "poll", mock_poll)
    monkeypatch.setattr(Consumer, "commit", mock_commit)
    monkeypatch.setattr(Consumer, "close", mock_close)


@pytest.fixture(scope="module")
def mock_webhook_change_log_message() -> Callable[[dict], bytes]:
    change_log_message = {
        "action": "Create",
        "resourceType": "run",
        "status": "TRIGGERED",
        "trigger": {
            "by": {"orgId": "test_org", "userId": "test_user"},
            "origin": "UI",
            "at": "2022-11-16T16:31:32.447Z",
        },
        "context": {
            "entity": None,
            "blueprint": "Service",
            "runId": "r_jE5FhDURh4Uen2Qr",
        },
        "diff": {
            "before": None,
            "after": {
                "id": "r_jE5FhDURh4Uen2Qr",
                "status": "IN_PROGRESS",
                "blueprint": {"identifier": "Service", "title": "Service"},
                "action": "Create",
                "endedAt": None,
                "source": "UI",
                "relatedEntityExists": False,
                "relatedBlueprintExists": True,
                "properties": {},
                "createdAt": "2022-11-16T16:31:32.447Z",
                "updatedAt": "2022-11-16T16:31:32.447Z",
                "createdBy": "test_user",
                "updatedBy": "test_user",
            },
        },
        "changelogDestination": {
            "type": "WEBHOOK",
            "agent": True,
            "url": "http://localhost:80/api/test",
        },
    }

    def get_change_log_message(invocation_method: dict) -> bytes:
        if invocation_method is not None:
            change_log_message["changelogDestination"] = invocation_method
        return json.dumps(change_log_message).encode()

    return get_change_log_message


@pytest.fixture(scope="module")
def mock_webhook_run_message() -> Callable[[dict], bytes]:
    run_message: dict = {
        "action": "Create",
        "resourceType": "run",
        "status": "TRIGGERED",
        "trigger": {
            "by": {"orgId": "test_org", "userId": "test_user"},
            "origin": "UI",
            "at": "2022-11-16T16:31:32.447Z",
        },
        "context": {
            "entity": None,
            "blueprint": "Service",
            "runId": "r_jE5FhDURh4Uen2Qr",
        },
        "payload": {
            "entity": None,
            "action": {
                "id": "action_34aweFQtayw7SCVb",
                "identifier": "Create",
                "title": "Create",
                "icon": "DefaultBlueprint",
                "userInputs": {
                    "properties": {
                        "foo": {"type": "string", "description": "Description"},
                        "bar": {"type": "number", "description": "Description"},
                    },
                    "required": [],
                },
                "invocationMethod": {
                    "type": "WEBHOOK",
                    "agent": True,
                    "url": "http://localhost:80/api/test",
                },
                "trigger": "CREATE",
                "description": "",
                "blueprint": "Service",
                "createdAt": "2022-11-15T09:58:52.863Z",
                "createdBy": "test_user",
                "updatedAt": "2022-11-15T09:58:52.863Z",
                "updatedBy": "test_user",
            },
            "properties": {},
        },
    }

    def get_run_message(invocation_method: dict) -> bytes:
        if invocation_method is not None:
            run_message["payload"]["action"]["invocationMethod"] = invocation_method
        return json.dumps(run_message).encode()

    return get_run_message


@pytest.fixture(scope="module")
def mock_gitlab_run_message() -> Callable[[dict], bytes]:
    run_message: dict = {
        "action": "Create",
        "resourceType": "run",
        "status": "TRIGGERED",
        "trigger": {
            "by": {"orgId": "test_org", "userId": "test_user"},
            "origin": "UI",
            "at": "2022-11-16T16:31:32.447Z",
        },
        "context": {
            "entity": None,
            "blueprint": "Service",
            "runId": "r_jE5FhDURh4Uen2Qr",
        },
        "payload": {
            "entity": None,
            "action": {
                "id": "action_34aweFQtayw7SCVb",
                "identifier": "Create",
                "title": "Create",
                "icon": "DefaultBlueprint",
                "userInputs": {
                    "properties": {
                        "foo": {"type": "string", "description": "Description"},
                        "bar": {"type": "number", "description": "Description"},
                    },
                    "required": [],
                },
                "invocationMethod": {
                    "type": "GITLAB",
                    "agent": True,
                    "defaultRef": "main",
                    "projectName": "project",
                    "groupName": "group",
                },
                "trigger": "CREATE",
                "description": "",
                "blueprint": "Service",
                "createdAt": "2022-11-15T09:58:52.863Z",
                "createdBy": "test_user",
                "updatedAt": "2022-11-15T09:58:52.863Z",
                "updatedBy": "test_user",
            },
            "properties": {},
        },
    }

    def get_gitlab_run_message(invocation_method: dict) -> bytes:
        if invocation_method is not None:
            run_message["payload"]["action"]["invocationMethod"] = invocation_method
        return json.dumps(run_message).encode()

    return get_gitlab_run_message


@pytest.fixture
def mock_gitlab_token(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("group_project", "token")
