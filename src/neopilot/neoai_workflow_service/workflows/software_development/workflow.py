# pylint: disable=unknown-option-value,direct-environment-variable-reference
import os
from datetime import datetime, timezone
from enum import StrEnum
from functools import partial
from typing import Annotated

# pylint disables are going to be fixed via
# https://gitlab.com/gitlab-org/neoai-workflow/neoai-workflow-service/-/issues/78
from langchain_core.messages import (  # pylint: disable=no-langgraph-langchain-imports
    AIMessage,
)
from langgraph.checkpoint.memory import (  # pylint: disable=no-langgraph-langchain-imports
    BaseCheckpointSaver,
)
from langgraph.graph import (  # pylint: disable=no-langgraph-langchain-imports
    END,
    StateGraph,
)

from neopilot.ai_gateway.model_metadata import current_model_metadata_context
from neoai_workflow_service.agents import (
    HandoverAgent,
    PlanSupervisorAgent,
    PlanTerminatorAgent,
    ToolsExecutor,
)
from neoai_workflow_service.components import (
    PlanApprovalComponent,
    ToolsApprovalComponent,
    ToolsRegistry,
)
from neoai_workflow_service.components.executor.component import ExecutorComponent
from neoai_workflow_service.components.goal_disambiguation import (
    GoalDisambiguationComponent,
)
from neoai_workflow_service.components.planner.component import PlannerComponent
from neoai_workflow_service.entities import (
    MessageTypeEnum,
    Plan,
    ToolStatus,
    UiChatLog,
    WorkflowState,
    WorkflowStatusEnum,
)
from neoai_workflow_service.entities.agent_user_environment import (
    process_agent_user_environment,
)
from neoai_workflow_service.tools.handover import HandoverTool
from neoai_workflow_service.tracking.errors import log_exception
from neoai_workflow_service.workflows.abstract_workflow import AbstractWorkflow

# Constants
QUEUE_MAX_SIZE = 1
MAX_TOKENS_TO_SAMPLE = 16384
RECURSION_LIMIT = 300
DEBUG = os.getenv("DEBUG")
MAX_MESSAGES_TO_DISPLAY = 5
MAX_MESSAGE_LENGTH = 200

EXECUTOR_TOOLS = [
    "create_issue",
    "list_issues",
    "get_issue",
    "update_issue",
    "dismiss_vulnerability",
    "confirm_vulnerability",
    "create_issue_note",
    "get_vulnerability_details",
    "create_merge_request_note",
    "list_issue_notes",
    "get_issue_note",
    "create_merge_request",
    "get_job_logs",
    "get_merge_request",
    "get_pipeline_errors",
    "get_project",
    "run_git_command",
    "list_all_merge_request_notes",
    "list_merge_request_diffs",
    "gitlab_issue_search",
    "gitlab_blob_search",
    "gitlab_merge_request_search",
    "run_command",
    "read_file",
    "read_files",
    "update_vulnerability_severity",
    "revert_to_detected_vulnerability",
    "create_file_with_contents",
    "edit_file",
    "find_files",
    "grep",
    "mkdir",
    "add_new_task",
    "remove_task",
    "update_task_description",
    "get_plan",
    "set_task_status",
    "handover_tool",
    "get_epic",
    "list_epics",
    "create_epic",
    "update_epic",
    "get_repository_file",
    "list_dir",
    "list_epic_notes",
    "get_commit",
    "list_commits",
    "get_commit_comments",
    "get_commit_diff",
    "get_work_item",
    "list_work_items",
    "get_work_item_notes",
    "create_work_item",
    "create_work_item_note",
    "post_neoai_code_review",
]

CONTEXT_BUILDER_TOOLS = [
    "get_previous_session_context",
    "list_issues",
    "get_issue",
    "list_issue_notes",
    "get_issue_note",
    "get_job_logs",
    "get_merge_request",
    "get_project",
    "get_pipeline_errors",
    "run_read_only_git_command",
    "run_git_command",
    "list_all_merge_request_notes",
    "list_merge_request_diffs",
    "gitlab_issue_search",
    "gitlab_blob_search",
    "gitlab_merge_request_search",
    "read_file",
    "read_files",
    "find_files",
    "list_dir",
    "grep",
    "handover_tool",
    "get_epic",
    "list_epics",
    "get_repository_file",
    "list_epic_notes",
    "get_commit",
    "list_commits",
    "get_commit_comments",
    "get_commit_diff",
    "get_work_item",
    "list_work_items",
    "get_work_item_notes",
    "create_work_item",
]

PLANNER_TOOLS = [
    "get_previous_session_context",
    "get_plan",
    "add_new_task",
    "remove_task",
    "update_task_description",
    "handover_tool",
    "create_plan",
]


class Routes(StrEnum):
    END = "end"
    CALL_TOOL = "call_tool"
    TOOLS_APPROVAL = "tools_approval"
    SUPERVISOR = PlanSupervisorAgent.__name__
    HANDOVER = HandoverAgent.__name__
    BUILD_CONTEXT = "build_context"
    STOP = "stop"
    CHAT = "chat"


def _router(
    routed_agent_name: str,
    tool_registry: ToolsRegistry,
    state: WorkflowState,
) -> Routes:
    if state["status"] in [WorkflowStatusEnum.CANCELLED, WorkflowStatusEnum.ERROR]:
        return Routes.STOP

    last_message = state["conversation_history"][routed_agent_name][-1]
    if isinstance(last_message, AIMessage) and len(last_message.tool_calls) > 0:
        if last_message.tool_calls[0]["name"] == HandoverTool.tool_title:
            return Routes.HANDOVER
        if any(tool_registry.approval_required(call["name"]) for call in last_message.tool_calls):
            return Routes.TOOLS_APPROVAL
        return Routes.CALL_TOOL

    return Routes.SUPERVISOR


def _should_continue(
    state: WorkflowState,
) -> Routes:
    if state["status"] in [WorkflowStatusEnum.ERROR, WorkflowStatusEnum.CANCELLED]:
        return Routes.STOP

    return Routes.BUILD_CONTEXT


class Workflow(AbstractWorkflow):
    async def _handle_workflow_failure(self, error: BaseException, compiled_graph, graph_config):
        log_exception(error, extra={"workflow_id": self._workflow_id, "source": __name__})

    def _setup_workflow_graph(
        self,
        graph: StateGraph,
        tools_registry,
        goal,
    ):
        allow_agent_to_request_user = self._workflow_config.get("allow_agent_to_request_user", True)
        # Add nodes to the graph
        graph.set_entry_point("build_context")

        last_node_name = self._add_context_builder_nodes(graph, tools_registry)
        disambiguation_component = GoalDisambiguationComponent(
            user=self._user,
            goal=goal,
            model_config=self._model_config,
            http_client=self._http_client,
            workflow_id=self._workflow_id,
            tools_registry=tools_registry,
            allow_agent_to_request_user=allow_agent_to_request_user,
            workflow_type=self._workflow_type,
        )
        disambiguation_entry_node = disambiguation_component.attach(
            graph=graph,
            component_exit_node="planning",
            graph_termination_node="plan_terminator",
            component_execution_state=WorkflowStatusEnum.PLANNING,
        )

        graph.add_edge(last_node_name, disambiguation_entry_node)

        planner_component = PlannerComponent(
            user=self._user,
            workflow_id=self._workflow_id,
            workflow_type=self._workflow_type,
            planner_toolset=tools_registry.toolset(PLANNER_TOOLS),
            executor_toolset=tools_registry.toolset(EXECUTOR_TOOLS),
            tools_registry=tools_registry,
            model_config=self._model_config,
            goal=goal,
            project=self._project,  # type: ignore[arg-type]
            http_client=self._http_client,
            additional_context=self._additional_context,
        )

        plan_approval_component = None
        if allow_agent_to_request_user:
            plan_approval_component = PlanApprovalComponent(
                workflow_id=self._workflow_id,
                approved_agent_name="planner",
                approved_agent_state=WorkflowStatusEnum.PLANNING,
            )

        planner_component.attach(
            graph=graph,
            next_node="set_status_to_execution",
            exit_node="plan_terminator",
            approval_component=plan_approval_component,
        )
        # graph.add_edge(disambiguation_exit_node, "planning")
        plan_terminator = PlanTerminatorAgent(workflow_id=self._workflow_id)
        graph.add_node("plan_terminator", plan_terminator.run)

        graph.add_node(
            "set_status_to_execution",
            HandoverAgent(
                new_status=WorkflowStatusEnum.EXECUTION,
                handover_from="planner",
            ).run,
        )

        execution_approval_component = ToolsApprovalComponent(
            workflow_id=self._workflow_id,
            approved_agent_name="executor",
            approved_agent_state=WorkflowStatusEnum.EXECUTION,
            toolset=tools_registry.toolset(EXECUTOR_TOOLS),
        )

        executor_component = ExecutorComponent(
            workflow_id=self._workflow_id,
            workflow_type=self._workflow_type,
            executor_toolset=tools_registry.toolset(EXECUTOR_TOOLS),
            tools_registry=tools_registry,
            model_config=self._model_config,
            goal=goal,
            project=self._project,  # type: ignore[arg-type]
            http_client=self._http_client,
            additional_context=self._additional_context,
            user=self._user,
        )

        executor_entry_node = executor_component.attach(
            graph=graph,
            next_node=END,
            exit_node="plan_terminator",
            approval_component=execution_approval_component,
        )
        graph.add_edge("set_status_to_execution", executor_entry_node)

        graph.add_edge("plan_terminator", END)

        return graph

    def _compile(
        self,
        goal: str,
        tools_registry: ToolsRegistry,
        checkpointer: BaseCheckpointSaver,
    ):
        graph = StateGraph(WorkflowState)

        graph = self._setup_workflow_graph(
            graph,
            tools_registry,
            goal,
        )

        return graph.compile(checkpointer=checkpointer)

    def get_workflow_state(self, goal: str) -> WorkflowState:
        initial_ui_chat_log = UiChatLog(
            message_type=MessageTypeEnum.TOOL,
            message_sub_type=None,
            content=f"Starting workflow with goal: {goal}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=ToolStatus.SUCCESS,
            correlation_id=None,
            tool_info=None,
            additional_context=None,
        )

        return WorkflowState(
            plan=Plan(steps=[]),
            status=WorkflowStatusEnum.NOT_STARTED,
            conversation_history={},
            last_human_input=None,
            handover=[],
            ui_chat_log=[initial_ui_chat_log],
            project=self._project,
            goal=goal,
            additional_context=self._additional_context,
        )

    def _setup_context_builder(self, tools_registry: ToolsRegistry):
        context_builder_toolset = tools_registry.toolset(CONTEXT_BUILDER_TOOLS)

        context_builder = self._prompt_registry.get_on_behalf(
            self._user,
            "workflow/context_builder",
            "^1.0.0",
            tools=context_builder_toolset.bindable,  # type: ignore[arg-type]
            workflow_id=self._workflow_id,
            workflow_type=self._workflow_type,
            http_client=self._http_client,
            model_metadata=current_model_metadata_context.get(),
        )

        context_builder.prompt_template_inputs.setdefault("agent_user_environment", {}).update(
            process_agent_user_environment(self._additional_context)
        )

        return {
            "agent": context_builder,
            "toolset": context_builder_toolset,
            "handover": HandoverAgent(
                new_status=WorkflowStatusEnum.PLANNING,
                handover_from=context_builder.name,
                include_conversation_history=True,
            ),
            "supervisor": PlanSupervisorAgent(supervised_agent_name="context_builder"),
            "tools_executor": ToolsExecutor(
                tools_agent_name=context_builder.name,
                toolset=context_builder_toolset,
                workflow_id=self._workflow_id,
                workflow_type=self._workflow_type,
            ),
        }

    def _add_context_builder_nodes(
        self, graph: StateGraph, tools_registry: ToolsRegistry
    ) -> Annotated[str, "The name of the last handover node"]:
        context_builder_components = self._setup_context_builder(tools_registry)

        graph.add_node("build_context", context_builder_components["agent"].run)
        graph.add_node("build_context_tools", context_builder_components["tools_executor"].run)
        graph.add_node("build_context_handover", context_builder_components["handover"].run)
        graph.add_node("build_context_supervisor", context_builder_components["supervisor"].run)

        context_builder_approval_component = ToolsApprovalComponent(
            workflow_id=self._workflow_id,
            approved_agent_name="context_builder",
            approved_agent_state=WorkflowStatusEnum.NOT_STARTED,
            toolset=context_builder_components["toolset"],
        )

        context_builder_approval_entry_node = context_builder_approval_component.attach(
            graph=graph,
            next_node="build_context_tools",
            back_node="build_context",
            exit_node="plan_terminator",
        )

        graph.add_conditional_edges(
            "build_context",
            partial(_router, "context_builder", tools_registry),
            {
                Routes.CALL_TOOL: "build_context_tools",
                Routes.TOOLS_APPROVAL: context_builder_approval_entry_node,
                Routes.HANDOVER: "build_context_handover",
                Routes.SUPERVISOR: "build_context_supervisor",
                Routes.STOP: "plan_terminator",
            },
        )
        graph.add_conditional_edges(
            "build_context_tools",
            _should_continue,
            {
                Routes.BUILD_CONTEXT: "build_context",
                Routes.STOP: "plan_terminator",
            },
        )

        graph.add_edge("build_context_supervisor", "build_context")
        return "build_context_handover"
