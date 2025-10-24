from typing import AsyncIterator, Generic, Optional, cast

import starlette_context
from gitlab_cloud_connector import GitLabUnitPrimitive

from neopilot.ai_gateway.api.auth_utils import StarletteUser
from neopilot.ai_gateway.chat.agents import (
    AgentError,
    AgentToolAction,
    ReActAgent,
    TypeAgentEvent,
    TypeAgentInputs,
)
from neopilot.ai_gateway.chat.agents.react import ReActAgentInputs
from neopilot.ai_gateway.chat.base import BaseToolsRegistry
from neopilot.ai_gateway.chat.tools import BaseTool
from neopilot.ai_gateway.model_metadata import TypeModelMetadata
from neopilot.ai_gateway.prompts.config.models import ModelClassProvider
from neopilot.ai_gateway.structured_logging import get_request_logger
from lib.internal_events import InternalEventsClient

__all__ = [
    "GLAgentRemoteExecutor",
]

_REACT_AGENT_AVAILABLE_TOOL_NAMES_CONTEXT_KEY = "neoai_chat.agent_available_tools"

log = get_request_logger("gl_agent_remote_executor")


class GLAgentRemoteExecutor(Generic[TypeAgentInputs, TypeAgentEvent]):
    def __init__(
        self,
        *,
        agent: ReActAgent,
        tools_registry: BaseToolsRegistry,
        internal_event_client: InternalEventsClient,
    ):
        self.agent = agent
        self.tools_registry = tools_registry
        self.internal_event_client = internal_event_client
        self._tools: list[BaseTool] | None = None

    @property
    def tools(self) -> list[BaseTool]:
        if self._tools is None:
            self._tools = self.tools_registry.get_all()

        return self._tools

    @property
    def tools_by_name(self) -> dict:
        return {tool.name: tool for tool in self.tools}

    def on_behalf(
        self,
        user: StarletteUser,
        gl_version: str,
        model_metadata: Optional[TypeModelMetadata] = None,
    ):
        # Access the user tools as soon as possible to raise an exception
        # (in case of invalid unit primitives) before starting the data stream.
        # Reason: https://github.com/tiangolo/fastapi/discussions/10138
        if not user.is_debug:
            # TODO: Remove it when proper access control for unit primitives with different providers is implemented
            # https://gitlab.com/gitlab-org/cloud-connector/gitlab-cloud-connector/-/issues/60
            if (
                model_metadata
                and model_metadata.provider == ModelClassProvider.AMAZON_Q
                and user.can(GitLabUnitPrimitive.AMAZON_Q_INTEGRATION)
            ):
                self._tools = [tool for tool in self.tools_registry.get_all() if tool.is_compatible(gl_version)]
            else:
                self._tools = self.tools_registry.get_on_behalf(user, gl_version)

    async def stream(self, *, inputs: TypeAgentInputs) -> AsyncIterator[TypeAgentEvent]:
        inputs.tools = self.tools

        tools_by_name = self.tools_by_name

        starlette_context.context[_REACT_AGENT_AVAILABLE_TOOL_NAMES_CONTEXT_KEY] = list(tools_by_name.keys())

        log.info("Processed inputs", source=__name__, inputs=inputs)

        async for event in self.agent.astream(cast(ReActAgentInputs, inputs)):
            if isinstance(event, AgentToolAction):
                if event.tool in tools_by_name:
                    tool = tools_by_name[event.tool]
                    self.internal_event_client.track_event(
                        f"request_{tool.unit_primitive}",
                        category=__name__,
                    )
                    yield cast(TypeAgentEvent, event)
                else:
                    yield cast(
                        TypeAgentEvent,
                        AgentError(message="tool not available", retryable=False),
                    )
            else:
                yield event
