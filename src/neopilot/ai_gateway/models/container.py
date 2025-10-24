from __future__ import annotations

import httpx
from dependency_injector import containers, providers
from google.cloud.aiplatform.gapic import PredictionServiceAsyncClient
from openai import AsyncOpenAI

from neopilot.ai_gateway.config import ConfigModelLimits
from neopilot.ai_gateway.models import mock
from neopilot.ai_gateway.models.agent_model import AgentModel
from neopilot.ai_gateway.models.amazon_q import AmazonQModel
from neopilot.ai_gateway.models.anthropic import (AnthropicChatModel,
                                                  AnthropicModel)
from neopilot.ai_gateway.models.base import (grpc_connect_vertex,
                                             init_anthropic_client)
from neopilot.ai_gateway.models.litellm import (LiteLlmChatModel,
                                                LiteLlmTextGenModel)
from neopilot.ai_gateway.models.vertex_text import (PalmCodeBisonModel,
                                                    PalmCodeGeckoModel,
                                                    PalmTextBisonModel)
from neopilot.ai_gateway.proxy.clients import (AnthropicProxyClient,
                                               OpenAIProxyClient,
                                               VertexAIProxyClient)

__all__ = [
    "ContainerModels",
]


def _init_vertex_grpc_client(
    endpoint: str,
    mock_model_responses: bool,
    custom_models_enabled: bool,
) -> PredictionServiceAsyncClient | None:
    if mock_model_responses or custom_models_enabled:
        return None
    return grpc_connect_vertex({"api_endpoint": endpoint})


def _init_async_fireworks_client(model_keys: dict, model_endpoints: dict) -> AsyncOpenAI | None:
    api_key = model_keys.get("fireworks_api_key")
    base_url = model_endpoints.get("fireworks_current_region_endpoint", {}).get("endpoint", {})
    if api_key and base_url:
        return AsyncOpenAI(api_key=api_key, base_url=base_url, http_client=httpx.AsyncClient())

    return None


def _init_anthropic_proxy_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="https://api.anthropic.com/", timeout=httpx.Timeout(timeout=60.0))


def _init_vertex_ai_proxy_client(endpoint: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=f"https://{endpoint}/",
        timeout=httpx.Timeout(timeout=60.0),
    )


def _init_openai_proxy_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://api.openai.com/",
        timeout=httpx.Timeout(timeout=60.0),
    )


class ContainerModels(containers.DeclarativeContainer):
    # We need to resolve the model based on the model name provided by the upstream container.
    # Hence, `VertexTextBaseModel.from_model_name` and `AnthropicModel.from_model_name` are only partially applied here.

    config = providers.Configuration(strict=True)
    integrations = providers.DependenciesContainer()

    _mock_selector = providers.Callable(
        lambda mock_model_responses: "mocked" if mock_model_responses else "original",
        config.mock_model_responses,
    )

    grpc_client_vertex = providers.Singleton(
        _init_vertex_grpc_client,
        endpoint=config.vertex_text_model.endpoint,
        mock_model_responses=config.mock_model_responses,
        custom_models_enabled=config.custom_models.enabled,
    )

    async_fireworks_client = providers.Singleton(
        _init_async_fireworks_client,
        model_keys=config.model_keys,
        model_endpoints=config.model_endpoints,
    )

    http_client_anthropic = providers.Singleton(init_anthropic_client)

    http_client_anthropic_proxy = providers.Singleton(_init_anthropic_proxy_client)

    http_client_vertex_ai_proxy = providers.Singleton(
        _init_vertex_ai_proxy_client,
        endpoint=config.vertex_text_model.endpoint,
    )

    http_client_openai_proxy = providers.Singleton(_init_openai_proxy_client)

    vertex_text_bison = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            PalmTextBisonModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        mocked=providers.Factory(mock.LLM),
    )

    vertex_code_bison = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            PalmCodeBisonModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        mocked=providers.Factory(mock.LLM),
    )

    vertex_code_gecko = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            PalmCodeGeckoModel.from_model_name,
            client=grpc_client_vertex,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
        ),
        mocked=providers.Factory(mock.LLM),
    )

    anthropic_claude = providers.Selector(
        _mock_selector,
        original=providers.Factory(AnthropicModel.from_model_name, client=http_client_anthropic),
        mocked=providers.Factory(mock.LLM),
    )

    anthropic_claude_chat = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            AnthropicChatModel.from_model_name,
            client=http_client_anthropic,
        ),
        mocked=providers.Factory(mock.ChatModel),
    )

    litellm = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            LiteLlmTextGenModel.from_model_name,
            custom_models_enabled=config.custom_models.enabled,
            disable_streaming=config.custom_models.disable_streaming,
            provider_keys=config.model_keys,
            provider_endpoints=config.model_endpoints,
            async_fireworks_client=async_fireworks_client,
            vertex_model_location=config.vertex_text_model.location,
        ),
        mocked=providers.Factory(mock.LLM),
    )

    litellm_chat = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            LiteLlmChatModel.from_model_name,
            custom_models_enabled=config.custom_models.enabled,
            disable_streaming=config.custom_models.disable_streaming,
            provider_keys=config.model_keys,
            provider_endpoints=config.model_endpoints,
            async_fireworks_client=async_fireworks_client,
        ),
        mocked=providers.Factory(mock.ChatModel),
    )

    agent_model = providers.Selector(
        _mock_selector,
        original=providers.Factory(AgentModel),
        mocked=providers.Factory(mock.LLM),
    )

    amazon_q_model = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            AmazonQModel,
            client_factory=integrations.amazon_q_client_factory,
        ),
        mocked=providers.Factory(mock.LLM),
    )

    anthropic_proxy_client = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            AnthropicProxyClient,
            client=http_client_anthropic_proxy,
            limits=providers.Factory(ConfigModelLimits, config.model_engine_limits),
        ),
        mocked=providers.Factory(mock.ProxyClient),
    )

    vertex_ai_proxy_client = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            VertexAIProxyClient,
            client=http_client_vertex_ai_proxy,
            project=config.vertex_text_model.project,
            location=config.vertex_text_model.location,
            limits=providers.Factory(ConfigModelLimits, config.model_engine_limits),
        ),
        mocked=providers.Factory(mock.ProxyClient),
    )

    openai_proxy_client = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            OpenAIProxyClient,
            client=http_client_openai_proxy,
            limits=providers.Factory(ConfigModelLimits, config.model_engine_limits),
        ),
        mocked=providers.Factory(mock.ProxyClient),
    )
