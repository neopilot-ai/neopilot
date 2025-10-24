from __future__ import annotations

import base64
import json
from typing import Any, List, Optional, Tuple, Type
from urllib.parse import quote

import structlog
from neoai_workflow_service.gitlab.url_parser import (GitLabUrlParseError,
                                                      GitLabUrlParser)
from neoai_workflow_service.policies.file_exclusion_policy import \
    FileExclusionPolicy
from neoai_workflow_service.tools.gitlab_resource_input import \
    ProjectResourceInput
from neoai_workflow_service.tools.neoai_base_tool import NeoaiBaseTool
from pydantic import BaseModel, Field

log = structlog.stdlib.get_logger(__name__)


class RepositoryFileResourceInput(ProjectResourceInput):
    ref: Optional[str] = Field(
        default=None,
        description="The name of branch, tag or commit. Use HEAD to automatically use the default branch.",
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Full path to file, such as lib/class.rb.",
    )


class RepositoryFileBaseTool(NeoaiBaseTool):
    def _validate_repository_file_url(
        self,
        url: Optional[str],
        project_id: Optional[str],
        ref: Optional[str],
        file_path: Optional[str],
    ) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
        """Validate repository file URL and extract project_id, ref, and file_path.

        Args:
            url: The GitLab URL to parse
            project_id: The project ID provided by the user
            ref: The ref provided by the user
            file_path: The file path provided by the user

        Returns:
            Tuple containing:
                - The validated project_id (or None if validation failed)
                - The validated ref (or None if validation failed)
                - The validated file_path (or None if validation failed)
                - A list of error messages (empty if validation succeeded)
        """
        errors = []

        if not url:
            if not project_id:
                errors.append("'project_id' must be provided when 'url' is not")
            if not ref:
                errors.append("'ref' must be provided when 'url' is not")
            if not file_path:
                errors.append("'file_path' must be provided when 'url' is not")
            return project_id, ref, file_path, errors

        try:
            url_project_id, url_ref, url_file_path = GitLabUrlParser.parse_repository_file_url(url, self.gitlab_host)

            # If both URL and IDs are provided, check if they match
            if project_id is not None and str(project_id) != url_project_id:
                errors.append(f"Project ID mismatch: provided '{project_id}' but URL contains '{url_project_id}'")
            if ref is not None and ref != url_ref:
                errors.append(f"Ref mismatch: provided '{ref}' but URL contains '{url_ref}'")
            if file_path and file_path != url_file_path:
                errors.append(f"File path mismatch: provided '{file_path}' but URL contains '{url_file_path}'")

            # Use the values from the URL
            return url_project_id, url_ref, url_file_path, errors
        except GitLabUrlParseError as e:
            errors.append(f"Failed to parse URL: {str(e)}")
            return project_id, ref, file_path, errors


class GetRepositoryFile(RepositoryFileBaseTool):
    name: str = "get_repository_file"

    # editorconfig-checker-disable
    description: str = """Get the contents of a file from a remote repository.

    To identify a file you must provide either:
    - project_id, ref, and file_path parameters, or
    - A GitLab URL like:
      - https://gitlab.com/namespace/project/-/blob/master/README.md
      - https://gitlab.com/group/subgroup/project/-/blob/main/src/file.py
    """
    # editorconfig-checker-enable

    args_schema: Type[BaseModel] = RepositoryFileResourceInput  # type: ignore

    async def _execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        project_id = kwargs.get("project_id")
        ref = kwargs.get("ref")
        file_path = kwargs.get("file_path")

        project_id, ref, file_path, errors = self._validate_repository_file_url(url, project_id, ref, file_path)

        if errors:
            return json.dumps({"error": "; ".join(errors)})

        try:
            if file_path is None:
                return json.dumps({"error": "Missing file_path"})

            # Check file exclusion policy if project is available
            policy = FileExclusionPolicy(self.project)
            if file_path and not policy.is_allowed(file_path):
                return json.dumps({"error": FileExclusionPolicy.format_llm_exclusion_message([file_path])})

            encoded_file_path = quote(file_path, safe="")

            response = await self.gitlab_client.aget(
                path=f"/api/v4/projects/{project_id}/repository/files/{encoded_file_path}",
                params={"ref": ref},
                parse_json=True,
                use_http_response=True,
            )

            if not response.is_success():
                log.error(
                    "Get repository file request failed with status %s: %s",
                    response.status_code,
                    response.body,
                )
                return json.dumps({"error": response.body})

            content = base64.b64decode(response.body["content"]).decode("utf-8")

            return json.dumps({"content": content})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def format_display_message(self, args: RepositoryFileResourceInput, _tool_response: Any = None) -> str:
        # Check file exclusion policy for display message if project is available
        policy = FileExclusionPolicy(self.project)
        if args.file_path and not policy.is_allowed(args.file_path):
            return FileExclusionPolicy.format_user_exclusion_message([args.file_path])

        if args.url:
            return f"Get repository file content from {args.url}"
        return f"Get repository file {args.file_path} from project {args.project_id} at ref {args.ref}"


class RepositoryTreeResourceInput(ProjectResourceInput):
    path: Optional[str] = Field(
        default=None,
        description="Path inside repository. Used to get content of subdirectories",
    )
    ref: Optional[str] = Field(
        default=None,
        description="The name of a repository branch or tag or, if not given, the default branch",
    )
    recursive: Optional[bool] = Field(
        default=False,
        description="Boolean value for getting a recursive tree",
    )
    page: Optional[int] = Field(
        default=1,
        description="Page number for pagination (min 1)",
        ge=1,
    )
    per_page: Optional[int] = Field(
        default=20,
        description="Results per page for pagination (min 1, max 100)",
        ge=1,
        le=100,
    )


class ListRepositoryTree(NeoaiBaseTool):
    name: str = "list_repository_tree"
    description: str = """List files and directories in a GitLab repository.

    To identify a project you must provide either:
    - project_id parameter, or
    - A GitLab URL like:
        - https://gitlab.com/namespace/project
        - https://gitlab.com/group/subgroup/project

    You can specify a path to get contents of a subdirectory, a specific ref (branch/tag),
    and whether to get a recursive tree.

    For example:
    - Given project_id 13, the tool call would be:
        list_repository_tree(project_id=13)
    - To list files in a specific subdirectory with a specific branch:
        list_repository_tree(project_id=13, path="src", ref="main")
    - To recursively list all files in a project:
        list_repository_tree(project_id=13, recursive=True)
    """
    args_schema: Type[BaseModel] = RepositoryTreeResourceInput  # type: ignore

    async def _execute(self, **kwargs) -> str:
        url = kwargs.get("url")
        project_id = kwargs.get("project_id")

        project_id, errors = self._validate_project_url(url, project_id)

        if errors:
            return json.dumps({"error": "; ".join(errors)})

        params = {}
        optional_params = ["path", "ref", "page", "per_page"]
        for param in optional_params:
            if param in kwargs and kwargs[param] is not None:
                params[param] = kwargs[param]

        recursive = kwargs.get("recursive", None)
        if recursive is not None:
            params["recursive"] = str(recursive).lower()

        try:
            response = await self.gitlab_client.aget(
                path=f"/api/v4/projects/{project_id}/repository/tree",
                params=params,
                use_http_response=True,
            )

            if not response.is_success():
                log.error(
                    "List repository tree request failed with status %s: %s",
                    response.status_code,
                    response.body,
                )
                return json.dumps(response.body)

            # Filter results based on file exclusion policy
            policy = FileExclusionPolicy(self.project)

            # Extract file paths from the response objects
            file_paths: List[str] = [
                item.get("path", "") for item in response.body if isinstance(item.get("path"), str)
            ]
            allowed_paths, _excluded_paths = policy.filter_allowed(file_paths)

            # Filter the original response to only include allowed items
            filtered_response = [item for item in response.body if item.get("path") in allowed_paths]

            return json.dumps({"tree": filtered_response})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def format_display_message(self, args: RepositoryTreeResourceInput, _tool_response: Any = None) -> str:
        path_str = f" in path '{args.path}'" if args.path else ""
        ref_str = f" at ref '{args.ref}'" if args.ref else ""
        recursive_str = " recursively" if args.recursive else ""

        if args.url:
            return f"List repository tree{recursive_str}{path_str}{ref_str} from {args.url}"
        return f"List repository tree{recursive_str}{path_str}{ref_str} in project {args.project_id}"
