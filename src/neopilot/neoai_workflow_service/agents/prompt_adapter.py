from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Union

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompt_values import ChatPromptValue, PromptValue
from langchain_core.runnables import Runnable, RunnableConfig

from neopilot.ai_gateway.model_metadata import current_model_metadata_context
from neopilot.ai_gateway.prompts import Prompt, jinja2_formatter
from neopilot.ai_gateway.prompts.config.base import PromptConfig
from neopilot.ai_gateway.prompts.config.models import ModelClassProvider
from neoai_workflow_service.agents.base import BaseAgent
from neoai_workflow_service.entities.state import ChatWorkflowState
from neoai_workflow_service.gitlab.gitlab_api import Namespace, Project
from neoai_workflow_service.gitlab.gitlab_service_context import GitLabServiceContext
from neoai_workflow_service.slash_commands.goal_parser import parse as slash_command_parse


class ChatAgentPromptTemplate(Runnable[ChatWorkflowState, PromptValue]):
    def __init__(self, prompt_template: dict[str, str]):
        self.prompt_template = prompt_template

    def invoke(
        self,
        input: ChatWorkflowState,
        config: Optional[RunnableConfig] = None,  # pylint: disable=unused-argument
        **_kwargs: Any,
    ) -> PromptValue:
        messages: list[BaseMessage] = []
        agent_name = _kwargs["agent_name"]
        project: Project | None = input.get("project")
        namespace: Namespace | None = input.get("namespace")

        # Get GitLab instance info from context
        gitlab_instance_info = GitLabServiceContext.get_current_instance_info()

        model_metadata = current_model_metadata_context.get()

        # Handle system messages with static and dynamic parts
        # Create separate system messages for static and dynamic parts
        if "system_static" in self.prompt_template:
            static_content_text = jinja2_formatter(
                self.prompt_template["system_static"],
                gitlab_instance_type=(gitlab_instance_info.instance_type if gitlab_instance_info else "Unknown"),
                gitlab_instance_url=(gitlab_instance_info.instance_url if gitlab_instance_info else "Unknown"),
                gitlab_instance_version=(gitlab_instance_info.instance_version if gitlab_instance_info else "Unknown"),
                model_friendly_name=(
                    model_metadata.friendly_name if model_metadata and model_metadata.friendly_name else "Unknown"
                ),
            )
            # Always cache static system prompt for Anthropic models
            is_anthropic = _kwargs.get("is_anthropic_model", False)
            if is_anthropic:
                cached_static_content: list[Union[str, dict]] = [
                    {
                        "text": static_content_text,
                        "type": "text",
                        "cache_control": {"type": "ephemeral", "ttl": "5m"},
                    }
                ]
                messages.append(SystemMessage(content=cached_static_content))
            else:
                messages.append(SystemMessage(content=static_content_text))

        if "system_dynamic" in self.prompt_template:
            dynamic_content = jinja2_formatter(
                self.prompt_template["system_dynamic"],
                current_date=datetime.now().strftime("%Y-%m-%d"),
                current_time=datetime.now().strftime("%H:%M:%S"),
                current_timezone=datetime.now().astimezone().tzname(),
                project=project,
                namespace=namespace,
            )
            messages.append(SystemMessage(content=dynamic_content))

        for m in input["conversation_history"][agent_name]:
            if isinstance(m, HumanMessage):
                slash_command = None

                if isinstance(m.content, str) and m.content.strip().startswith("/"):
                    command_name, remaining_text = slash_command_parse(m.content)
                    slash_command = {
                        "name": command_name,
                        "input": remaining_text,
                    }

                messages.append(
                    HumanMessage(
                        jinja2_formatter(
                            self.prompt_template["user"],
                            message=m,
                            slash_command=slash_command,
                        )
                    )
                )
            else:
                messages.append(m)  # AIMessage or ToolMessage

        return ChatPromptValue(messages=messages)


class ChatPrompt(BaseAgent[ChatWorkflowState, BaseMessage]):
    @classmethod
    def _build_prompt_template(cls, config: PromptConfig) -> Runnable:
        return ChatAgentPromptTemplate(config.prompt_template)


class BasePromptAdapter(ABC):
    prompt: Prompt

    def __init__(self, prompt: Prompt):
        self.prompt = prompt

    @abstractmethod
    async def get_response(self, input: ChatWorkflowState) -> BaseMessage:
        pass

    @abstractmethod
    def get_model(self):
        pass


class DefaultPromptAdapter(BasePromptAdapter):
    async def get_response(self, input: ChatWorkflowState) -> BaseMessage:
        is_anthropic_model = self.prompt.model_provider == ModelClassProvider.ANTHROPIC

        return await self.prompt.ainvoke(
            input=input,
            agent_name=self.prompt.name,
            is_anthropic_model=is_anthropic_model,
        )

    def get_model(self):
        return self.prompt.model


class CustomPromptAdapter(BasePromptAdapter):
    def __init__(self, prompt: Prompt):
        super().__init__(prompt)
        self._agent_name = prompt.name

    # Custom prompts don't have ChatAgentPromptTemplate's built-in handling, so we manually inject the
    # system_dynamic to match the behavior that ChatPrompt/ChatAgentPromptTemplate provides automatically.
    @staticmethod
    def enrich_prompt_template(prompt_template: dict[str, Any]) -> dict[str, Any]:
        if "prompt_template" not in prompt_template:
            raise ValueError("prompt_template must contain 'prompt_template' key")

        context_template = "{% include 'chat/agent/partials/system_dynamic/1.0.0.jinja' %}"
        additional_context_template = "{% include 'chat/agent/partials/additional_context/1.0.0.jinja' %}"

        if "system" in prompt_template["prompt_template"]:
            existing_system = prompt_template["prompt_template"]["system"]
            if context_template not in existing_system:
                prompt_template["prompt_template"]["system"] = (
                    "<system_instructions>\n"
                    + existing_system
                    + "\n</system_instructions>\n"
                    + context_template
                    + "\n"
                    + additional_context_template
                )
        else:
            prompt_template["prompt_template"]["system"] = context_template

        return prompt_template

    async def get_response(self, input: ChatWorkflowState) -> BaseMessage:
        conversation_history = input["conversation_history"].get(self._agent_name, [])
        last_message = conversation_history[-1] if conversation_history else None
        additional_context = (
            last_message.additional_kwargs.get("additional_context")
            if last_message and hasattr(last_message, "additional_kwargs")
            else None
        )

        variables = {
            "goal": input["goal"],
            "project": input["project"],
            "namespace": input["namespace"],
            "current_date": datetime.now().strftime("%Y-%m-%d"),
            "current_time": datetime.now().strftime("%H:%M:%S"),
            "current_timezone": datetime.now().astimezone().tzname(),
            "additional_context": additional_context,
        }

        return await self.prompt.ainvoke(input={**variables, "history": conversation_history})

    def get_model(self):
        return self.prompt.model
