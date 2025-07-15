# GitHub Actions Setup for Docker Hub

This document explains how to set up the GitHub Actions workflows for building and publishing Docker images to Docker Hub.

## Required Secrets

You need to configure the following secrets in your GitHub repository settings:

1. **`DOCKER_HUB_TOKEN`** - Your Docker Hub access token
   - Go to [Docker Hub Security Settings](https://hub.docker.com/settings/security)
   - Create a new access token with "Read, Write, Delete" permissions
   - Copy the token and add it as a repository secret

2. **`PORT_CLIENT_ID`** and **`PORT_CLIENT_SECRET`** (Optional)
   - Only needed if you want to keep the Port integration in the python-app.yml workflow
   - Otherwise, you can remove the Port-related steps from that workflow

## Workflows Overview

### 1. Docker Hub Publish (`docker-hub-publish.yml`)

This is the main workflow for building and pushing Docker images to Docker Hub.

**Triggers:**
- Push to `main` branch
- Push of version tags (`v*.*.*`)
- Pull requests (build only, no push)
- Manual trigger (workflow_dispatch)

**Versioning Strategy:**
- **Tags**: When you push a tag like `v1.2.3`, it creates:
  - `christensen143/port-agent-jack:1.2.3`
  - `christensen143/port-agent-jack:latest`
- **Main branch**: Creates:
  - `christensen143/port-agent-jack:latest`
  - `christensen143/port-agent-jack:<short-sha>`
- **Pull requests**: Creates (not pushed):
  - `christensen143/port-agent-jack:pr-<number>`

**Features:**
- Multi-platform builds (linux/amd64, linux/arm64)
- Build caching for faster builds
- Automatic README sync to Docker Hub
- GitHub release creation for version tags

### 2. Version Bump (`version-bump.yml`)

Helper workflow to manage versioning.

**Usage:**
1. Go to Actions tab
2. Select "Version Bump" workflow
3. Click "Run workflow"
4. Choose version bump type:
   - `patch`: 1.2.3 → 1.2.4
   - `minor`: 1.2.3 → 1.3.0
   - `major`: 1.2.3 → 2.0.0

**What it does:**
- Updates version in `pyproject.toml`
- Creates and pushes a git tag
- Creates a PR with the changes

### 3. Python Application (`python-app.yml`)

Runs tests and code quality checks.

**Note**: This workflow has Port integration that you may want to remove or update with your own Port credentials.

## Quick Start

1. **Add Docker Hub Token Secret**:
   ```
   Repository Settings → Secrets and variables → Actions → New repository secret
   Name: DOCKER_HUB_TOKEN
   Value: <your-docker-hub-token>
   ```

2. **Update Docker Hub Username** (if different from christensen143):
   - Edit `.github/workflows/docker-hub-publish.yml`
   - Change `DOCKER_HUB_USERNAME: christensen143` to your username
   - Change `IMAGE_NAME: port-agent-jack` if desired

3. **Create Your First Release**:
   ```bash
   # Manual tagging
   git tag -a v0.1.0 -m "Initial release with environment filtering"
   git push origin v0.1.0
   
   # Or use the Version Bump workflow
   ```

4. **Verify Docker Image**:
   ```bash
   docker pull christensen143/port-agent-jack:latest
   docker pull christensen143/port-agent-jack:0.1.0
   ```

## Customization Options

### Change Image Name
Edit `DOCKER_HUB_USERNAME` and `IMAGE_NAME` in `docker-hub-publish.yml`

### Disable Multi-platform Builds
Remove `linux/arm64` from the `platforms` configuration if you only need amd64

### Add Additional Tags
Modify the tagging logic in the "Extract metadata" step

### Disable Automatic README Sync
Remove or comment out the "Update Docker Hub Description" step

## Troubleshooting

1. **Authentication Failed**: Ensure your Docker Hub token has the correct permissions
2. **Build Failed**: Check the workflow logs for specific errors
3. **Tag Not Created**: Ensure you're using the correct tag format (`v*.*.*`)
4. **Multi-platform Build Issues**: Try building for a single platform first

## Best Practices

1. Always test changes in a pull request before merging
2. Use semantic versioning for releases
3. Update the README.md with any user-facing changes
4. Keep Docker images small by using multi-stage builds
5. Regularly update base images for security patches