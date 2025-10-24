# pylint: disable=direct-environment-variable-reference

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Optional

import grpc
from lib.internal_events import EventContext, current_event_context
from neoai_workflow_service.interceptors import (
    X_GITLAB_FEATURE_ENABLED_BY_NAMESPACE_IDS,
    X_GITLAB_FEATURE_ENABLEMENT_TYPE, X_GITLAB_GLOBAL_USER_ID_HEADER,
    X_GITLAB_HOST_NAME, X_GITLAB_INSTANCE_ID_HEADER,
    X_GITLAB_IS_A_GITLAB_MEMBER, X_GITLAB_NAMESPACE_ID, X_GITLAB_PROJECT_ID,
    X_GITLAB_REALM_HEADER, X_GITLAB_ROOT_NAMESPACE_ID, X_GITLAB_USER_ID_HEADER)
from neoai_workflow_service.interceptors.correlation_id_interceptor import \
    correlation_id
from neoai_workflow_service.interceptors.gitlab_version_interceptor import \
    gitlab_version
from neoai_workflow_service.interceptors.language_server_version_interceptor import \
    language_server_version


def convert_feature_enabled_string_to_list(
    enabled_features: Optional[str] = None,
) -> Optional[List[int]]:
    if not enabled_features or enabled_features == "undefined":
        return None

    feature_list = [int(feature.strip()) for feature in enabled_features.split(",")]
    return list(dict.fromkeys(feature_list))


class InternalEventsInterceptor(grpc.aio.ServerInterceptor):

    def __init__(self):
        pass

    async def intercept_service(self, continuation, handler_call_details: grpc.HandlerCallDetails) -> None:
        metadata = dict(handler_call_details.invocation_metadata)

        is_gitlab_member = metadata.get(X_GITLAB_IS_A_GITLAB_MEMBER, None)
        is_gitlab_member = is_gitlab_member.lower() == "true" if is_gitlab_member else None

        feature_enabled_by_namespace_ids = metadata.get(X_GITLAB_FEATURE_ENABLED_BY_NAMESPACE_IDS, None)
        feature_enabled_by_namespace_ids = (
            str(feature_enabled_by_namespace_ids) if feature_enabled_by_namespace_ids else None
        )

        project_id = metadata.get(X_GITLAB_PROJECT_ID)
        project_id = int(project_id) if project_id else None

        namespace_id = metadata.get(X_GITLAB_NAMESPACE_ID)
        namespace_id = int(namespace_id) if namespace_id else None

        # Get language server version from context
        lsp_version = language_server_version.get()
        extra = {}
        if lsp_version and hasattr(lsp_version, "version"):
            extra["lsp_version"] = str(lsp_version.version)

        # Get GitLab instance version from context
        instance_version_value = gitlab_version.get()

        context = EventContext(
            realm=metadata.get(X_GITLAB_REALM_HEADER),
            environment=os.environ.get("NEOAI_WORKFLOW_SERVICE_ENVIRONMENT", "development"),
            source="neoai-workflow-service-python",
            instance_id=metadata.get(X_GITLAB_INSTANCE_ID_HEADER),
            host_name=metadata.get(X_GITLAB_HOST_NAME),
            instance_version=instance_version_value,
            global_user_id=metadata.get(X_GITLAB_GLOBAL_USER_ID_HEADER),
            user_id=metadata.get(X_GITLAB_USER_ID_HEADER),
            context_generated_at=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id.get(),
            project_id=project_id,
            feature_enabled_by_namespace_ids=convert_feature_enabled_string_to_list(
                enabled_features=feature_enabled_by_namespace_ids
            ),
            feature_enablement_type=metadata.get(X_GITLAB_FEATURE_ENABLEMENT_TYPE),
            namespace_id=namespace_id,
            ultimate_parent_namespace_id=metadata.get(X_GITLAB_ROOT_NAMESPACE_ID, None) or None,
            is_gitlab_team_member=is_gitlab_member,
            extra=extra,
        )

        current_event_context.set(context)

        return await continuation(handler_call_details)
