import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Dict, Optional

import jsonschema
from dependency_injector.wiring import Provide, inject
from gitlab_cloud_connector import CloudConnectorUser
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple
from langgraph.graph import StateGraph
from langgraph.types import Command

from neopilot.ai_gateway.container import ContainerApplication
from neopilot.ai_gateway.prompts import InMemoryPromptRegistry
from neopilot.ai_gateway.prompts.registry import LocalPromptRegistry
from contract import contract_pb2
from neoai_workflow_service.agent_platform.v1.components.base import (
    BaseComponent,
    EndComponent,
)
from neoai_workflow_service.agent_platform.v1.flows.flow_config import (
    FlowConfig,
    load_component_class,
)
from neoai_workflow_service.agent_platform.v1.routers import Router
from neoai_workflow_service.agent_platform.v1.state import FlowState
from neoai_workflow_service.agent_platform.v1.state.base import FlowEvent, FlowEventType
from neoai_workflow_service.checkpointer.gitlab_workflow_utils import (
    WorkflowStatusEventEnum,
)
from neoai_workflow_service.components.tools_registry import ToolsRegistry
from neoai_workflow_service.entities.state import (
    MessageTypeEnum,
    ToolStatus,
    UiChatLog,
    WorkflowStatusEnum,
)
from neoai_workflow_service.tracking.errors import log_exception
from neoai_workflow_service.workflows.abstract_workflow import (
    AbstractWorkflow,
    InvocationMetadata,
)
from neoai_workflow_service.workflows.type_definitions import AdditionalContext
from lib.internal_events.client import InternalEventsClient
from lib.internal_events.event_enum import CategoryEnum

__all__ = ["Flow"]

_EXECUTOR_CONTEXT = ["os_information", "shell_information", "agent_user_environment"]


class UserDecision(StrEnum):
    APPROVE = "approval"
    REJECT = "rejection"


class Flow(AbstractWorkflow):
    _config: FlowConfig
    _flow_prompt_registry: InMemoryPromptRegistry | LocalPromptRegistry

    # pylint: disable=dangerous-default-value
    @inject
    def __init__(
        self,
        workflow_id: str,
        workflow_metadata: Dict[str, Any],
        workflow_type: CategoryEnum,
        config: FlowConfig,
        invocation_metadata: InvocationMetadata = {
            "base_url": "",
            "gitlab_token": "",
        },
        mcp_tools: list[contract_pb2.McpTool] = [],
        user: Optional[CloudConnectorUser] = None,
        additional_context: Optional[list[AdditionalContext]] = None,
        approval: Optional[contract_pb2.Approval] = None,
        prompt_registry: LocalPromptRegistry = Provide[ContainerApplication.pkg_prompts.prompt_registry],
        internal_event_client: InternalEventsClient = Provide[ContainerApplication.internal_event.client],
        **kwargs,
    ):
        super().__init__(
            workflow_id=workflow_id,
            workflow_metadata=workflow_metadata,
            workflow_type=workflow_type,
            invocation_metadata=invocation_metadata,
            mcp_tools=mcp_tools,
            user=user,
            additional_context=additional_context,
            approval=approval,
            prompt_registry=prompt_registry,
            internal_event_client=internal_event_client,
            **kwargs,
        )
        self._config = config

        self._flow_prompt_registry = InMemoryPromptRegistry(prompt_registry)
        if self._config.prompts:
            for prompt_config in self._config.prompts:
                prompt_id = prompt_config.prompt_id
                self._flow_prompt_registry.register_prompt(
                    prompt_id=prompt_id,
                    prompt_data=prompt_config.to_prompt_config().model_dump(),
                )

    # pylint: enable=dangerous-default-value

    def get_workflow_state(self, goal: str) -> FlowState:  # type: ignore[override]
        initial_ui_chat_log = UiChatLog(
            message_type=MessageTypeEnum.TOOL,
            content=f"Starting Flow: {goal}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=ToolStatus.SUCCESS,
            correlation_id=None,
            tool_info=None,
            additional_context=None,
            message_sub_type=None,
        )

        return FlowState(
            status=WorkflowStatusEnum.NOT_STARTED,
            conversation_history={},
            ui_chat_log=[initial_ui_chat_log],
            context={
                "project_id": self._project.get("id"),  # type: ignore[union-attr]
                "project_http_url_to_repo": self._project.get("http_url_to_repo"),  # type: ignore[union-attr]
                "goal": goal,
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "workflow_id": self._workflow_id,
                "inputs": self._process_additional_context(self._additional_context or []),
            },
        )

    def _process_additional_context(self, additional_context: list[AdditionalContext]) -> Dict:
        processed_additional_context = {}

        jsonschemas_by_category = self._config.input_json_schemas_by_category()
        for item in additional_context:
            if item.category in _EXECUTOR_CONTEXT:  # This category is passed in from the executor
                processed_additional_context[item.category] = item.content
                continue

            if item.category not in jsonschemas_by_category.keys():
                raise ValueError(f"input schema was not provided for the category '{item.category}'.")
            try:
                schema = jsonschemas_by_category.get(item.category)
                if not item.content:
                    raise ValueError(f"content must be specified for input '{item.category}'.")

                content_object = json.loads(item.content)
                jsonschema.validate(content_object, schema)
                processed_additional_context[item.category] = content_object
            except jsonschema.ValidationError as e:
                raise ValueError(f"input '{item.category}' does not match specified schema: {e}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in input item, {e}")

        return processed_additional_context

    def _resume_command(self, goal: str) -> Command:
        event = FlowEvent(event_type=FlowEventType.RESPONSE, message=goal)
        if not self._approval:
            # Handle case where approval is None
            return Command(resume=event)

        match self._approval.WhichOneof("user_decision"):
            case UserDecision.APPROVE:
                event = FlowEvent(event_type=FlowEventType.APPROVE)
            case UserDecision.REJECT:
                event = FlowEvent(
                    event_type=FlowEventType.REJECT,
                    message=self._approval.rejection.message,
                )
            case _:
                # This should never happen according to contract.proto
                raise ValueError(f"Unexpected approval decision: {self._approval.WhichOneof('user_decision')}")

        return Command(resume=event)

    async def get_graph_input(self, goal: str, status_event: str, checkpoint_tuple: Optional[CheckpointTuple]) -> Any:
        match status_event:
            case WorkflowStatusEventEnum.START:
                return self.get_workflow_state(goal)
            case WorkflowStatusEventEnum.RESUME:
                return self._resume_command(goal)
            case WorkflowStatusEventEnum.RETRY:
                if checkpoint_tuple is None:
                    return self.get_workflow_state(goal)  # no saved checkpoints from last run
                return None  # retry from last checkpoint
            case _:
                return None

    def _build_components(self, tools_registry: ToolsRegistry, graph: StateGraph) -> dict[str, BaseComponent]:
        end_component = EndComponent(
            name="end",
            flow_id=self._workflow_id,
            flow_type=self._workflow_type,
        )
        end_component.attach(graph)

        components: dict[str, BaseComponent] = {"end": end_component}

        for comp_config in self._config.components:
            comp_name = comp_config["name"]  # explicit name field
            comp_class = load_component_class(comp_config["type"])

            comp_params = {k: v for k, v in comp_config.items() if k != "type"}

            comp_params.update(
                {
                    "prompt_registry": self._flow_prompt_registry,  # override DI
                    "flow_id": self._workflow_id,
                    "flow_type": self._workflow_type,
                }
            )

            if "toolset" in comp_params:
                comp_params["toolset"] = tools_registry.toolset(comp_params["toolset"])
            elif "tool_name" in comp_params:
                # If a tool_name is specified without a toolset, create a toolset containing just that tool.
                comp_params["toolset"] = tools_registry.toolset([comp_params["tool_name"]])

            if comp_name in components:
                raise ValueError(f"Duplicate component name: '{comp_name}'. Component names must be unique.")

            components[comp_name] = comp_class(**comp_params)

        return components

    def _build_routers(self, components: dict[str, BaseComponent], graph: StateGraph) -> None:
        """Build and attach routers to the graph based on configuration.

        Creates routers that orders components in the flow graph.
        Supports conditional routing based on component outputs.

        Args:
            components: Dictionary of component instances keyed by name
            graph: The StateGraph instance to attach routers to

        Example conditional router configuration:

        - from: "human_input"
            condition:
                input: "status"
                routes:
                    "Execution": "agent"
                    "default_route": "end"
        """
        for router_config in self._config.routers:
            from_comp = components[router_config["from"]]

            if "condition" in router_config:
                to_components = {}
                for route_key, comp_name in router_config["condition"]["routes"].items():
                    to_components[route_key] = components[comp_name]

                input_field = router_config["condition"]["input"]
                if not isinstance(input_field, str):
                    raise ValueError("Router input must be a string.")

                router = Router(
                    from_component=from_comp,
                    input=router_config["condition"]["input"],
                    to_component=to_components,
                )
            else:
                to_comp = components[router_config["to"]]
                router = Router(from_component=from_comp, to_component=to_comp)

            router.attach(graph)

    def _compile(
        self,
        goal: str,
        tools_registry: ToolsRegistry,
        checkpointer: BaseCheckpointSaver,
    ) -> Any:
        graph = StateGraph(FlowState)
        components = self._build_components(tools_registry, graph)
        self._build_routers(components, graph)

        entry_component = components[self._config.flow.entry_point]
        graph.set_entry_point(entry_component.__entry_hook__())

        return graph.compile(checkpointer=checkpointer)

    async def _handle_workflow_failure(self, error: BaseException, compiled_graph: Any, graph_config: Any):
        log_exception(error, extra={"workflow_id": self._workflow_id, "source": __name__})
