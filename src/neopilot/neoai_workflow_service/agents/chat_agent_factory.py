from typing import Optional, Type, Union

from gitlab_cloud_connector import CloudConnectorUser

from neopilot.ai_gateway.model_metadata import TypeModelMetadata
from neopilot.ai_gateway.prompts import InMemoryPromptRegistry, Prompt
from neopilot.ai_gateway.prompts.registry import LocalPromptRegistry
from neoai_workflow_service.agents.chat_agent import ChatAgent
from neoai_workflow_service.agents.prompt_adapter import (
    BasePromptAdapter,
    DefaultPromptAdapter,
)
from neoai_workflow_service.components.tools_registry import Toolset, ToolsRegistry
from lib.internal_events.event_enum import CategoryEnum


def create_agent(
    user: CloudConnectorUser,
    tools_registry: ToolsRegistry,
    prompt_id: str,
    prompt_version: str | None,
    model_metadata: Optional[TypeModelMetadata],
    internal_event_category: str,
    tools: Toolset,
    prompt_registry: Union[LocalPromptRegistry, InMemoryPromptRegistry],
    workflow_id: str,
    workflow_type: CategoryEnum,
    adapter_cls: Type[BasePromptAdapter] = DefaultPromptAdapter,
) -> ChatAgent:
    prompt: Prompt = prompt_registry.get_on_behalf(
        user=user,
        prompt_id=prompt_id,
        prompt_version=prompt_version,  # type: ignore[arg-type]
        model_metadata=model_metadata,
        internal_event_category=internal_event_category,
        tools=tools.bindable,  # type: ignore[arg-type]
        workflow_id=workflow_id,
        workflow_type=workflow_type,
    )

    return ChatAgent(
        name=prompt.name,
        prompt_adapter=adapter_cls(prompt),
        tools_registry=tools_registry,
    )
