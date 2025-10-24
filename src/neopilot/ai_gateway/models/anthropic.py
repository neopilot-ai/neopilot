from enum import StrEnum
from typing import Any, AsyncIterator, Callable, Optional, Union

import httpx
import structlog
from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    AsyncStream,
)
from anthropic._types import NOT_GIVEN
from anthropic.types import Completion, ContentBlockDeltaEvent
from anthropic.types import Message as AnthropicMessage

from neopilot.ai_gateway.models.base import (
    KindModelProvider,
    ModelAPICallError,
    ModelAPIError,
    ModelMetadata,
)
from neopilot.ai_gateway.models.base_chat import ChatModelBase, Message, Role
from neopilot.ai_gateway.models.base_text import (
    TextGenModelBase,
    TextGenModelChunk,
    TextGenModelOutput,
)
from neopilot.ai_gateway.safety_attributes import SafetyAttributes

__all__ = [
    "AnthropicAPIConnectionError",
    "AnthropicAPIStatusError",
    "AnthropicAPITimeoutError",
    "AnthropicModel",
    "AnthropicChatModel",
    "KindAnthropicModel",
]

log = structlog.stdlib.get_logger("codesuggestions")


class AnthropicAPIConnectionError(ModelAPIError):
    @classmethod
    def from_exception(cls, ex: APIConnectionError):
        wrapper = cls(ex.message, errors=(ex,))

        return wrapper


class AnthropicAPIStatusError(ModelAPICallError):
    @classmethod
    def from_exception(cls, ex: APIStatusError):
        cls.code = ex.status_code
        wrapper = cls(ex.message, errors=(ex,))

        return wrapper


class AnthropicAPITimeoutError(ModelAPIError):
    @classmethod
    def from_exception(cls, ex: APITimeoutError):
        wrapper = cls(ex.message, errors=(ex,))

        return wrapper


class KindAnthropicModel(StrEnum):
    # Avoid using model versions that only specify the major version number.
    # More info - https://docs.anthropic.com/claude/reference/selecting-a-model
    CLAUDE_2_1 = "claude-2.1"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20240620"
    CLAUDE_3_5_SONNET_VERTEX = "claude-3-5-sonnet@20240620"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
    CLAUDE_3_5_SONNET_V2 = "claude-3-5-sonnet-20241022"
    CLAUDE_3_5_SONNET_V2_VERTEX = "claude-3-5-sonnet-v2@20241022"
    CLAUDE_3_7_SONNET = "claude-3-7-sonnet-20250219"
    CLAUDE_3_7_SONNET_VERTEX = "claude-3-7-sonnet@20250219"
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
    CLAUDE_SONNET_4_VERTEX = "claude-sonnet-4@20250514"
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"


class AnthropicModel(TextGenModelBase):
    """This class uses the deprecated Completions API from Anthropic. Claude models v3 and above should use
    AnthropicChatModel.

    Ref: https://docs.anthropic.com/claude/reference/migrating-from-text-completions-to-messages
    """

    # Ref: https://docs.anthropic.com/claude/reference/versioning
    DEFAULT_VERSION = "2023-06-01"

    OPTS_CLIENT = {
        "default_headers": {},
        "max_retries": 1,
    }

    OPTS_MODEL = {
        "timeout": httpx.Timeout(30.0, connect=5.0),
        "max_tokens_to_sample": 2048,
        "stop_sequences": NOT_GIVEN,
        "temperature": 0.2,
        "top_k": NOT_GIVEN,
        "top_p": NOT_GIVEN,
    }

    def __init__(
        self,
        client: AsyncAnthropic,
        version: str = DEFAULT_VERSION,
        model_name: str = KindAnthropicModel.CLAUDE_3_5_SONNET_V2.value,
        **kwargs: Any,
    ):
        client_opts = self._obtain_client_opts(version, **kwargs)

        self.client = client.with_options(**client_opts)
        self.model_opts = self._obtain_model_opts(**kwargs)

        self._metadata = ModelMetadata(
            name=model_name,
            engine=KindModelProvider.ANTHROPIC.value,
        )

    @staticmethod
    def _obtain_model_opts(**kwargs: Any):
        return _obtain_opts(AnthropicModel.OPTS_MODEL, **kwargs)

    @staticmethod
    def _obtain_client_opts(version: str, **kwargs: Any):
        opts = _obtain_opts(AnthropicModel.OPTS_CLIENT, **kwargs)

        headers = opts["default_headers"]
        if not headers.get("anthropic-version", None):
            headers["anthropic-version"] = version

        return opts

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    @property
    def input_token_limit(self) -> int:
        # Ref: https://docs.anthropic.com/en/docs/about-claude/models#legacy-model-comparison
        return 100_000

    async def generate(
        self,
        prefix: str,
        suffix: Optional[str] = "",
        stream: bool = False,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[float] = None,
        **kwargs: Any,
    ) -> Union[TextGenModelOutput, list[TextGenModelOutput], AsyncIterator[TextGenModelChunk]]:
        default_values = {
            **{
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "max_output_tokens": max_output_tokens,
            },
            **kwargs,
        }
        opts = _obtain_opts(self.model_opts, **default_values)

        log.debug("codegen anthropic call:", **opts)

        with self.instrumentator.watch(stream=stream) as watcher:
            try:
                suggestion = await self.client.completions.create(
                    model=self.metadata.name,
                    prompt=prefix,
                    stream=stream,
                    **opts,
                )
            except APIStatusError as ex:
                raise AnthropicAPIStatusError.from_exception(ex)
            except APITimeoutError as ex:
                raise AnthropicAPITimeoutError.from_exception(ex)
            except APIConnectionError as ex:
                raise AnthropicAPIConnectionError.from_exception(ex)

            if stream:
                return self._handle_stream(suggestion, watcher.finish)

        completion_text = getattr(suggestion, "completion", "")
        return TextGenModelOutput(
            text=completion_text,
            # Give a high value, the model doesn't return scores.
            score=10**5,
            safety_attributes=SafetyAttributes(),
        )

    async def _handle_stream(self, response, after_callback: Callable) -> AsyncIterator[TextGenModelChunk]:
        try:
            async for event in response:
                if isinstance(event, AsyncStream):
                    async for comp in event:
                        yield TextGenModelChunk(text=comp.completion)
                elif isinstance(event, Completion):
                    yield TextGenModelChunk(text=event.completion)
        finally:
            after_callback()

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindAnthropicModel],
        client: AsyncAnthropic,
        **kwargs: Any,
    ):
        try:
            kind_model = KindAnthropicModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(client, model_name=kind_model.value, **kwargs)


class AnthropicChatModel(ChatModelBase):
    # Ref: https://docs.anthropic.com/claude/reference/versioning
    DEFAULT_VERSION = "2023-06-01"

    OPTS_CLIENT = {
        "default_headers": {},
        "max_retries": 1,
    }

    OPTS_MODEL = {
        "timeout": httpx.Timeout(30.0, connect=5.0),
        "max_tokens": 4096,
        "stop_sequences": NOT_GIVEN,
        "temperature": 0.2,
        "top_k": NOT_GIVEN,
        "top_p": NOT_GIVEN,
    }

    def __init__(
        self,
        client: AsyncAnthropic,
        version: str = DEFAULT_VERSION,
        model_name: str = KindAnthropicModel.CLAUDE_3_HAIKU.value,
        **kwargs: Any,
    ):
        client_opts = self._obtain_client_opts(version, **kwargs)

        self.client = client.with_options(**client_opts)
        self.model_opts = self._obtain_model_opts(**kwargs)

        self._metadata = ModelMetadata(
            name=model_name,
            engine=KindModelProvider.ANTHROPIC.value,
        )

    @staticmethod
    def _obtain_model_opts(**kwargs: Any):
        return _obtain_opts(AnthropicChatModel.OPTS_MODEL, **kwargs)

    @staticmethod
    def _obtain_client_opts(version: str, **kwargs: Any):
        opts = _obtain_opts(AnthropicChatModel.OPTS_CLIENT, **kwargs)

        headers = opts["default_headers"]
        if not headers.get("anthropic-version", None):
            headers["anthropic-version"] = version

        return opts

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    @property
    def input_token_limit(self) -> int:
        # Ref: https://docs.anthropic.com/claude/docs/models-overview#model-comparison
        return 200_000

    async def generate(
        self,
        messages: list[Message],
        stream: bool = False,
        temperature: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        **kwargs: Any,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:

        default_values = {
            **{
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "max_output_tokens": max_output_tokens,
            },
            **kwargs,
        }
        opts = _obtain_opts(self.model_opts, **default_values)
        log.debug("codegen anthropic call:", **opts)

        model_messages = _build_model_messages(messages)

        with self.instrumentator.watch(stream=stream) as watcher:
            try:
                suggestion = await self.client.messages.create(
                    model=self.metadata.name,
                    stream=stream,
                    **model_messages,
                    **opts,
                )
            except APIStatusError as ex:
                raise AnthropicAPIStatusError.from_exception(ex)
            except APITimeoutError as ex:
                raise AnthropicAPITimeoutError.from_exception(ex)
            except APIConnectionError as ex:
                raise AnthropicAPIConnectionError.from_exception(ex)

            if stream:
                return self._handle_stream(
                    suggestion,
                    watcher.finish,
                    watcher.register_error,
                )

        text = (
            getattr(suggestion.content[0], "text", "") if hasattr(suggestion, "content") and suggestion.content else ""
        )
        return TextGenModelOutput(
            text=text,
            # Give a high value, the model doesn't return scores.
            score=10**5,
            safety_attributes=SafetyAttributes(),
        )

    async def _handle_stream(
        self,
        response,
        after_callback: Callable,
        error_callback: Callable,
    ) -> AsyncIterator[TextGenModelChunk]:
        try:
            async for event in response:
                if isinstance(event, AnthropicMessage):
                    text = getattr(event.content[0], "text", "") if event.content else ""
                elif isinstance(event, ContentBlockDeltaEvent):
                    text = getattr(event.delta, "text", "") if event.delta else ""
                else:
                    continue
                yield TextGenModelChunk(text=text)
        except Exception:
            error_callback()
            raise
        finally:
            after_callback()

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindAnthropicModel],
        client: AsyncAnthropic,
        **kwargs: Any,
    ):
        try:
            kind_model = KindAnthropicModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        return cls(client, model_name=kind_model.value, **kwargs)


def _build_model_messages(messages: list[Message]) -> dict:
    request: dict = {"system": NOT_GIVEN, "messages": []}

    for message in messages:
        if message.role == Role.SYSTEM:
            request["system"] = message.content
        else:
            request["messages"].append(message.model_dump())

    return request


def _obtain_opts(default_opts: dict, **kwargs: Any) -> dict:
    return {opt_name: kwargs.pop(opt_name, opt_value) or opt_value for opt_name, opt_value in default_opts.items()}
