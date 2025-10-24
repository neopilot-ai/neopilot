# pylint: disable=direct-environment-variable-reference

import os

import structlog
from prometheus_client import start_http_server

from neoai_workflow_service.tracking.neoai_workflow_metrics import NeoaiWorkflowMetrics

log = structlog.stdlib.get_logger("monitoring")

neoai_workflow_metrics = NeoaiWorkflowMetrics()


def setup_monitoring():
    addr = os.environ.get("PROMETHEUS_METRICS__ADDR")
    port = os.environ.get("PROMETHEUS_METRICS__PORT")
    if port and addr:
        log.info("Metrics HTTP server running on http://%s:%s", addr, port)

        start_http_server(
            addr=addr,
            port=int(port),
        )
    else:
        log.debug("Metrics are disabled...")

    return neoai_workflow_metrics
