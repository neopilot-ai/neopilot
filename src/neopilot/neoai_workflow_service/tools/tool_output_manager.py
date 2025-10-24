import json
from textwrap import dedent
from typing import Any

import structlog
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from neoai_workflow_service.token_counter.approximate_token_counter import (
    ApproximateTokenCounter,
)

logger = structlog.get_logger("tools_executor")


TOOL_RESPONSE_MAX_BYTES = 100 * 1024  # 100 KiB
TOOL_RESPONSE_TRUNCATED_SIZE = 50 * 1024  # 50 KiB


token_counter = ApproximateTokenCounter("planner")


def _add_truncation_instruction(truncated_text: str, original_token_size: int, truncated_token_size: int) -> str:
    """Create a formatted truncation notice message."""
    percentage = (truncated_token_size / original_token_size) * 100
    return dedent(
        f"""
        <truncation_notice>
        IMPORTANT: This tool output has been truncated due to size limits.

        <truncation_details>
        - Original size: {original_token_size} tokens
        - Displayed size: {truncated_token_size} tokens
        - Percentage shown: {percentage:.1f}%
        </truncation_details>

        <truncated_tool_output>
        {truncated_text}
        </truncated_tool_output>

        <instructions>
        When generating a response based on truncated tool output, explicitly inform the user by including a note such as: "Note: This response is based on truncated tool output and may be incomplete."

        If you need information that might be in the missing portion, please try one of these actions:
        1. Refine your tool call to request a specific subset or filter the data
        2. Use alternative approaches to gather the necessary information
        </instructions>
        </truncation_notice>
        """
    )


def truncate_string(text: str, tool_name: str) -> str:
    """Truncate string > TOOL_RESPONSE_MAX_BYTES to TOOL_RESPONSE_TRUNCATED_SIZE."""
    encoded = text.encode("utf-8")

    if len(encoded) <= TOOL_RESPONSE_MAX_BYTES:
        return text

    truncated_text = encoded[:TOOL_RESPONSE_TRUNCATED_SIZE].decode("utf-8", errors="ignore")

    # Log token size to be consistent
    original_token_size = token_counter.count_string_content(text)
    truncated_token_size = token_counter.count_string_content(truncated_text)

    logger.info(
        "Tool response exceeds max size and will be truncated",
        tool_name=tool_name,
        original_token_size=original_token_size,
        truncated_token_size=truncated_token_size,
    )

    truncated_output = _add_truncation_instruction(
        truncated_text=truncated_text,
        original_token_size=original_token_size,
        truncated_token_size=truncated_token_size,
    )

    return truncated_output


def truncate_tool_response(tool_response: Any, tool_name: str) -> Any:
    """Truncate tool response if it exceeds token limit."""

    def convert_to_str(obj: Any) -> str:
        return obj if isinstance(obj, str) else json.dumps(obj)

    try:
        # Skip the Command objects
        if isinstance(tool_response, Command):
            logger.info("Skip truncation for Command tool response")
            return tool_response

        # Handle ToolMessage objects
        if isinstance(tool_response, ToolMessage):
            content_str = convert_to_str(tool_response.content)
            truncated_content = truncate_string(content_str, tool_name=tool_name)

            if truncated_content != content_str:
                new_response = tool_response.model_copy()
                new_response.content = truncated_content
                return new_response

            return tool_response

        # Handle string and other types
        response_str = convert_to_str(tool_response)
        truncated_str = truncate_string(response_str, tool_name=tool_name)

        return truncated_str if truncated_str != response_str else tool_response

    except Exception as e:
        logger.error(f"Abort tool response truncation due to unexpected error: {e}")
        return tool_response
