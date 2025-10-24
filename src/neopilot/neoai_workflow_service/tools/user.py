from __future__ import annotations

import json
from typing import Any, Type

import structlog
from neoai_workflow_service.tools.neoai_base_tool import NeoaiBaseTool
from pydantic import BaseModel

log = structlog.stdlib.get_logger(__name__)


class GetCurrentUserInput(BaseModel):
    pass


class GetCurrentUser(NeoaiBaseTool):
    name: str = "get_current_user"
    description: str = """
    Get the current user information from GitLab API

    Only the following information will be retrieved from the current user endpoint:
    - user name
    - job title
    - preferred languages (written in ISO 639‑1 language code)
    """
    args_schema: Type[BaseModel] = GetCurrentUserInput

    async def _execute(self) -> str:
        try:
            response = await self.gitlab_client.aget(path="/api/v4/user", parse_json=True, use_http_response=True)

            if not response.is_success():
                log.error(
                    "Get current user request failed with status %s: %s",
                    response.status_code,
                    response.body,
                )

            formatted_response = {
                "user_name": response.body.get("username"),
                "job_title": response.body.get("job_title"),
                "preferred_language": response.body.get("preferred_language"),
            }

            return json.dumps({"user": formatted_response})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def format_display_message(self, args: GetCurrentUserInput, _tool_response: Any = None) -> str:
        return "Get current user information"
