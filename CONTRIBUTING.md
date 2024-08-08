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

### Running Against Local Port Instance

When debugging the Port Execution Agent locally against a local instance of Port, follow these steps:

1. **Set Up Local Environment:**
   - Ensure you have a local instance of Port running. This will act as your development and testing environment.

2. **Configure Environment Variables:**
   - Create or update your `.env` file to include the following environment variable:
     ```env
     USING_LOCAL_PORT_INSTANCE=True
     ```

3. **Kafka Authentication:**
   - When `USING_LOCAL_PORT_INSTANCE` is set to `True`, the execution agent will not attempt to pull your local organization's kafka credentials.

4. **Running the Agent Locally:**
   - Start the execution agent as you normally would.

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

