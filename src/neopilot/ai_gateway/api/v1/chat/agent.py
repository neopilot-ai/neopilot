from __future__ import annotations

from time import time
from typing import Annotated, AsyncIterator, Optional, Union

from dependency_injector.providers import Factory, FactoryAggregate
from fastapi import APIRouter, Depends, HTTPException, Request, status
from gitlab_cloud_connector import GitLabUnitPrimitive
from lib.internal_events import InternalEventsClient

from neopilot.ai_gateway.api.auth_utils import StarletteUser, get_current_user
from neopilot.ai_gateway.api.feature_category import track_metadata
from neopilot.ai_gateway.api.v1.chat.auth import (
    ChatInvokable, authorize_with_unit_primitive)
from neopilot.ai_gateway.api.v1.chat.typing import (ChatRequest, ChatResponse,
                                                    ChatResponseMetadata,
                                                    PromptPayload,
                                                    StreamChatResponse)
from neopilot.ai_gateway.async_dependency_resolver import (
    get_chat_anthropic_claude_factory_provider,
    get_chat_litellm_factory_provider, get_internal_event_client)
from neopilot.ai_gateway.models import (AnthropicAPIConnectionError,
                                        AnthropicAPIStatusError,
                                        AnthropicAPITimeoutError,
                                        KindAnthropicModel, KindModelProvider)
from neopilot.ai_gateway.models.base_text import (TextGenModelChunk,
                                                  TextGenModelOutput)
from neopilot.ai_gateway.tracking import log_exception

__all__ = [
    "router",
]

router = APIRouter()

CHAT_INVOKABLES = [
    ChatInvokable(name="explain_code", unit_primitive=GitLabUnitPrimitive.NEOAI_CHAT),
    ChatInvokable(name="write_tests", unit_primitive=GitLabUnitPrimitive.NEOAI_CHAT),
    ChatInvokable(name="refactor_code", unit_primitive=GitLabUnitPrimitive.NEOAI_CHAT),
    ChatInvokable(
        name="explain_vulnerability",
        unit_primitive=GitLabUnitPrimitive.EXPLAIN_VULNERABILITY,
    ),
    ChatInvokable(
        name="summarize_comments",
        unit_primitive=GitLabUnitPrimitive.SUMMARIZE_COMMENTS,
    ),
    ChatInvokable(
        name="troubleshoot_job",
        unit_primitive=GitLabUnitPrimitive.TROUBLESHOOT_JOB,
    ),
    # Deprecated. Added for backward compatibility.
    # Please, refer to `v2/chat/agent` for additional details.
    ChatInvokable(name="agent", unit_primitive=GitLabUnitPrimitive.NEOAI_CHAT),
]

path_unit_primitive_map = {ci.name: ci.unit_primitive for ci in CHAT_INVOKABLES}


@router.post(
    "/{chat_invokable}",
    response_model=ChatResponse,
    deprecated=True,
    summary="Deprecated endpoint",
    description="This endpoint is deprecated and will be removed "
    "https://github.com/neopilot-ai/neopilot/-/issues/825",
    status_code=status.HTTP_200_OK,
)
@authorize_with_unit_primitive("chat_invokable", chat_invokables=CHAT_INVOKABLES)
@track_metadata("chat_invokable", mapping=path_unit_primitive_map)
async def chat(
    request: Request,  # pylint: disable=unused-argument
    chat_request: ChatRequest,
    chat_invokable: str,  # pylint: disable=unused-argument
    current_user: Annotated[StarletteUser, Depends(get_current_user)],  # pylint: disable=unused-argument
    anthropic_claude_factory: Annotated[FactoryAggregate, Depends(get_chat_anthropic_claude_factory_provider)],
    litellm_factory: Annotated[Factory, Depends(get_chat_litellm_factory_provider)],
    internal_event_client: Annotated[  # pylint: disable=unused-argument
        InternalEventsClient, Depends(get_internal_event_client)
    ],
):

    prompt_component = chat_request.prompt_components[0]
    payload = prompt_component.payload

    internal_event_client.track_event(
        f"request_{path_unit_primitive_map[chat_invokable]}",
        category=__name__,
    )

    try:
        if payload.provider in (
            KindModelProvider.LITELLM,
            KindModelProvider.MISTRALAI,
        ):
            model = litellm_factory(
                name=payload.model,
                endpoint=payload.model_endpoint,
                api_key=payload.model_api_key,
                provider=payload.provider,
                identifier=payload.model_identifier,
            )

            completion = await model.generate(
                messages=payload.content,
                stream=chat_request.stream,
            )
        else:
            completion = await _generate_completion(anthropic_claude_factory, payload, stream=chat_request.stream)

        if isinstance(completion, AsyncIterator):
            return await _handle_stream(completion)
        return ChatResponse(
            response=completion.text,
            metadata=ChatResponseMetadata(
                provider=payload.provider,
                model=payload.model.value if payload.model else None,
                timestamp=int(time()),
            ),
        )
    except AnthropicAPIStatusError as ex:
        log_exception(ex)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Anthropic API Status Error.",
        )
    except AnthropicAPITimeoutError as ex:
        log_exception(ex)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Anthropic API Timeout Error.",
        )
    except AnthropicAPIConnectionError as ex:
        log_exception(ex)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Anthropic API Connection Error.",
        )


async def _generate_completion(
    anthropic_claude_factory: FactoryAggregate,
    prompt: PromptPayload,
    stream: Optional[bool] = False,
) -> Union[TextGenModelOutput, AsyncIterator[TextGenModelChunk]]:
    opts = prompt.params.dict() if prompt.params else {}

    if isinstance(prompt.content, str):
        factory_type = "llm"  # retrieve `AnthropicModel` from the FactoryAggregate object
        opts.update({"prefix": prompt.content, "stream": stream})
    else:  # otherwise, `list[Message]`
        factory_type = "chat"  # retrieve `AnthropicChatModel` from the FactoryAggregate object
        opts.update({"messages": prompt.content, "stream": stream})

        # Hack: Anthropic renamed the `max_tokens_to_sample` arg to `max_tokens` for the new Message API
        if max_tokens := opts.pop("max_tokens_to_sample", None):
            opts["max_tokens"] = max_tokens

        # Temporary fix for mitigating https://gitlab.com/gitlab-com/gl-infra/production/-/issues/18996.
        # v1/chat/agent endpoint uses Claude models that support up to 4096 output tokens.
        if "max_tokens" in opts and opts["max_tokens"] > 4096:
            opts["max_tokens"] = 4096

    prompt_model = prompt.model
    if prompt.model in [
        KindAnthropicModel.CLAUDE_2_1,
        KindAnthropicModel.CLAUDE_3_SONNET,
    ]:
        # Overriding the model.
        # See https://github.com/neopilot-ai/neopilot/-/issues/1311
        prompt_model = KindAnthropicModel.CLAUDE_3_5_SONNET

    completion = await anthropic_claude_factory(factory_type, name=prompt_model).generate(**opts)

    return completion


async def _handle_stream(
    response: AsyncIterator[TextGenModelChunk],
) -> StreamChatResponse:
    async def _stream_generator():
        async for result in response:
            yield result.text

    return StreamChatResponse(_stream_generator(), media_type="text/event-stream")
