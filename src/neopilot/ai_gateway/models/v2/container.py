from dependency_injector import containers, providers
from langchain_openai import ChatOpenAI
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler

from neopilot.ai_gateway.integrations.amazon_q.chat import ChatAmazonQ
from neopilot.ai_gateway.models import mock
from neopilot.ai_gateway.models.base import init_anthropic_client, log_request
from neopilot.ai_gateway.models.v2.anthropic_claude import ChatAnthropic
from neopilot.ai_gateway.models.v2.chat_litellm import ChatLiteLLM
from neopilot.ai_gateway.prompts.typing import Model

__all__ = [
    "ContainerModels",
]


def _litellm_factory(*args, **kwargs) -> Model:

    if kwargs.get("custom_llm_provider", "") == "vertex_ai":
        kwargs["client"] = AsyncHTTPHandler(event_hooks={"request": [log_request]})

    return ChatLiteLLM(*args, **kwargs)


def _mock_selector(mock_model_responses: bool, use_agentic_mock: bool) -> str:
    if mock_model_responses and use_agentic_mock:
        return "agentic"

    if mock_model_responses:
        return "mocked"

    return "original"


class ContainerModels(containers.DeclarativeContainer):
    # We need to resolve the model based on the model name provided by the upstream container.
    # Hence, `ChatAnthropic` etc. are only partially applied here.

    config = providers.Configuration(strict=True)
    integrations = providers.DependenciesContainer()

    _mock_selector = providers.Callable(
        _mock_selector,
        config.mock_model_responses,
        config.use_agentic_mock,
    )

    http_async_client_anthropic = providers.Singleton(init_anthropic_client)

    anthropic_claude_chat_fn = providers.Selector(
        _mock_selector,
        original=providers.Factory(
            ChatAnthropic,
            async_client=http_async_client_anthropic,
            betas=["extended-cache-ttl-2025-04-11", "context-1m-2025-08-07"],
        ),
        mocked=providers.Factory(mock.FakeModel),
        agentic=providers.Factory(mock.AgenticFakeModel),
    )

    openai_chat_fn = providers.Factory(ChatOpenAI, output_version="responses/v1")

    lite_llm_chat_fn = providers.Factory(_litellm_factory)
    amazon_q_chat_fn = providers.Factory(
        ChatAmazonQ,
        amazon_q_client_factory=integrations.amazon_q_client_factory,
    )
