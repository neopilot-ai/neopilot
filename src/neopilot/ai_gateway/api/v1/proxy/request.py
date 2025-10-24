from __future__ import annotations

import functools
import typing

from fastapi import BackgroundTasks, HTTPException, Request, status
from gitlab_cloud_connector import (FEATURE_CATEGORIES_FOR_PROXY_ENDPOINTS,
                                    UNIT_PRIMITIVE_AND_DESCRIPTION_MAPPING,
                                    GitLabFeatureCategory, GitLabUnitPrimitive)

from neopilot.ai_gateway.abuse_detection import AbuseDetector
from neopilot.ai_gateway.api.auth_utils import StarletteUser
from neopilot.ai_gateway.api.feature_category import X_GITLAB_UNIT_PRIMITIVE

# It's implemented here, because eventually we want to restrict this endpoint to
# ai_gateway_model_provider_proxy unit primitive only, so we won't rely on
# FEATURE_CATEGORIES_FOR_PROXY_ENDPOINTS const anymore.
#
# https://github.com/neopilot-ai/neopilot/-/issues/1420
#
# Currently, this endpoint is used by older self-managed instances, so we cannot just restrict
# the list of unit primitives due to the backward compatibility promise.
EXTENDED_FEATURE_CATEGORIES_FOR_PROXY_ENDPOINTS = {
    **FEATURE_CATEGORIES_FOR_PROXY_ENDPOINTS,
    **{GitLabUnitPrimitive.AI_GATEWAY_MODEL_PROVIDER_PROXY: GitLabFeatureCategory.NEOAI_AGENT_PLATFORM},
}


def authorize_with_unit_primitive_header():
    """Authorize with x-gitlab-unit-primitive header.

    See
    https://github.com/neopilot-ai/neopilot/-/blob/main/docs/auth.md#use-x-gitlab-unit-primitive-header
    for more information.
    """

    def decorator(func: typing.Callable) -> typing.Callable:
        @functools.wraps(func)
        async def wrapper(
            request: Request,
            background_tasks: BackgroundTasks,
            abuse_detector: AbuseDetector,
            *args: typing.Any,
            **kwargs: typing.Any,
        ) -> typing.Any:
            await _validate_request(request, background_tasks, abuse_detector)
            return await func(request, background_tasks, abuse_detector, *args, **kwargs)

        return wrapper

    return decorator


async def _validate_request(request: Request, background_tasks: BackgroundTasks, abuse_detector: AbuseDetector) -> None:
    if X_GITLAB_UNIT_PRIMITIVE not in request.headers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing {X_GITLAB_UNIT_PRIMITIVE} header",
        )

    unit_primitive = request.headers[X_GITLAB_UNIT_PRIMITIVE]

    if unit_primitive not in GitLabUnitPrimitive.__members__.values():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown unit primitive header {unit_primitive}",
        )

    unit_primitive = GitLabUnitPrimitive(unit_primitive)

    current_user: StarletteUser = request.user

    if not current_user.can(unit_primitive):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized to access {unit_primitive}",
        )

    if abuse_detector.should_detect():
        body_bytes = await request.body()
        body = body_bytes.decode("utf-8", errors="ignore")

        description = UNIT_PRIMITIVE_AND_DESCRIPTION_MAPPING.get(unit_primitive, "")
        background_tasks.add_task(abuse_detector.detect, request, body, description)
