"""Agentic mock model that allows responses to be specified in the request. The model will extract responses and tool
calls from tags, enabling multi-node graph execution.

Usage examples:
    Basic response:
    "Summarize https://gitlab.com/example-issue. <response>Here is the summary: The issue discusses...</response>"

    Multi-node workflow with tool calls (must be an array):
    "Analyze the issue.
    <response>
        I need to search for more info then I'll provide analysis.
        <tool_calls>[{"name": "search", "args": {"query": "issue details"}}]</tool_calls>
    </response>"

    Sequential responses for multiple agent calls:
    "Do complex task.
    <responses>
        <response>I'll start by gathering information. <tool_calls>[{"name": "get_info"}]</tool_calls></response>
        <response>Based on the info, here's my analysis...</response>
    </responses>"

    Response with latency simulation:
    "<response latency_ms='500'>This response will be delayed by 500ms</response>"
"""

import asyncio
import json
import re
from typing import Any, NamedTuple, Optional

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.outputs import ChatGeneration, ChatResult


class Response(NamedTuple):
    content: str
    tool_calls: list[ToolCall]
    latency_ms: int


class ResponseHandler:
    """Handles parsing and state management for scripted responses."""

    def __init__(self, messages: list[BaseMessage]):
        self.content = self._get_user_input(messages)
        self.responses: list[Response] = self._parse_all_responses() if self.content else []
        self.current_index = 0

    def _get_user_input(self, messages: list[BaseMessage]) -> Optional[str]:
        if not messages:
            return None

        user_message = next((msg for msg in messages if isinstance(msg, HumanMessage)), None)

        if not user_message or not user_message.content:
            return None

        return user_message.text()

    def _parse_all_responses(self) -> list[Response]:
        """Parse all defined responses from the user input content return as a list."""
        assert self.content is not None

        # Pattern to capture response tags with optional attributes and content
        # <response            - opening tag
        # (?:\s+([^>]*))?      - optional non-capturing group for attributes:
        #   \s+
        #   ([^>]*)            - capture group 1: any chars except '>' (attributes)
        #   ?
        # \s*>                 - optional whitespace then closing '>'
        # (.*?)                - capture group 2: response content (non-greedy)
        # </response>          - closing tag
        response_pattern = r"<response(?:\s+([^>]*))?\s*>(.*?)</response>"
        matches = re.findall(response_pattern, self.content, re.DOTALL | re.IGNORECASE)

        parsed_responses = []
        for attributes_str, response_text in matches:
            response_text = response_text.strip()
            clean_content, tool_calls = self._extract_tools_from_response(response_text)
            latency_ms = self._extract_latency_from_attributes(attributes_str)

            parsed_responses.append(Response(clean_content, tool_calls, latency_ms))

        return parsed_responses if parsed_responses else [Response("mock response (no response tag specified)", [], 0)]

    def _extract_tools_from_response(self, response_text: str) -> tuple[str, list[ToolCall]]:
        tool_calls: list[ToolCall] = []

        tool_pattern = r"<tool_calls>(.*?)</tool_calls>"
        tool_matches = re.findall(tool_pattern, response_text, re.DOTALL | re.IGNORECASE)

        for tool_match in tool_matches:
            try:
                tools_json = json.loads(tool_match.strip())
                if not isinstance(tools_json, list):
                    raise ValueError(
                        f"Tool calls must be an array, got {type(tools_json).__name__}: {tool_match.strip()}"
                    )

                for tool in tools_json:
                    if not isinstance(tool, dict):
                        raise ValueError(f"Each tool call must be an object, got {type(tool).__name__}: {tool}")
                    if "name" not in tool:
                        raise ValueError(f"Tool call missing required 'name' field: {tool}")

                    tool_call: ToolCall = {
                        "name": tool["name"],
                        "args": tool.get("args", {}),
                        "id": f"call_{len(tool_calls) + 1}",
                        "type": "tool_call",
                    }
                    tool_calls.append(tool_call)

            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in tool_calls: {tool_match.strip()}") from e

        clean_response = re.sub(tool_pattern, "", response_text, flags=re.DOTALL | re.IGNORECASE)
        clean_response = clean_response.strip()

        return clean_response, tool_calls

    def _extract_latency_from_attributes(self, attributes_str: str) -> int:
        if not attributes_str:
            return 0

        # Pattern to extract latency_ms attribute value
        # latency_ms           - literal match for attribute name
        # \s*=\s*              - equals sign with optional whitespace
        # ['\"]?               - optional single or double quote
        # (\d+)                - capture group: one or more digits (the value)
        # ['\"]?               - optional closing quote (matches opening quote type)
        latency_pattern = r"latency_ms\s*=\s*['\"]?(\d+)['\"]?"
        match = re.search(latency_pattern, attributes_str, re.IGNORECASE)

        if match:
            return int(match.group(1))

        return 0

    def get_next_response(self) -> Response:
        """Get the next response in sequence, returning empty response when exhausted."""
        if not self.content:
            return Response(
                "mock response (no response tag specified)",
                [],
                0,
            )

        if self.current_index >= len(self.responses):
            return Response("mock response (all scripted responses exhausted)", [], 0)

        response = self.responses[self.current_index]
        self.current_index += 1
        return response


class AgenticFakeModel(BaseChatModel):
    """Mock model for agentic workflows that extracts responses and tool calls from tags in the input.

    Supports:
    - Basic responses: <response>text</response>
    - Tool calls for multi-node execution: <tool_calls>[{"name": "tool", "args": {}}]</tool_calls>
    - Sequential responses: multiple <response> tags in order
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._response_handler: Optional[ResponseHandler] = None

    @property
    def _is_agentic_mock_model(self) -> bool:
        return True

    @property
    def _llm_type(self) -> str:
        return "agentic-fake-provider"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model": "agentic-fake-model"}

    async def _generate_with_latency(self, messages: list[BaseMessage]) -> ChatResult:
        if self._response_handler is None:
            self._response_handler = ResponseHandler(messages)

        response = self._response_handler.get_next_response()

        if response.latency_ms > 0:
            await asyncio.sleep(response.latency_ms / 1000.0)

        ai_message = AIMessage(
            content=response.content,
            tool_calls=response.tool_calls if response.tool_calls else [],
        )

        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs,
    ) -> ChatResult:
        return asyncio.run(self._generate_with_latency(messages))

    def bind_tools(self, *_args: Any, **_kwargs: Any) -> Any:
        return self

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        return await self._generate_with_latency(messages)
