import logging
import os

import gitlab
import requests
from core.config import settings
from invokers.base_invoker import BaseInvoker
import gitlab

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class GitLabPipelineInvoker(BaseInvoker):

    def invoke(self, body: dict, project_path: str):
        logger.info("GitLabPipelineInvoker - start - project: %s",
                    project_path)

        res = requests.post(
            f'{settings.GITLAB_URL}/api/v4/projects/{project_path}/trigger/pipeline',
            data=body,
            timeout=settings.GITLAB_PIPELINE_INVOKER_TIMEOUT
        )

        logger.info(
            "GitLabPipelineInvoker - done - project: %s,  status code: %s",
            project_path,
            res.status_code,
        )
        res.raise_for_status()

        return res.json()

    @staticmethod
    def get_running_pipeline(project_path: str, pipeline_id: str, access_token: str):
        return requests.get(f'{settings.GITLAB_URL}/api/v4/projects/{project_path}/pipelines/{pipeline_id}',
                            headers= {"Authorization": f"Bearer {access_token}"},
                            timeout=settings.GITLAB_PIPELINE_INVOKER_TIMEOUT).json()

gitlab_pipeline_invoker = GitLabPipelineInvoker()