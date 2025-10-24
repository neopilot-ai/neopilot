from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from lib.internal_events import InternalEventsClient

from neopilot.ai_gateway.abuse_detection import AbuseDetector
from neopilot.ai_gateway.api.feature_category import (X_GITLAB_UNIT_PRIMITIVE,
                                                      feature_categories)
from neopilot.ai_gateway.api.v1.proxy.request import (
    EXTENDED_FEATURE_CATEGORIES_FOR_PROXY_ENDPOINTS,
    authorize_with_unit_primitive_header)
from neopilot.ai_gateway.async_dependency_resolver import (
    get_abuse_detector, get_internal_event_client, get_openai_proxy_client)
from neopilot.ai_gateway.proxy.clients import OpenAIProxyClient

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("proxy")

router = APIRouter()


@router.post("/openai" + "/{path:path}")
@authorize_with_unit_primitive_header()
@feature_categories(EXTENDED_FEATURE_CATEGORIES_FOR_PROXY_ENDPOINTS)
async def openai(
    request: Request,
    background_tasks: BackgroundTasks,  # pylint: disable=unused-argument
    # pylint: disable=unused-argument
    abuse_detector: Annotated[AbuseDetector, Depends(get_abuse_detector)],
    openai_proxy_client: Annotated[OpenAIProxyClient, Depends(get_openai_proxy_client)],
    internal_event_client: Annotated[InternalEventsClient, Depends(get_internal_event_client)],
):
    unit_primitive = request.headers[X_GITLAB_UNIT_PRIMITIVE]
    internal_event_client.track_event(
        f"request_{unit_primitive}",
        category=__name__,
    )

    return await openai_proxy_client.proxy(request)
