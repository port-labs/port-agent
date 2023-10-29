import logging
import urllib.parse

import requests
from core.config import settings
from invokers.base_invoker import BaseInvoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class GitLabPipelineInvoker(BaseInvoker):
    def invoke(self, body: dict, project_path: str) -> None:
        logger.info("GitLabPipelineInvoker - start - project: %s", project_path)

        res = requests.post(
            f"{settings.GITLAB_URL}/api/v4/projects/{urllib.parse.quote(project_path, safe='')}/trigger/pipeline",
            json=body,
            timeout=settings.GITLAB_PIPELINE_INVOKER_TIMEOUT,
        )

        logger.info(
            "GitLabPipelineInvoker - done - project: %s,  status code: %s",
            project_path,
            res.status_code,
        )

        if res.status_code >= 400:
            raise Exception(res.text)


gitlab_pipeline_invoker = GitLabPipelineInvoker()
