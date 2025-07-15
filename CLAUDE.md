# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Port Agent is a Python-based microservice that consumes messages from Apache Kafka and executes webhooks based on configured transformations. It serves as a bridge between Port's event system and external services like GitLab, GitHub, and generic webhooks.

## Architecture

The application follows an event-driven architecture with clear separation of concerns:

1. **Streaming Layer** (`app/streamer.py`): Orchestrates the message flow
2. **Kafka Consumer** (`app/consumers/kafka_consumer.py`): Consumes messages from Kafka topics
3. **Processing Layer** (`app/processors/`): Transforms Kafka messages into webhook payloads
4. **Invocation Layer** (`app/invokers/`): Executes webhooks with transformed payloads
5. **Port Client** (`app/clients/port_client.py`): Reports results back to Port

Key design patterns:
- Processor classes inherit from `BaseProcessor` for consistent message handling
- Invoker classes inherit from `BaseInvoker` for consistent webhook execution
- Configuration is managed through Pydantic models in `app/core/`
- HMAC signature verification for all incoming messages

## Development Commands

Run these commands from the project root:

```bash
# Run tests with coverage
./scripts/test.sh

# Format code (black, isort, autoflake)
./scripts/format.sh

# Lint code (mypy, black check, isort check, flake8)
./scripts/lint.sh

# Install dependencies
poetry install

# Run the application locally
poetry run python -m app.main

# Build Docker image
docker build -t port-agent .
```

## Configuration

The application uses environment variables for configuration. Key variables:

- `PORT_ORG_ID`: Your Port organization ID
- `PORT_CLIENT_ID`: Port OAuth client ID  
- `PORT_CLIENT_SECRET`: Port OAuth client secret
- `PORT_API_URL`: Port API URL (default: https://api.getport.io)
- `KAFKA_CONSUMER_GROUP_ID`: Kafka consumer group
- `KAFKA_CONSUMER_SECURITY_PROTOCOL`: Kafka security protocol (SASL_SSL, etc.)
- `KAFKA_CONSUMER_BOOTSTRAP_SERVERS`: Kafka broker addresses
- `STREAMER_NAME`: Unique name for this agent instance
- `KAFKA_CONSUMER_POLL_TIMEOUT`: Kafka poll timeout in seconds
- `AGENT_ENVIRONMENTS`: Comma-separated list of environments this agent should process (e.g., "production,staging")

For local development against a local Port instance:
- Set `USING_LOCAL_PORT_INSTANCE=true`
- This uses `ACCESS_TOKEN` for authentication instead of OAuth

### Environment-Specific Deployment

To deploy multiple agents for different environments using the same Port organization:

1. Set unique `KAFKA_CONSUMER_GROUP_ID` for each environment (e.g., "org_id-prod", "org_id-staging")
2. Set `AGENT_ENVIRONMENTS` to specify which environments each agent handles:
   - Production agent: `AGENT_ENVIRONMENTS=production`
   - Staging agent: `AGENT_ENVIRONMENTS=staging`
   - Dev agent: `AGENT_ENVIRONMENTS=dev,test,sandbox`

3. In Port, include the environment field in your self-service action invocation methods:
   ```json
   {
     "invocationMethod": {
       "type": "WEBHOOK",
       "agent": true,
       "environment": "production",
       "url": "https://your-webhook-url"
     }
   }
   ```

Messages without an environment field will be skipped by agents with `AGENT_ENVIRONMENTS` configured.

## Testing

Tests are organized to mirror the application structure:
- Unit tests are in `tests/` with the same structure as `app/`
- Fixtures are defined in `conftest.py` files
- Heavy use of mocking for external dependencies (Kafka, HTTP requests)
- Run a specific test: `poetry run pytest tests/path/to/test.py::test_name`

## Message Processing Flow

1. Kafka message consumed with format:
   ```json
   {
     "action": {...},
     "payload": {...},
     "trigger": {...}
   }
   ```

2. HMAC signature verified using organization ID as key

3. Message transformed based on invocation method:
   - GitLab: Uses control_the_payload_config.json rules
   - Generic webhook: Direct payload forwarding
   - Request headers and body customizable via JQ transformations

4. Webhook executed with:
   - Configurable HTTP method
   - Custom headers (including Port-Agent-Signature)
   - Transformed body
   - SSL verification options

5. Results reported back to Port via runs API

## Common Development Tasks

When adding a new invocation method:
1. Create a new processor in `app/processors/`
2. Create a new invoker in `app/invokers/`
3. Update `control_the_payload_config.json` with transformation rules
4. Add corresponding tests
5. Update the processor/invoker mappings in the streamer

When modifying message transformations:
- Edit JQ queries in `control_the_payload_config.json`
- Test transformations using the jq_service module
- Ensure backward compatibility with existing payloads

## Security Considerations

- All messages must pass HMAC verification
- Support for encrypted fields with AES decryption
- Webhook signatures included in Port-Agent-Signature header
- SSL verification configurable per webhook
- Secrets handled via environment variables only