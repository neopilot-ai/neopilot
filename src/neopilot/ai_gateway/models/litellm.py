from enum import StrEnum
from typing import AsyncIterator, Callable, Optional, Sequence, Union

from litellm import CustomStreamWrapper, ModelResponse, acompletion
from litellm.exceptions import APIConnectionError, InternalServerError
from openai import AsyncOpenAI

from neopilot.ai_gateway.models.base import (
    KindModelProvider,
    ModelAPIError,
    ModelMetadata,
    TokensConsumptionMetadata,
)
from neopilot.ai_gateway.models.base_chat import ChatModelBase, Message, Role
from neopilot.ai_gateway.models.base_text import (
    TextGenModelBase,
    TextGenModelChunk,
    TextGenModelOutput,
)
from neopilot.ai_gateway.models.vertex_text import KindVertexTextModel
from neopilot.ai_gateway.safety_attributes import SafetyAttributes
from neopilot.ai_gateway.tracking import SnowplowEventContext

__all__ = [
    "LiteLlmChatModel",
    "LiteLlmTextGenModel",
    "KindLiteLlmModel",
    "KindGitLabModel",
    "LiteLlmAPIConnectionError",
    "LiteLlmInternalServerError",
]

STUBBED_API_KEY = "stubbed-api-key"


class LiteLlmAPIConnectionError(ModelAPIError):
    @classmethod
    def from_exception(cls, ex: APIConnectionError):
        wrapper = cls(ex.message, errors=(ex,))

        return wrapper


class LiteLlmInternalServerError(ModelAPIError):
    @classmethod
    def from_exception(cls, ex: InternalServerError):
        wrapper = cls(ex.message, errors=(ex,))

        return wrapper


class KindGitLabModel(StrEnum):
    CODESTRAL_2501_FIREWORKS = "codestral_2501_fireworks"
    CODESTRAL_2501_VERTEX = "codestral_2501_vertex"
    CLAUDE_SONNET_3_7 = "claude_sonnet_3_7_20250219"
    CLAUDE_3_5_SONNET = "claude_3_5_sonnet_20240620"
    CLAUDE_3_5_HAIKU = "claude_3_5_haiku_20241022"
    GITLAB_DEFAULT_MODEL = ""


class KindLiteLlmModel(StrEnum):
    CODEGEMMA = "codegemma"
    CODELLAMA = "codellama"
    CODESTRAL = "codestral"
    CODESTRAL_2501 = "codestral-2501"
    MISTRAL = "mistral"
    MIXTRAL = "mixtral"
    DEEPSEEKCODER = "deepseekcoder"
    CLAUDE_3 = "claude_3"
    CLAUDE_3_5 = "claude_3.5"
    GPT = "gpt"
    QWEN_2_5 = "qwen2p5-coder-7b"
    LLAMA3 = "llama3"
    GENERAL = "general"

    def _chat_provider_prefix(self, provider):
        # Chat models hosted behind openai proxies should be prefixed with "openai/":
        # https://docs.litellm.ai/docs/providers/openai_compatible
        if provider == KindModelProvider.LITELLM:
            return "custom_openai"

        return provider.value

    def _text_provider_prefix(self, provider):
        # Text completion models hosted behind openai proxies should be prefixed with "text-completion-openai/":
        # https://docs.litellm.ai/docs/providers/openai_compatible
        if provider == KindModelProvider.LITELLM:
            return "text-completion-custom_openai"

        return f"text-completion-{provider.value}"

    def chat_model(self, provider=KindModelProvider.LITELLM) -> str:
        return f"{self._chat_provider_prefix(provider)}/{self.value}"

    def text_model(self, provider=KindModelProvider.LITELLM) -> str:
        return f"{self._text_provider_prefix(provider)}/{self.value}"


class ModelCompletionType(StrEnum):
    TEXT = "text"
    CHAT = "chat"
    FIM = "fim"


MODEL_STOP_TOKENS = {
    KindLiteLlmModel.MISTRAL: ["</new_code>"],
    # Ref: https://huggingface.co/google/codegemma_2b-7b
    # The model returns the completion, followed by one of the FIM tokens or the EOS token.
    # You should ignore everything that comes after any of these tokens.
    KindLiteLlmModel.CODEGEMMA: [
        "<|fim_prefix|>",
        "<|fim_suffix|>",
        "<|fim_middle|>",
        "<|file_separator|>",
    ],
    KindLiteLlmModel.CODESTRAL_2501: [
        "\n\n",
        "\n+++++",
        "[PREFIX]",
        "</s>[SUFFIX]",
        "[MIDDLE]",
    ],
    KindLiteLlmModel.QWEN_2_5: [
        "<|fim_prefix|>",
        "<|fim_suffix|>",
        "<|fim_middle|>",
        "<|fim_pad|>",
        "<|repo_name|>",
        "<|file_sep|>",
        "<|im_start|>",
        "<|im_end|>",
        "\n\n",
    ],
}

MODEL_SPECIFICATIONS = {
    KindModelProvider.VERTEX_AI: {
        KindVertexTextModel.CODESTRAL_2501: {
            "timeout": 60,
            "completion_type": ModelCompletionType.TEXT,
        },
    },
    KindModelProvider.FIREWORKS: {
        KindLiteLlmModel.CODESTRAL_2501: {
            "timeout": 60,
            "completion_type": ModelCompletionType.FIM,
            # this model is suffix-first, then prefix
            "fim_format": "</s>[SUFFIX]{suffix}[PREFIX]{prefix}[MIDDLE]",
            "session_header": True,
        },
        KindLiteLlmModel.QWEN_2_5: {
            "timeout": 60,
            "completion_type": ModelCompletionType.FIM,
            "fim_format": "<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>",
            "session_header": True,
        },
    },
}


INPUT_TOKENS_LIMIT = {
    KindLiteLlmModel.CODEGEMMA: 8_192,
    KindLiteLlmModel.CODELLAMA: 16_384,
}
DEFAULT_TOKEN_LIMIT = 32_768


class LiteLlmChatModel(ChatModelBase):
    @property
    def input_token_limit(self) -> int:
        return INPUT_TOKENS_LIMIT.get(self.model_name, DEFAULT_TOKEN_LIMIT)

    def __init__(
        self,
        model_name: KindLiteLlmModel = KindLiteLlmModel.MISTRAL,
        provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
        metadata: Optional[ModelMetadata] = None,
        disable_streaming: bool = False,
        async_fireworks_client: Optional[AsyncOpenAI] = None,
    ):
        self._metadata = _init_litellm_model_metadata(metadata, model_name, provider)
        self.provider = provider
        self.model_name = model_name
        self.stop_tokens = MODEL_STOP_TOKENS.get(model_name, [])
        self.disable_streaming = disable_streaming
        self.async_fireworks_client = async_fireworks_client

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(
        self,
        messages: list[Message],
        stream: bool = False,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        top_p: float = 0.95,
        code_context: Optional[Sequence[str]] = None,  # pylint: disable=unused-argument
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:
        should_stream = not self.disable_streaming and stream

        if isinstance(messages, str):
            messages = [Message(content=messages, role=Role.USER)]

        litellm_messages = [message.model_dump(mode="json") for message in messages]

        completion_args = {
            "messages": litellm_messages,
            "stream": should_stream,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_output_tokens,
            "timeout": 30.0,
            "stop": self.stop_tokens,
            **self.model_metadata_to_params(),
        }

        if self.provider == KindModelProvider.FIREWORKS:
            completion_args["client"] = self.async_fireworks_client
            # disable prompt caching
            completion_args["prompt_cache_max_len"] = 0

        with self.instrumentator.watch(stream=stream) as watcher:
            suggestion = await acompletion(**completion_args)

            if should_stream:
                return self._handle_stream(
                    suggestion,
                    watcher.finish,
                    watcher.register_error,
                )

        return TextGenModelOutput(
            text=suggestion.choices[0].message.content,
            # Give a high value, the model doesn't return scores.
            score=10**5,
            safety_attributes=SafetyAttributes(),
            metadata=self._extract_suggestion_metadata(suggestion),
        )

    async def _handle_stream(
        self,
        response: CustomStreamWrapper,
        after_callback: Callable,
        error_callback: Callable,
    ) -> AsyncIterator[TextGenModelChunk]:
        try:
            async for chunk in response:
                yield TextGenModelChunk(text=(chunk.choices[0].delta.content or ""))
        except Exception:
            error_callback()
            raise
        finally:
            after_callback()

    def _extract_suggestion_metadata(self, suggestion):
        return TokensConsumptionMetadata(
            output_tokens=(suggestion.usage.completion_tokens if hasattr(suggestion, "usage") else 0),
        )

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindLiteLlmModel],
        custom_models_enabled: bool = False,
        disable_streaming: bool = False,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        identifier: Optional[str] = None,
        provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
        provider_keys: Optional[dict] = None,
        provider_endpoints: Optional[dict] = None,
        async_fireworks_client: Optional[AsyncOpenAI] = None,
    ):
        if not custom_models_enabled:
            if endpoint is not None or api_key is not None:
                raise ValueError("specifying custom models endpoint is disabled")

        if provider == KindModelProvider.MISTRALAI:
            api_key = provider_keys.get("mistral_api_key")

        if provider == KindModelProvider.FIREWORKS:
            api_key = provider_keys.get("fireworks_api_key")

            endpoint, identifier = _get_fireworks_config(provider_endpoints, name)
            identifier = f"fireworks_ai/{identifier}"

        try:
            kind_model = KindLiteLlmModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        model_metadata = ModelMetadata(
            name=kind_model.chat_model(provider),
            engine=provider,
            endpoint=endpoint,
            api_key=api_key,
            identifier=identifier,
        )

        return cls(
            kind_model,
            provider,
            model_metadata,
            disable_streaming,
            async_fireworks_client=async_fireworks_client,
        )


class LiteLlmTextGenModel(TextGenModelBase):
    @property
    def input_token_limit(self) -> int:
        return INPUT_TOKENS_LIMIT.get(self.model_name, DEFAULT_TOKEN_LIMIT)

    def __init__(
        self,
        using_cache: bool,
        model_name: KindLiteLlmModel = KindLiteLlmModel.CODEGEMMA,
        vertex_model_location: str = "",
        provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
        metadata: Optional[ModelMetadata] = None,
        disable_streaming: bool = False,
        async_fireworks_client: Optional[AsyncOpenAI] = None,
    ):
        self.provider = provider
        self.model_name = model_name
        self._metadata = _init_litellm_model_metadata(metadata, model_name, provider)
        self.disable_streaming = disable_streaming
        self.vertex_model_location = vertex_model_location

        self.stop_tokens = MODEL_STOP_TOKENS.get(model_name, [])
        self.async_fireworks_client = async_fireworks_client
        self.using_cache = using_cache

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    @property
    def specifications(self):
        return MODEL_SPECIFICATIONS.get(self.provider, {}).get(self.model_name, {})

    async def generate(
        self,
        prefix: str,
        suffix: Optional[str] = "",
        stream: bool = False,
        temperature: float = 0.95,
        max_output_tokens: int = 16,
        top_p: float = 0.95,
        code_context: Optional[Sequence[str]] = None,  # pylint: disable=unused-argument
        snowplow_event_context: Optional[SnowplowEventContext] = None,
    ) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:
        should_stream = not self.disable_streaming and stream

        with self.instrumentator.watch(stream=should_stream) as watcher:
            try:
                suggestion = await self._get_suggestion(
                    prefix=prefix,
                    suffix=suffix,
                    stream=should_stream,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    top_p=top_p,
                    snowplow_event_context=snowplow_event_context,
                )
            except APIConnectionError as ex:
                raise LiteLlmAPIConnectionError.from_exception(ex)
            except InternalServerError as ex:
                raise LiteLlmInternalServerError.from_exception(ex)

            if should_stream:
                return self._handle_stream(
                    suggestion,
                    watcher.finish,
                    watcher.register_error,
                )

        score = 10**5  # default high value if model doesn't provide score

        # For fireworks/qwen, use logprob of first token as score
        if self.provider == KindModelProvider.FIREWORKS:
            score = suggestion.choices[0].logprobs.token_logprobs[0]

        return TextGenModelOutput(
            text=self._extract_suggestion_text(suggestion),
            score=score,
            safety_attributes=SafetyAttributes(),
            metadata=self._extract_suggestion_metadata(suggestion, max_output_tokens),
        )

    async def _handle_stream(
        self,
        response: CustomStreamWrapper,
        after_callback: Callable,
        error_callback: Callable,
    ) -> AsyncIterator[TextGenModelChunk]:
        try:
            async for chunk in response:
                yield TextGenModelChunk(text=(chunk.choices[0].delta.content or ""))
        except Exception:
            error_callback()
            raise
        finally:
            after_callback()

    async def _get_suggestion(
        self,
        prefix: str,
        stream: bool,
        temperature: float,
        max_output_tokens: int,
        top_p: float,
        suffix: Optional[str] = "",
        snowplow_event_context: Optional[SnowplowEventContext] = None,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        content = prefix

        if self._completion_type() == ModelCompletionType.FIM:
            fim_format = self.specifications.get("fim_format")
            content = fim_format.format(prefix=prefix, suffix=suffix or "")

        completion_args = {
            "messages": [{"content": content, "role": Role.USER}],
            "max_tokens": max_output_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
            "timeout": self.specifications.get("timeout", 30.0),
            "stop": self._get_stop_tokens(suffix),
        }

        if self._is_vertex():
            completion_args["vertex_ai_location"] = self._get_vertex_model_location()
            completion_args["model"] = self.metadata.name
        else:
            completion_args = completion_args | self.model_metadata_to_params()

        if self._completion_type() == ModelCompletionType.TEXT:
            completion_args["suffix"] = suffix
            completion_args["text_completion"] = True

        if self._session_header() and snowplow_event_context and snowplow_event_context.gitlab_global_user_id:
            completion_args["extra_headers"] = {"x-session-affinity": snowplow_event_context.gitlab_global_user_id}

        if self.provider == KindModelProvider.FIREWORKS:
            completion_args["client"] = self.async_fireworks_client
            # disable prompt caching
            if not self.using_cache:
                completion_args["prompt_cache_max_len"] = 0
            completion_args["logprobs"] = 1

        return await acompletion(**completion_args)

    def _completion_type(self):
        return self.specifications.get("completion_type", ModelCompletionType.CHAT)

    def _session_header(self):
        return self.specifications.get("session_header", False)

    def _extract_suggestion_text(self, suggestion):
        if self._completion_type() == ModelCompletionType.TEXT:
            return suggestion.choices[0].text

        return suggestion.choices[0].message.content

    def _extract_suggestion_metadata(self, suggestion, max_output_tokens):
        output_tokens = suggestion.usage.completion_tokens if hasattr(suggestion, "usage") else 0

        max_output_tokens_used = output_tokens == max_output_tokens

        return TokensConsumptionMetadata(
            output_tokens=output_tokens,
            max_output_tokens_used=max_output_tokens_used,
        )

    def _get_stop_tokens(self, suffix):  # pylint: disable=unused-argument
        return self.stop_tokens

    def _is_vertex(self):
        return self.provider == KindModelProvider.VERTEX_AI

    def _get_vertex_model_location(self):
        if self.vertex_model_location.startswith("europe-"):
            return "europe-west4"

        return "us-central1"

    @classmethod
    def from_model_name(
        cls,
        name: Union[str, KindLiteLlmModel],
        custom_models_enabled: bool = False,
        disable_streaming: bool = False,
        vertex_model_location: str = "",
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        identifier: Optional[str] = None,
        provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
        provider_keys: Optional[dict] = None,
        provider_endpoints: Optional[dict] = None,
        async_fireworks_client: Optional[AsyncOpenAI] = None,
        using_cache: bool = True,
    ):
        if not custom_models_enabled:
            if endpoint is not None or api_key is not None:
                raise ValueError("specifying custom models endpoint is disabled")

        if provider == KindModelProvider.MISTRALAI:
            api_key = provider_keys.get("mistral_api_key")

        if provider == KindModelProvider.FIREWORKS:
            api_key = provider_keys.get("fireworks_api_key")

            if not api_key:
                raise ValueError("Fireworks API key is missing from configuration.")

            endpoint, identifier = _get_fireworks_config(provider_endpoints, name)
            identifier = f"text-completion-openai/{identifier}"

        try:
            if provider == KindModelProvider.VERTEX_AI:
                kind_model = KindVertexTextModel(name)
            else:
                kind_model = KindLiteLlmModel(name)
        except ValueError:
            raise ValueError(f"no model found by the name '{name}'")

        metadata = ModelMetadata(
            name=kind_model.text_model(provider),
            engine=provider.value,
            endpoint=endpoint,
            api_key=api_key,
            identifier=identifier,
        )

        return cls(
            model_name=kind_model,
            provider=provider,
            metadata=metadata,
            disable_streaming=disable_streaming,
            async_fireworks_client=async_fireworks_client,
            vertex_model_location=vertex_model_location,
            using_cache=using_cache,
        )


def _get_fireworks_config(provider_endpoints: dict, model_name: str) -> tuple[str, str]:
    """Get Fireworks endpoint and identifier based on region configuration.

    Args:
        provider_endpoints: Dictionary containing provider endpoint configurations

    Returns:
        tuple: (endpoint, identifier) for Fireworks configuration

    Raises:
        ValueError: If required configuration is missing
    """
    # Get endpoint configuration for selected region
    region_config = provider_endpoints.get("fireworks_current_region_endpoint", {})

    if not region_config:
        raise ValueError("Fireworks regional endpoints configuration is missing.")

    model_config = region_config.get(model_name)

    if not model_config:
        raise ValueError(f"Fireworks model configuration is missing for model {model_name}.")

    endpoint = model_config.get("endpoint")
    identifier = model_config.get("identifier")

    if not endpoint or not identifier:
        raise ValueError("Fireworks endpoint or identifier missing in region config.")

    return endpoint, identifier


def _init_litellm_model_metadata(
    metadata: Optional[ModelMetadata] = None,
    model_name: KindLiteLlmModel = KindLiteLlmModel.MISTRAL,
    provider: Optional[KindModelProvider] = KindModelProvider.LITELLM,
) -> ModelMetadata:
    if metadata:
        return ModelMetadata(**(metadata._asdict() | {"api_key": metadata.api_key or STUBBED_API_KEY}))

    return ModelMetadata(
        name=model_name.chat_model(provider),
        api_key=STUBBED_API_KEY,
        engine=provider.value(),
    )
