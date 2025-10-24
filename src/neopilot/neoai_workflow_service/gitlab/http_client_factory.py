import os

from neoai_workflow_service.executor.outbox import Outbox
from neoai_workflow_service.gitlab.direct_http_client import DirectGitLabHttpClient
from neoai_workflow_service.gitlab.executor_http_client import ExecutorGitLabHttpClient
from neoai_workflow_service.gitlab.http_client import GitlabHttpClient


def get_http_client(
    outbox: Outbox,
    base_url: str,
    gitlab_token: str,
) -> GitlabHttpClient:
    if base_url == os.getenv("NEOAI_WORKFLOW_DIRECT_CONNECTION_BASE_URL"):
        return DirectGitLabHttpClient(base_url, gitlab_token)
    else:
        return ExecutorGitLabHttpClient(outbox)
