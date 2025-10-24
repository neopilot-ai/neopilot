from __future__ import annotations

from typing import Any, Optional, Type

from contract import contract_pb2
from neoai_workflow_service.executor.action import _execute_action
from neoai_workflow_service.tools.neoai_base_tool import NeoaiBaseTool
from pydantic import BaseModel, Field


class GitCommandInput(BaseModel):
    repository_url: str = Field(description="Http git remote url")
    command: str = Field(description="Git command to run")
    args: Optional[str] = Field(description="Git command arguments, leave empty if none", default=None)


class Command(NeoaiBaseTool):
    name: str = "run_git_command"
    description: str = """Runs a git command in the repository working directory."""
    args_schema: Type[BaseModel] = GitCommandInput  # type: ignore

    async def _execute(self, repository_url: str, command: str, args: Optional[str] = None) -> str:
        return await _execute_action(
            self.metadata,  # type: ignore
            contract_pb2.Action(
                runGitCommand=contract_pb2.RunGitCommand(command=command, arguments=args, repository_url=repository_url)
            ),
        )

    def format_display_message(self, git_command_args: GitCommandInput, _tool_response: Any = None) -> str:
        return f"Run git command: git {git_command_args.command} {git_command_args.args} in repository"
