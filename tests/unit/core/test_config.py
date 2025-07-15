import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_agent_environments_parsing_from_string():
    """Test that AGENT_ENVIRONMENTS can be parsed from a comma-separated string."""
    # Test with string input
    settings = Settings(
        STREAMER_NAME="KAFKA",
        PORT_ORG_ID="test_org",
        PORT_CLIENT_ID="test_id",
        PORT_CLIENT_SECRET="test_secret",
        AGENT_ENVIRONMENTS="production,staging,development"
    )
    assert settings.AGENT_ENVIRONMENTS == ["production", "staging", "development"]


def test_agent_environments_parsing_with_spaces():
    """Test that AGENT_ENVIRONMENTS handles spaces correctly."""
    settings = Settings(
        STREAMER_NAME="KAFKA",
        PORT_ORG_ID="test_org",
        PORT_CLIENT_ID="test_id",
        PORT_CLIENT_SECRET="test_secret",
        AGENT_ENVIRONMENTS="production, staging , development"
    )
    assert settings.AGENT_ENVIRONMENTS == ["production", "staging", "development"]


def test_agent_environments_parsing_from_list():
    """Test that AGENT_ENVIRONMENTS can be set as a list."""
    settings = Settings(
        STREAMER_NAME="KAFKA",
        PORT_ORG_ID="test_org",
        PORT_CLIENT_ID="test_id",
        PORT_CLIENT_SECRET="test_secret",
        AGENT_ENVIRONMENTS=["production", "staging"]
    )
    assert settings.AGENT_ENVIRONMENTS == ["production", "staging"]


def test_agent_environments_empty_string():
    """Test that empty string results in empty list."""
    settings = Settings(
        STREAMER_NAME="KAFKA",
        PORT_ORG_ID="test_org",
        PORT_CLIENT_ID="test_id",
        PORT_CLIENT_SECRET="test_secret",
        AGENT_ENVIRONMENTS=""
    )
    assert settings.AGENT_ENVIRONMENTS == []


def test_agent_environments_default():
    """Test that AGENT_ENVIRONMENTS defaults to empty list when not provided."""
    settings = Settings(
        STREAMER_NAME="KAFKA",
        PORT_ORG_ID="test_org",
        PORT_CLIENT_ID="test_id",
        PORT_CLIENT_SECRET="test_secret"
    )
    assert settings.AGENT_ENVIRONMENTS == []


def test_agent_environments_single_value():
    """Test parsing a single environment value."""
    settings = Settings(
        STREAMER_NAME="KAFKA",
        PORT_ORG_ID="test_org",
        PORT_CLIENT_ID="test_id",
        PORT_CLIENT_SECRET="test_secret",
        AGENT_ENVIRONMENTS="production"
    )
    assert settings.AGENT_ENVIRONMENTS == ["production"]