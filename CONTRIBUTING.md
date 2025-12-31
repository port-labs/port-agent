# Contributing to Port Execution Agent

Thank you for your interest in contributing to the Port Execution Agent! We welcome contributions and feedback from the community. To help you get started, please follow these guidelines.

## How to Contribute

### Reporting Issues

If you encounter any bugs or issues with the execution agent, please report an issue via our [Slack Community](https://port-community.slack.com/archives/C07CB3MV63G). When reporting an issue, be sure to include:
- A description of the problem, including any error messages.
- Steps to reproduce the issue.
- Any relevant logs or screenshots.

### Suggesting Enhancements

If you have suggestions for new features or improvements, please open a feature request [here](https://roadmap.getport.io/ideas), or reach to us via our [Slack Community](https://port-community.slack.com/archives/C07CB3MV63G).

Provide details on:
- The enhancement or feature you are proposing.
- How it would benefit users.
- Any additional context or use cases.

### Submitting Code

To submit code contributions:
1. Fork the repository on GitHub.
2. Create a new branch for your changes.
3. Make your changes and test them thoroughly.
4. Ensure your code adheres to our coding style and guidelines.
5. Open a pull request against the `main` branch of the original repository. Include a clear description of your changes and any relevant context.

## Coding Guidelines

- Write clear and concise commit messages.
- Ensure your changes do not break existing functionality.
- Add or update tests as necessary.

## Debugging

### Set Environment Variables

Create or update your `.env` file to include the following environment variables (replace with your actual values):

```env
STREAMER_NAME=KAFKA
KAFKA_CONSUMER_GROUP_ID=my_consumer_group

PORT_ORG_ID=your_organization_id_here
PORT_CLIENT_ID=your_client_id_here
PORT_CLIENT_SECRET=your_client_secret_here
PORT_API_BASE_URL=your_api_base_url_here
 ```

### Run with Python

**Prequisites:**

- Python 3.11
- [Poetry](https://python-poetry.org/docs/#installing-manually)

**Install Dependencies:**

It is recommended to install the dependencies inside a virtual environment:

```bash
VENV_PATH=".venv"
python3.11 -m venv $VENV_PATH
$VENV_PATH/bin/pip install -U pip setuptools
$VENV_PATH/bin/pip install poetry
source $VENV_PATH/bin/activate

poetry install
```

**Run the Agent:**

Activate the virtual environment if not already activated:

```bash
source .venv/bin/activate
```

The execution must be from the `app` directory:

```bash
cd app
```

To start the Port Execution Agent, run the following command from the `app` directory:

```bash
python main.py
```

### Run with Docker

Before running the container, ensure you have built the Docker image:

```bash
docker build -t port-execution-agent .
```

Run the Port Execution Agent container with the following command:

```bash
docker run \
  --name port-execution-agent \
  --env-file .env \
  --network host \
  port-execution-agent
```

### General Troubleshooting (Optional)

For debugging the Port Execution Agent in other environments, consider the following tips:

1. **Check Authentication and Configuration:**
   - Ensure that all necessary authentication details are correctly configured for Kafka and any other external services.

2. **Review Logs:**
   - Examine the logs for any error messages or issues that might provide insights into problems.

3. **Verify Endpoints and Connectivity:**
   - Ensure that all endpoints are correctly specified and accessible.

4. **Update Dependencies:**
   - Check that all dependencies are up-to-date and compatible with your environment.

5. **Consult Documentation:**
   - Refer to our [Documentation](https://docs.getport.io/actions-and-automations/setup-backend/webhook/port-execution-agent).

## Contact

For any questions or additional support, please contact us via Intercom or check our [Slack Community](https://port-community.slack.com/archives/C07CB3MV63G).

Thank you for contributing to the Port Execution Agent!

