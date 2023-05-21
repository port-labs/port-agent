import logging

import requests
from core.config import settings
from invokers.base_invoker import BaseInvoker

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


class GitLabPipelineInvoker(BaseInvoker):
    def invoke(self, payload: dict, url: str) -> None:
        logger.info("GitLabPipelineInvoker - start - destination: %s, payload: %s", url, payload)

        res = requests.post(
            url,
            data=payload,
            timeout=settings.GITLAB_PIPELINE_INVOKER_TIMEOUT,
        )

        logger.info(
            "GitLabPipelineInvoker - done - destination: %s, payload: %s,  status code: %s",
            url,
            payload,
            res.status_code,
        )
        res.raise_for_status()


gitlab_pipeline_invoker = GitLabPipelineInvoker()
