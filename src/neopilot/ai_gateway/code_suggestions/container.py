from __future__ import annotations

import anthropic
from dependency_injector import containers, providers
from transformers import PreTrainedTokenizerFast

from neopilot.ai_gateway.code_suggestions.completions import (
    CodeCompletions, CodeCompletionsLegacy)
from neopilot.ai_gateway.code_suggestions.generations import CodeGenerations
from neopilot.ai_gateway.code_suggestions.processing import \
    ModelEngineCompletions
from neopilot.ai_gateway.code_suggestions.processing.post.completions import \
    PostProcessor as PostProcessorCompletions
from neopilot.ai_gateway.code_suggestions.processing.post.completions import \
    PostProcessorOperation
from neopilot.ai_gateway.code_suggestions.processing.pre import \
    TokenizerTokenStrategy
from neopilot.ai_gateway.models import KindAnthropicModel, KindVertexTextModel
from neopilot.ai_gateway.models.base import KindModelProvider
from neopilot.ai_gateway.models.base_chat import ChatModelBase
from neopilot.ai_gateway.models.base_text import TextGenModelBase
from neopilot.ai_gateway.tokenizer import init_tokenizer
from neopilot.ai_gateway.tracking.instrumentator import SnowplowInstrumentator

__all__ = [
    "ContainerCodeSuggestions",
]


class ContainerCodeGenerations(containers.DeclarativeContainer):
    tokenizer = providers.Dependency(instance_of=PreTrainedTokenizerFast)
    vertex_code_bison = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]
    anthropic_claude = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]
    anthropic_claude_chat = providers.Dependency(instance_of=ChatModelBase)  # type: ignore[type-abstract]
    amazon_q_model = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]
    litellm_chat = providers.Dependency(instance_of=ChatModelBase)  # type: ignore[type-abstract]
    agent_model = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]

    snowplow_instrumentator = providers.Dependency(instance_of=SnowplowInstrumentator)

    vertex = providers.Factory(
        CodeGenerations,
        model=providers.Factory(vertex_code_bison, name=KindVertexTextModel.CODE_BISON_002),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        snowplow_instrumentator=snowplow_instrumentator,
    )

    # We need to resolve the model based on model name provided in request payload
    # Hence, CodeGenerations is only partially applied here.
    anthropic_factory = providers.Factory(
        CodeGenerations,
        model=providers.Factory(
            anthropic_claude,
            stop_sequences=["</new_code>", anthropic.HUMAN_PROMPT],
        ),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        snowplow_instrumentator=snowplow_instrumentator,
    )

    anthropic_chat_factory = providers.Factory(
        CodeGenerations,
        model=providers.Factory(anthropic_claude_chat),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        snowplow_instrumentator=snowplow_instrumentator,
    )

    litellm_factory = providers.Factory(
        CodeGenerations,
        model=providers.Factory(litellm_chat),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        snowplow_instrumentator=snowplow_instrumentator,
    )

    amazon_q_factory = providers.Factory(
        CodeGenerations,
        model=providers.Factory(amazon_q_model),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        snowplow_instrumentator=snowplow_instrumentator,
    )

    agent_factory = providers.Factory(
        CodeGenerations,
        model=providers.Factory(agent_model),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        snowplow_instrumentator=snowplow_instrumentator,
    )

    anthropic_default = providers.Factory(
        anthropic_factory,
        model__name=KindAnthropicModel.CLAUDE_3_5_SONNET_V2,
    )


class ContainerCodeCompletions(containers.DeclarativeContainer):
    tokenizer = providers.Dependency(instance_of=PreTrainedTokenizerFast)
    vertex_code_gecko = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]
    anthropic_claude = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]
    anthropic_claude_chat = providers.Dependency(instance_of=ChatModelBase)  # type: ignore[type-abstract]
    litellm = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]
    agent_model = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]
    amazon_q_model = providers.Dependency(instance_of=TextGenModelBase)  # type: ignore[type-abstract]
    snowplow_instrumentator = providers.Dependency(instance_of=SnowplowInstrumentator)

    config = providers.Configuration(strict=True)

    vertex_legacy = providers.Factory(
        CodeCompletionsLegacy,
        engine=providers.Factory(
            ModelEngineCompletions,
            model=providers.Factory(vertex_code_gecko, name=KindVertexTextModel.CODE_GECKO_002),
            tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        ),
        post_processor=providers.Factory(
            PostProcessorCompletions,
            overrides={
                PostProcessorOperation.FIX_END_BLOCK_ERRORS: PostProcessorOperation.FIX_END_BLOCK_ERRORS_LEGACY,
            },
            exclude=config.excl_post_process,
        ).provider,
        snowplow_instrumentator=snowplow_instrumentator,
    )

    anthropic = providers.Factory(
        CodeCompletions,
        model=providers.Factory(anthropic_claude_chat),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
    )

    litellm_factory = providers.Factory(
        CodeCompletions,
        model=providers.Factory(litellm),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
    )

    fireworks_factory = providers.Factory(
        CodeCompletions,
        model=providers.Factory(
            litellm,
            provider=KindModelProvider.FIREWORKS,
        ),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        post_processor=providers.Factory(
            PostProcessorCompletions,
            exclude=config.excl_post_process,
            extras=[
                PostProcessorOperation.FILTER_SCORE,
                PostProcessorOperation.FIX_TRUNCATION,
            ],
            score_threshold=config.fireworks_score_threshold,
        ).provider,
    )

    litellm_vertex_codestral_factory = providers.Factory(
        CodeCompletions,
        model=providers.Factory(
            litellm,
            name=KindVertexTextModel.CODESTRAL_2501,
            provider=KindModelProvider.VERTEX_AI,
        ),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
        post_processor=providers.Factory(
            PostProcessorCompletions,
            extras=[PostProcessorOperation.STRIP_ASTERISKS],
            exclude=config.excl_post_process,
        ).provider,
    )

    agent_factory = providers.Factory(
        CodeCompletions,
        model=providers.Factory(agent_model),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
    )

    amazon_q_factory = providers.Factory(
        CodeCompletions,
        model=providers.Factory(amazon_q_model),
        tokenization_strategy=providers.Factory(TokenizerTokenStrategy, tokenizer=tokenizer),
    )


class ContainerCodeSuggestions(containers.DeclarativeContainer):
    models = providers.DependenciesContainer()

    config = providers.Configuration(strict=True)

    tokenizer = providers.Singleton(init_tokenizer)

    snowplow = providers.DependenciesContainer()

    generations = providers.Container(
        ContainerCodeGenerations,
        tokenizer=tokenizer,
        vertex_code_bison=models.vertex_code_bison,
        anthropic_claude=models.anthropic_claude,
        anthropic_claude_chat=models.anthropic_claude_chat,
        litellm_chat=models.litellm_chat,
        agent_model=models.agent_model,
        amazon_q_model=models.amazon_q_model,
        snowplow_instrumentator=snowplow.instrumentator,
    )

    completions = providers.Container(
        ContainerCodeCompletions,
        tokenizer=tokenizer,
        vertex_code_gecko=models.vertex_code_gecko,
        anthropic_claude=models.anthropic_claude,
        anthropic_claude_chat=models.anthropic_claude_chat,
        litellm=models.litellm,
        agent_model=models.agent_model,
        amazon_q_model=models.amazon_q_model,
        config=config,
        snowplow_instrumentator=snowplow.instrumentator,
    )
