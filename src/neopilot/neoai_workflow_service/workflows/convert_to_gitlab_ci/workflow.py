# pylint: disable=too-many-return-statements,unused-argument

import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from langgraph.checkpoint.memory import BaseCheckpointSaver
from langgraph.graph import END, StateGraph

from neoai_workflow_service.agents import HandoverAgent, RunToolNode, ToolsExecutor
from neoai_workflow_service.components import ToolsRegistry
from neoai_workflow_service.entities import (
    MAX_SINGLE_MESSAGE_TOKENS,
    MessageTypeEnum,
    Plan,
    ToolStatus,
    UiChatLog,
    WorkflowState,
    WorkflowStatusEnum,
)
from neoai_workflow_service.token_counter.approximate_token_counter import (
    ApproximateTokenCounter,
)
from neoai_workflow_service.tracking import log_exception
from neoai_workflow_service.workflows.abstract_workflow import (
    RECURSION_LIMIT,
    AbstractWorkflow,
)
from neoai_workflow_service.workflows.type_definitions import AdditionalContext
from lib.internal_events.event_enum import CategoryEnum

AGENT_NAME = "ci_pipelines_manager_agent"


# ROUTERS
class Routes(StrEnum):
    CONTINUE = "continue"
    END = "end"
    AGENT = "agent"
    COMMIT_CHANGES = "commit_changes"


def _router(state: WorkflowState) -> str:
    if state["status"] == WorkflowStatusEnum.CANCELLED:
        return Routes.END

    agent_messages = state["conversation_history"].get(AGENT_NAME, [])
    if not agent_messages or len(agent_messages) < 2:
        return Routes.END

    tool_calls = getattr(agent_messages[-2], "tool_calls", [])
    if len(tool_calls) == 0:
        return Routes.END

    tool_name = tool_calls[0].get("name")

    if tool_name == "read_file":
        return Routes.AGENT

    if tool_name == "ci_linter":
        last_msg = str(agent_messages[-1].content) if agent_messages else ""
        try:
            result = json.loads(last_msg)
        except (json.JSONDecodeError, TypeError) as e:
            log_exception(
                e,
                extra={
                    "tool_name": "ci_linter",
                    "last_msg": last_msg,
                    "error_type": "json_parsing_error",
                },
            )
            return Routes.AGENT

        if result.get("valid") is True:
            return Routes.COMMIT_CHANGES

        validation_count = len(
            [
                msg
                for msg in agent_messages
                if hasattr(msg, "tool_calls")
                and msg.tool_calls
                and any(call.get("name") == "ci_linter" for call in msg.tool_calls)
            ]
        )

        if validation_count >= 3:
            return Routes.COMMIT_CHANGES

        return Routes.AGENT

    if tool_name == "create_file_with_contents":
        create_count = len(
            [
                msg
                for msg in agent_messages
                if hasattr(msg, "tool_calls")
                and msg.tool_calls
                and any(call.get("name") == "create_file_with_contents" for call in msg.tool_calls)
            ]
        )

        if create_count >= 3:
            return Routes.COMMIT_CHANGES

        return Routes.AGENT

    return Routes.END


def _tools_execution_requested(state: WorkflowState) -> str:
    if state["status"] == WorkflowStatusEnum.CANCELLED:
        return Routes.END

    agent_messages = state["conversation_history"].get(AGENT_NAME, [])
    if agent_messages and getattr(agent_messages[-1], "tool_calls", []):
        return Routes.CONTINUE

    return Routes.END


def _git_output(command_output: list[str], state: WorkflowState):
    logs: list[UiChatLog] = [
        UiChatLog(
            message_type=MessageTypeEnum.TOOL,
            message_sub_type=None,
            content=f"{command_output[-1]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=ToolStatus.SUCCESS,
            correlation_id=None,
            tool_info=None,
            additional_context=None,
        )
    ]

    return {
        "ui_chat_log": logs,
    }


class Workflow(AbstractWorkflow):
    async def _handle_workflow_failure(self, error: BaseException, compiled_graph: Any, graph_config: Any):
        log_exception(error, extra={"workflow_id": self._workflow_id, "source": __name__})

    def _recursion_limit(self):
        return RECURSION_LIMIT

    def _compile(
        self,
        goal: str,
        tools_registry: ToolsRegistry,
        checkpointer: BaseCheckpointSaver,
    ):
        graph = StateGraph(WorkflowState)

        # Setup workflow graph
        graph = self._setup_workflow_graph(
            graph,
            tools_registry,
            goal,
        )

        return graph.compile(checkpointer=checkpointer)

    def _load_file_contents(self, file_contents: list[str], state: WorkflowState):
        content = file_contents[0]
        if not file_contents or "Error running tool: unable to open file:" in content:
            raise RuntimeError("Failed to load file contents, ensure that file is present")

        if ApproximateTokenCounter(AGENT_NAME).count_string_content(content) > MAX_SINGLE_MESSAGE_TOKENS:
            return {
                "ui_chat_log": [
                    UiChatLog(
                        message_type=MessageTypeEnum.TOOL,
                        message_sub_type=None,
                        content="File too large, skipping.",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        status=ToolStatus.FAILURE,
                        correlation_id=None,
                        tool_info=None,
                        additional_context=None,
                    )
                ],
                "status": WorkflowStatusEnum.EXECUTION,
            }

        return {
            "additional_context": [AdditionalContext(category="file", content=content)],
            "ui_chat_log": [
                UiChatLog(
                    message_type=MessageTypeEnum.TOOL,
                    message_sub_type=None,
                    content="Loaded Jenkins file",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    status=ToolStatus.SUCCESS,
                    correlation_id=None,
                    tool_info=None,
                    additional_context=None,
                )
            ],
            "status": WorkflowStatusEnum.EXECUTION,
        }

    def _setup_translator_nodes(self, tools_registry: ToolsRegistry):
        translator_agent: Any
        translation_tools = ["create_file_with_contents", "read_file", "ci_linter"]
        agents_toolset = tools_registry.toolset(translation_tools)

        translator_agent = self._prompt_registry.get_on_behalf(
            self._user,
            "workflow/convert_to_gitlab_ci",
            "^1.0.0",
            tools=agents_toolset.bindable,  # type: ignore[arg-type]
            workflow_id=self._workflow_id,
            workflow_type=CategoryEnum.WORKFLOW_CONVERT_TO_GITLAB_CI,
            http_client=self._http_client,
        )

        return {
            "agent": translator_agent,
            "tools": translation_tools,
            "tools_executor": ToolsExecutor(
                tools_agent_name=AGENT_NAME,
                toolset=agents_toolset,
                workflow_id=self._workflow_id,
                workflow_type=CategoryEnum.WORKFLOW_CONVERT_TO_GITLAB_CI,
            ),
            "start_node": "request_translation",
        }

    def get_source_branch(self):
        if not self._additional_context:
            return None

        for context in self._additional_context:
            if context.category == "agent_user_environment" and context.content:
                try:
                    content_data = json.loads(context.content)
                    return content_data.get("source_branch")
                except (json.JSONDecodeError, TypeError):
                    continue
        return None

    def _setup_workflow_graph(
        self,
        graph: StateGraph,
        tools_registry,
        ci_config_file_path,
    ):
        translator_components = self._setup_translator_nodes(tools_registry)

        self.log.info("Starting %s workflow graph compilation", self._workflow_type)
        graph.set_entry_point("load_files")

        # Load jenkins file contents
        graph.add_node(
            "load_files",
            RunToolNode[WorkflowState](
                tool=tools_registry.get("read_file"),  # type: ignore
                input_parser=lambda _: [{"file_path": ci_config_file_path}],
                output_parser=self._load_file_contents,  # type: ignore
                flow_type=self._workflow_type,
            ).run,
        )
        # translator nodes
        graph.add_node(translator_components["start_node"], translator_components["agent"].run)
        graph.add_node("execution_tools", translator_components["tools_executor"].run)

        source_branch = self.get_source_branch()
        merge_request_target = ""
        if source_branch:
            merge_request_target = f"-o merge_request.target={source_branch}"

        # deterministic git actions
        graph.add_node(
            "git_actions",
            RunToolNode[WorkflowState](
                tool=tools_registry.get("run_git_command"),  # type: ignore
                input_parser=lambda _: [
                    {
                        "repository_url": (self._project["http_url_to_repo"]),  # type: ignore[index]
                        "command": "add",
                        "args": "-A",
                    },
                    {
                        "repository_url": (self._project["http_url_to_repo"]),  # type: ignore[index]
                        "command": "commit",
                        "args": "-m 'Neoai Agent: Convert to GitLab CI'",
                    },
                    {
                        "repository_url": (self._project["http_url_to_repo"]),  # type: ignore[index]
                        "command": "push",
                        "args": f"-o merge_request.create "
                        f"-o merge_request.title='Neoai Agent: Convert to GitLab CI' "
                        f"-o merge_request.description='Created by Neoai Agent, session: {self._workflow_id}' "
                        f"{merge_request_target}",
                    },
                ],
                output_parser=_git_output,  # type: ignore
                flow_type=self._workflow_type,
            ).run,
        )

        graph.add_node(
            "complete",
            HandoverAgent(new_status=WorkflowStatusEnum.COMPLETED, handover_from=AGENT_NAME).run,
        )

        graph.add_edge("load_files", translator_components["start_node"])
        graph.add_conditional_edges(
            translator_components["start_node"],
            _tools_execution_requested,
            {
                Routes.CONTINUE: "execution_tools",
                Routes.END: "complete",
            },
        )
        graph.add_conditional_edges(
            "execution_tools",
            _router,
            {
                Routes.AGENT: translator_components["start_node"],
                Routes.END: "complete",
                Routes.COMMIT_CHANGES: "git_actions",
            },
        )
        graph.add_edge("git_actions", "complete")
        graph.add_edge("complete", END)
        return graph

    def get_workflow_state(self, goal: str) -> WorkflowState:
        target_file = goal
        initial_ui_chat_log = UiChatLog(
            message_type=MessageTypeEnum.TOOL,
            message_sub_type=None,
            content=f"Starting Jenkinsfile translation workflow from file: {target_file}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=ToolStatus.SUCCESS,
            correlation_id=None,
            tool_info=None,
            additional_context=None,
        )

        return WorkflowState(
            status=WorkflowStatusEnum.NOT_STARTED,
            ui_chat_log=[initial_ui_chat_log],
            conversation_history={},
            plan=Plan(steps=[]),
            handover=[],
            last_human_input=None,
            project=self._project,
            goal=goal,
            additional_context=None,
        )
