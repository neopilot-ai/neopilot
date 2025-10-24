# pylint: disable=direct-environment-variable-reference

from __future__ import annotations

import os

import googlecloudprofiler
from neoai_workflow_service.tracking.errors import log_exception


def setup_profiling():
    if os.environ.get("NEOAI_WORKFLOW_GOOGLE_CLOUD_PROFILER__ENABLED") != "true":
        return

    try:
        googlecloudprofiler.start(
            service="neoai-workflow-service",
            service_version=os.environ.get("K_REVISION", "1.0.0"),
        )
    except (ValueError, NotImplementedError) as e:
        log_exception(e)
