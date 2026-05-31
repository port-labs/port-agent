import os
from importlib.metadata import PackageNotFoundError, version

PORT_AGENT_PACKAGE_NAME = "port-agent"
PORT_AGENT_VERSION_ENV = "PORT_AGENT_VERSION"


def get_version() -> str:
    env_version = os.getenv(PORT_AGENT_VERSION_ENV)
    if env_version:
        return env_version

    try:
        return version(PORT_AGENT_PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"
