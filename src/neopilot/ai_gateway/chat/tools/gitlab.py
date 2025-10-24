from textwrap import dedent
from typing import Optional

from gitlab_cloud_connector import GitLabUnitPrimitive

from neopilot.ai_gateway.chat.tools.base import BaseRemoteTool

__all__ = [
    "CommitReader",
    "MergeRequestReader",
    "IssueReader",
    "GitlabDocumentation",
    "SelfHostedGitlabDocumentation",
    "EpicReader",
    "BuildReader",
    "WorkItemReader",
]


class IssueReader(BaseRemoteTool):
    name: str = "issue_reader"
    resource: str = "issues"
    unit_primitive: GitLabUnitPrimitive = GitLabUnitPrimitive.ASK_ISSUE
    min_required_gl_version: Optional[str] = None

    description: str = dedent(
        # editorconfig-checker-disable
        """\
        This tool retrieves the content of a specific issue
        ONLY if the user question fulfills the strict usage conditions below.

        **Strict Usage Conditions:**
        * **Condition 1: Issue ID Provided:** This tool MUST be used ONLY when the user provides a valid issue ID.
        * **Condition 2: Issue URL Context:** This tool MUST be used ONLY when the user is actively viewing a specific
          issue URL or a specific URL is provided by the user.

        **Do NOT** attempt to search for or identify issues based on descriptions, keywords, or user questions.

        **Action Input:**
        * The original question asked by the user.

        **Important:**  Reject any input that does not strictly adhere to the usage conditions above.
        Return a message stating you are unable to search for issues without a valid identifier."""
        # editorconfig-checker-enable
    )

    example: str = dedent(
        # editorconfig-checker-disable
        """\
        Question: Please identify the author of #123 issue
        Thought: You have access to the same resources as user who asks a question.
          Question is about the content of an issue, so you need to use "issue_reader" tool to retrieve and read issue.
          Based on this information you can present final answer about issue.
        Action: issue_reader
        Action Input: Please identify the author of #123 issue"""
        # editorconfig-checker-enable
    )


class WorkItemReader(BaseRemoteTool):
    name: str = "work_item_reader"
    resource: str = "work_items"
    unit_primitive: GitLabUnitPrimitive = GitLabUnitPrimitive.ASK_WORK_ITEM
    min_required_gl_version: Optional[str] = None

    description: str = dedent(
        """\
        This tool retrieves the content of a specific work items
        ONLY if the user question fulfills the strict usage conditions below.

        **Strict Usage Conditions:**
        * **Condition 1: Work item ID Provided:** This tool MUST be used ONLY when the user provides a valid work item
        ID.
        * **Condition 2: Work item URL Context:** This tool MUST be used ONLY when the user is actively viewing a
        specific work item URL or a specific URL is provided by the user.

        **Do NOT** attempt to search for or identify work items based on descriptions, keywords, or user questions.

        **Action Input:**
        * The original question asked by the user.

        **Important:**  Reject any input that does not strictly adhere to the usage conditions above.
        Return a message stating you are unable to search for work items without a valid identifier."""
    )

    example: str = dedent(
        """\
        Question: Please identify the author of https://some.host.name/some/long/path/-/work_items/410692
        Thought: You have access to the same resources as user who asks a question.
        Question is about the content of a work item, so you need to use "work_item_reader" tool to retrieve and read
        work item. Based on this information you can present final answer about work item.
        Action: work_item_reader
        Action Input: Please identify the author of https://some.host.name/some/long/path/-/work_items/410692"""
    )


class GitlabDocumentation(BaseRemoteTool):
    name: str = "gitlab_documentation"
    resource: str = "documentation answers"
    unit_primitive: GitLabUnitPrimitive = GitLabUnitPrimitive.DOCUMENTATION_SEARCH
    min_required_gl_version: Optional[str] = None

    description: str = dedent(
        """\
        This tool is beneficial when you need to answer questions concerning GitLab and its features.
        Questions can be about GitLab's projects, groups, issues, merge requests,
        epics, work items, milestones, labels, CI/CD pipelines, git repositories, and more."""
    )

    example: str = dedent(
        """\
        Question: How do I set up a new project?
        Thought: Question is about inner working of GitLab. "gitlab_documentation" tool is the right one for the job.
        Action: gitlab_documentation
        Action Input: How do I set up a new project?"""
    )


class SelfHostedGitlabDocumentation(BaseRemoteTool):
    name: str = "gitlab_documentation"
    resource: str = "documentation answers"
    unit_primitive: GitLabUnitPrimitive = GitLabUnitPrimitive.DOCUMENTATION_SEARCH
    min_required_gl_version: Optional[str] = None

    description: str = dedent(
        """\
        This tool is beneficial when you need to answer questions concerning GitLab and its features.
        Questions can be about GitLab's projects, groups, issues, merge requests,
        epics, work items, milestones, labels, CI/CD pipelines, git repositories, and more."""
    )

    example: str = dedent(
        # editorconfig-checker-disable
        """
        Question: How do I set up a new project?
        Thought: Question is about inner working of GitLab. "gitlab_documentation" tool is the right one for the job. I
          should keep the action input concise to it's intention and do not add punctuation, for example when question
          is 'How do I set up a project?' then Action Input is 'set up project' nad when question is 'Can you please
          help me open a merge request?' then Action Input is 'create merge request'.
        Action: gitlab_documentation
        Action Input: set up project
        """
        # editorconfig-checker-enable
    )


class EpicReader(BaseRemoteTool):
    name: str = "epic_reader"
    resource: str = "epics"
    unit_primitive: GitLabUnitPrimitive = GitLabUnitPrimitive.ASK_EPIC
    min_required_gl_version: Optional[str] = None

    description: str = dedent(
        # editorconfig-checker-disable
        # pylint: disable=line-too-long
        """\
        This tool retrieves the content of a specific epic or work item.
        ONLY if the user question fulfills the strict usage conditions below.

        **Strict Usage Conditions:**
        * **Condition 1: epic ID Provided:** This tool MUST be used ONLY when the user provides a valid epic or work
          item ID.
        * **Condition 2: epic URL Context:** This tool MUST be used ONLY when the user is actively viewing
          a specific epic or work item URL or a specific URL is provided by the user.

        **Do NOT** attempt to search for or identify epics or work items based on descriptions, keywords, or user
        questions.

        **Action Input:**
        * The original question asked by the user.

        **Important:**  Reject any input that does not strictly adhere to the usage conditions above.
        Return a message stating you are unable to search for epics or work items without a valid identifier."""
        # editorconfig-checker-enable
    )

    example: str = dedent(
        """\
        Question: Please identify the author of &123 epic.
        Thought: You have access to the same resources as user who asks a question.
            The question is about an epic, so you need to use "epic_reader" tool.
            Based on this information you can present final answer.
        Action: epic_reader
        Action Input: Please identify the author of &123 epic."""
    )


class CommitReader(BaseRemoteTool):
    name: str = "commit_reader"
    resource: str = "commits"
    unit_primitive: GitLabUnitPrimitive = GitLabUnitPrimitive.ASK_COMMIT
    min_required_gl_version: Optional[str] = "17.5.0-pre"

    description: str = dedent(
        # editorconfig-checker-disable
        """\
        This tool retrieves the content of a specific commit
        ONLY if the user question fulfills the strict usage conditions below.

        **Strict Usage Conditions:**
        * **Condition 1: Commit ID Provided:** This tool MUST be used ONLY when the user provides a valid commit ID.
        * **Condition 2: Commit URL Context:** This tool MUST be used ONLY when the user is actively viewing
          a specific commit URL or a specific URL is provided by the user.

        **Do NOT** attempt to search for or identify commits based on descriptions, keywords, or user questions.

        **Action Input:**
        * The original question asked by the user.

        **Important:**  Reject any input that does not strictly adhere to the usage conditions above.
        Return a message stating you are unable to search for commits without a valid identifier."""
        # editorconfig-checker-enable
    )

    example: str = dedent(
        """\
        Question: Please identify the author of #123 commit
        Thought: You have access to the same resources as user who asks a question.
            Question is about the content of a commit, so you need to use "commit_reader" tool to retrieve
            and read commit.
            Based on this information you can present final answer about commit.
        Action: commit_reader
        Action Input: Please identify the author of #123 commit"""
    )


class BuildReader(BaseRemoteTool):
    name: str = "build_reader"
    resource: str = "builds"
    unit_primitive: GitLabUnitPrimitive = GitLabUnitPrimitive.ASK_BUILD
    min_required_gl_version: Optional[str] = "17.5.0-pre"

    description: str = dedent(
        # editorconfig-checker-disable
        # pylint: disable=line-too-long
        """\
        This tool retrieves the content of a specific build, also known as a job
        ONLY if the user question fulfills the strict usage conditions below.

        **Strict Usage Conditions:**
        * **Condition 1: build ID or job ID Provided:** This tool MUST be used ONLY when the user provides a valid build
        ID or job ID.
        * **Condition 2: build URL or job URL Context:** This tool MUST be used ONLY when the user is actively viewing
          a specific build URL/job URL or a specific URL is provided by the user.

        **Do NOT** attempt to search for or identify builds or jobs based on descriptions, keywords, or user questions.

        **Action Input:**
        * The original question asked by the user.

        **Important:**  Reject any input that does not strictly adhere to the usage conditions above.
        Return a message stating you are unable to search for builds or jobs without a valid identifier."""
        # editorconfig-checker-enable
    )

    example: str = dedent(
        """\
        Question: Explain the job https://some.host.name/some/long/path/-/jobs/:job_id.
        Thought: You have access to the same resources as user who asks a question.
            The question is about a build or a job, so you need to use "build_reader" tool.
            Based on this information you can present final answer.
        Action: build_reader
        Action Input: Explain the job https://some.host.name/some/long/path/-/jobs/:job_id."""
    )


class MergeRequestReader(BaseRemoteTool):
    name: str = "merge_request_reader"
    resource: str = "merge_requests"
    unit_primitive: GitLabUnitPrimitive = GitLabUnitPrimitive.ASK_MERGE_REQUEST
    min_required_gl_version: Optional[str] = "17.5.0-pre"

    description: str = dedent(
        # editorconfig-checker-disable
        # pylint: disable=line-too-long
        """\
        This tool retrieves the content of a specific merge request
        ONLY if the user question fulfills the strict usage conditions below.

        **Strict Usage Conditions:**
        * **Condition 1: Merge request ID Provided:** This tool MUST be used ONLY when the user provides a valid merge
          request ID.
        * **Condition 2: Merge request URL Context:** This tool MUST be used ONLY when the user is actively viewing
          a specific merge request URL or a specific URL is provided by the user.

        **Do NOT** attempt to search for or identify merge requests based on descriptions, keywords, or user questions.

        **Action Input:**
        * The original question asked by the user.

        **Important:**  Reject any input that does not strictly adhere to the usage conditions above.
        Return a message stating you are unable to search for merge requests without a valid identifier."""
        # editorconfig-checker-enable
    )

    example: str = dedent(
        # pylint: disable=line-too-long
        """\
        Question: Please identify the author of #123 merge request
        Thought: You have access to the same resources as user who asks a question.
            Question is about the content of a merge request, so you need to use "merge_request_reader" tool to retrieve
            and read merge request.
            Based on this information you can present final answer about merge request.
        Action: merge_request_reader
        Action Input: Please identify the author of #123 merge request"""
    )
