from __future__ import annotations

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from gitlab_cloud_connector import (CloudConnectorConfig,
                                    GitLabFeatureCategory, GitLabUnitPrimitive,
                                    TokenAuthority)
from lib.internal_events import InternalEventsClient

from neopilot.ai_gateway.api.auth_utils import StarletteUser, get_current_user
from neopilot.ai_gateway.api.feature_category import feature_category
from neopilot.ai_gateway.api.v1.code.typing import Token
from neopilot.ai_gateway.async_dependency_resolver import (
    get_internal_event_client, get_token_authority)

__all__ = [
    "router",
]


log = structlog.stdlib.get_logger("user_access_token")

router = APIRouter()


@router.post("/user_access_token")
@feature_category(GitLabFeatureCategory.CODE_SUGGESTIONS)
async def user_access_token(
    request: Request,  # pylint: disable=unused-argument
    current_user: Annotated[StarletteUser, Depends(get_current_user)],
    token_authority: Annotated[TokenAuthority, Depends(get_token_authority)],
    internal_event_client: Annotated[InternalEventsClient, Depends(get_internal_event_client)],
    x_gitlab_global_user_id: Annotated[
        Optional[str], Header()
    ] = None,  # This is the value of X_GITLAB_GLOBAL_USER_ID_HEADER
    x_gitlab_realm: Annotated[Optional[str], Header()] = None,  # This is the value of X_GITLAB_REALM_HEADER
    x_gitlab_instance_id: Annotated[Optional[str], Header()] = None,  # This is the value of X_GITLAB_INSTANCE_ID_HEADER
):
    unit_primitives = [
        GitLabUnitPrimitive.COMPLETE_CODE,
        GitLabUnitPrimitive.AI_GATEWAY_MODEL_PROVIDER_PROXY,
    ]
    scopes = [
        unit_primitive
        for unit_primitive in unit_primitives
        if current_user.can(unit_primitive, disallowed_issuers=[CloudConnectorConfig().service_name])
    ]

    if not scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to create user access token",
        )

    internal_event_client.track_event(
        f"request_{GitLabUnitPrimitive.COMPLETE_CODE}",
        category=__name__,
    )

    if not x_gitlab_global_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Gitlab-Global-User-Id header",
        )

    if not x_gitlab_instance_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Gitlab-Instance-Id header",
        )

    if not x_gitlab_realm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Gitlab-Realm header",
        )

    try:
        token, expires_at = token_authority.encode(
            x_gitlab_global_user_id,
            x_gitlab_realm,
            current_user,
            x_gitlab_instance_id,
            scopes=scopes,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate JWT",
        )

    return Token(token=token, expires_at=expires_at)
