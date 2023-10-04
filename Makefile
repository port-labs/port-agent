##@ Formatting

.PHONY: format-autoflake
format-autoflake: ## autoflake (remove unused imports)
	@poetry run autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place app tests --exclude=__init__.py

.PHONY: format-black
format-black: ## black (code formatter)
	@poetry run black app tests

.PHONY: format-isort
format-isort: ## isort (import formatter)
	@poetry run isort --profile black app tests

##@ Linting

.PHONY: lint-mypy
lint-mypy: ## mypy (type checker)
	@poetry run mypy app tests

.PHONY: lint-black
lint-black: ## mypy (type checker)
	@poetry run black app tests --check

.PHONY: lint-isort
lint-isort: ## isort (import formatter)
	@poetry run isort --profile black app tests

.PHONY: lint-flake8
lint-flake8:	## flake8 (linter)
	@poetry run flake8

##@ Testing
# Define variables for environment settings
export PYTHONPATH=app
export STREAMER_NAME=test
export PORT_ORG_ID=test_org

.PHONY: test-pytest
test-pytest:
	@poetry run pytest --cov=app --cov-report=term-missing tests


format: format-autoflake format-black format-isort## run all formatters
lint:  lint-mypy lint-black lint-isort lint-flake8 ## run all linters
test: test-pytest ## run all tests

