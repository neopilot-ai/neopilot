from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from gitlab_cloud_connector import (CloudConnectorConfig,
                                    GitLabFeatureCategory, GitLabUnitPrimitive)
from lib.internal_events import InternalEventsClient

from neopilot.ai_gateway.api.auth_utils import StarletteUser, get_current_user
from neopilot.ai_gateway.api.feature_category import feature_category
from neopilot.ai_gateway.api.v1.x_ray.typing import XRayRequest, XRayResponse
from neopilot.ai_gateway.async_dependency_resolver import (
    get_internal_event_client, get_x_ray_anthropic_claude)
from neopilot.ai_gateway.models import AnthropicModel

__all__ = [
    "router",
]

log = structlog.stdlib.get_logger("x-ray")

router = APIRouter()


@router.post(
    "/libraries",
    response_model=XRayResponse,
    deprecated=True,
    summary="Deprecated endpoint",
    description="This endpoint is deprecated and will be removed "
    "https://github.com/neopilot-ai/neopilot/-/issues/692",
)
@feature_category(GitLabFeatureCategory.CODE_SUGGESTIONS)
async def libraries(
    request: Request,  # pylint: disable=unused-argument
    payload: XRayRequest,
    current_user: Annotated[StarletteUser, Depends(get_current_user)],
    model: Annotated[AnthropicModel, Depends(get_x_ray_anthropic_claude)],
    internal_event_client: Annotated[InternalEventsClient, Depends(get_internal_event_client)],
):
    if not current_user.can(
        GitLabUnitPrimitive.GENERATE_CODE,
        disallowed_issuers=[CloudConnectorConfig().service_name],
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to access X Ray",
        )

    internal_event_client.track_event(
        f"request_{GitLabUnitPrimitive.GENERATE_CODE}",
        category=__name__,
    )

    package_file_prompt = payload.prompt_components[0].payload

    completion = await model.generate(
        prefix=package_file_prompt.prompt,
        _suffix="",
    )

    # Handle direct completion
    if hasattr(completion, "text"):
        response = completion.text
    elif isinstance(completion, list):
        # Non-streamed multiple outputs
        response = "".join([c.text for c in completion])
    else:
        # Handle streaming completion
        chunks = []
        async for chunk in completion:
            chunks.append(chunk.text)
        response = "".join(chunks)

    return XRayResponse(response=response)
