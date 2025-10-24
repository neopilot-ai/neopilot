import json
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, NamedTuple, Optional

import httpx
import structlog
from anthropic import AsyncAnthropic
from anthropic._base_client import _DefaultAsyncHttpxClient
from google.cloud.aiplatform.gapic import PredictionServiceAsyncClient
from pydantic import BaseModel

from neopilot.ai_gateway.config import Config
from neopilot.ai_gateway.instrumentators.model_requests import ModelRequestInstrumentator
from neopilot.ai_gateway.structured_logging import can_log_request_data, get_request_logger

# TODO: The instrumentator needs the config here to know what limit needs to be
# reported for a model. This would be nicer if we dependency inject the instrumentator
# into the model itself
# https://github.com/neopilot-ai/neopilot/-/issues/384
config = Config()

__all__ = [
    "KindModelProvider",
    "ModelAPIError",
    "ModelAPICallError",
    "ModelMetadata",
    "TokensConsumptionMetadata",
    "ModelBase",
    "grpc_connect_vertex",
    "init_anthropic_client",
]

log = structlog.stdlib.get_logger("models")
request_log = get_request_logger("models")


class KindModelProvider(StrEnum):
    ANTHROPIC = "anthropic"
    VERTEX_AI = "vertex-ai"
    LITELLM = "litellm"
    MISTRALAI = "codestral"
    FIREWORKS = "fireworks_ai"
    AMAZON_Q = "amazon_q"
    GITLAB = "gitlab"


class ModelAPIError(Exception):
    def __init__(self, message: str, errors: tuple = (), details: tuple = ()):
        self.message = message
        self._errors = errors
        self._details = details

    def __str__(self):
        message = self.message

        if self.details:
            message = f"{message} {self.details}"

        return message

    @property
    def errors(self) -> list[Any]:
        return list(self._errors)

    @property
    def details(self) -> list[Any]:
        return list(self._details)


class ModelAPICallError(ModelAPIError):
    code: Optional[int] = None

    def __init__(self, message: str, errors: tuple = (), details: tuple = ()):
        super().__init__(f"{self.code} {message}", errors=errors, details=details)


class TokensConsumptionMetadata(BaseModel):
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    max_output_tokens_used: bool = False
    # number of tokens sent to AI Gateway
    context_tokens_sent: Optional[int] = None
    # number of tokens from context used in the prompt
    context_tokens_used: Optional[int] = None


class ModelMetadata(NamedTuple):
    name: str
    engine: str
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    identifier: Optional[str] = None


class ModelBase(ABC):
    @property
    def input_token_limit(self) -> int:
        # Default token limit
        return 2_048

    @property
    def instrumentator(self) -> ModelRequestInstrumentator:
        return ModelRequestInstrumentator(
            model_engine=self.metadata.engine,
            model_name=self.metadata.name,
            limits=config.model_engine_limits.for_model(engine=self.metadata.engine, name=self.metadata.name),
        )

    @property
    @abstractmethod
    def metadata(self) -> ModelMetadata:
        pass

    def model_metadata_to_params(self) -> dict[str, str]:
        params = {
            "api_base": str(self.metadata.endpoint),
            "api_key": str(self.metadata.api_key),
            "model": self.metadata.name,
        }

        if not self.metadata.identifier:
            return params

        provider, _, model_name = self.metadata.identifier.partition("/")

        if model_name:
            params["custom_llm_provider"] = provider
            params["model"] = model_name

            if provider == "bedrock":
                del params["api_base"]
        else:
            params["custom_llm_provider"] = "custom_openai"
            params["model"] = self.metadata.identifier

        return params


def grpc_connect_vertex(client_options: dict) -> PredictionServiceAsyncClient:
    log.info("Initializing Vertex AI client", **client_options)

    # Ignore the typecheck for this line until the type is changed to Union upstream:
    # https://github.com/googleapis/python-aiplatform/pull/5272
    return PredictionServiceAsyncClient(client_options=client_options)  # type: ignore


async def log_request(request: httpx.Request):
    if can_log_request_data():
        request_log.info(
            "Request to LLM",
            source=__name__,
            request_method=request.method,
            request_url=request.url,
            request_content_json=json.loads(request.content.decode("utf8")),
        )
    else:
        log.info(
            "Request to LLM",
            source=__name__,
            request_method=request.method,
            request_url=request.url,
            request_content_json={},
        )


def init_anthropic_client() -> AsyncAnthropic:
    # Setting 30 seconds to the keep-alive expiry to avoid TLS handshake on every request.
    # See https://www.python-httpx.org/advanced/resource-limits/ for more information.
    limits: httpx.Limits = httpx.Limits(max_connections=1000, max_keepalive_connections=100, keepalive_expiry=30)

    http_client: httpx.AsyncClient = _DefaultAsyncHttpxClient(limits=limits, event_hooks={"request": [log_request]})

    return AsyncAnthropic(http_client=http_client)
