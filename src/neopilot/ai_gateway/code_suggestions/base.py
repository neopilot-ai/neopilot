from enum import StrEnum
from pathlib import Path
from typing import NamedTuple, Optional

from neopilot.ai_gateway.code_suggestions.processing import LanguageId
from neopilot.ai_gateway.code_suggestions.processing.base import LANGUAGE_COUNTER
from neopilot.ai_gateway.code_suggestions.processing.ops import (
    lang_from_editor_lang,
    lang_from_filename,
    lang_name_from_filename,
)
from neopilot.ai_gateway.models import (
    KindAmazonQModel,
    KindAnthropicModel,
    KindGitLabModel,
    KindLiteLlmModel,
    KindModelProvider,
    KindVertexTextModel,
    ModelMetadata,
)
from neopilot.ai_gateway.models.base import TokensConsumptionMetadata

__all__ = [
    "KindUseCase",
    "CodeSuggestionsOutput",
    "CodeSuggestionsChunk",
    "ModelProvider",
    "PROVIDERS_MODELS_MAP",
    "USE_CASES_MODELS_MAP",
    "SAAS_PROMPT_MODEL_MAP",
]


class ModelProvider(StrEnum):
    VERTEX_AI = "vertex-ai"
    ANTHROPIC = "anthropic"
    LITELLM = "litellm"


class KindUseCase(StrEnum):
    CODE_COMPLETIONS = "code completions"
    CODE_GENERATIONS = "code generations"


PROVIDERS_MODELS_MAP = {
    KindModelProvider.ANTHROPIC: set(KindAnthropicModel),
    KindModelProvider.VERTEX_AI: set(KindVertexTextModel),
    KindModelProvider.LITELLM: set(KindLiteLlmModel),
    KindModelProvider.MISTRALAI: set(KindLiteLlmModel),
    KindModelProvider.FIREWORKS: set(KindLiteLlmModel),
    KindModelProvider.AMAZON_Q: set(KindAmazonQModel),
    KindModelProvider.GITLAB: set(KindGitLabModel),
}

USE_CASES_MODELS_MAP = {
    KindUseCase.CODE_COMPLETIONS: {
        KindAnthropicModel.CLAUDE_3_5_SONNET,
        KindAnthropicModel.CLAUDE_3_5_HAIKU,
        KindAnthropicModel.CLAUDE_3_5_SONNET_V2,
        KindVertexTextModel.CODE_GECKO_002,
        KindVertexTextModel.CODESTRAL_2501,
        KindLiteLlmModel.CODESTRAL_2501,
        KindLiteLlmModel.CODEGEMMA,
        KindLiteLlmModel.CODELLAMA,
        KindLiteLlmModel.CODESTRAL,
        KindLiteLlmModel.DEEPSEEKCODER,
        KindLiteLlmModel.LLAMA3,
        KindLiteLlmModel.MISTRAL,
        KindLiteLlmModel.MIXTRAL,
        KindLiteLlmModel.CLAUDE_3,
        KindLiteLlmModel.GPT,
        KindLiteLlmModel.QWEN_2_5,
        KindAmazonQModel.AMAZON_Q,
        KindGitLabModel.CODESTRAL_2501_FIREWORKS,
        KindGitLabModel.CODESTRAL_2501_VERTEX,
        KindGitLabModel.CLAUDE_SONNET_3_7,
        KindGitLabModel.CLAUDE_3_5_SONNET,
        KindGitLabModel.CLAUDE_3_5_HAIKU,
        KindGitLabModel.GITLAB_DEFAULT_MODEL,
    },
    KindUseCase.CODE_GENERATIONS: {
        KindVertexTextModel.CODE_BISON_002,
        KindVertexTextModel.GEMINI_2_5_FLASH,
        KindAnthropicModel.CLAUDE_3_SONNET,
        KindAnthropicModel.CLAUDE_3_5_SONNET,
        KindAnthropicModel.CLAUDE_3_HAIKU,
        KindAnthropicModel.CLAUDE_3_5_HAIKU,
        KindAnthropicModel.CLAUDE_3_5_SONNET_V2,
        KindLiteLlmModel.CODEGEMMA,
        KindLiteLlmModel.CODELLAMA,
        KindLiteLlmModel.CODESTRAL,
        KindLiteLlmModel.DEEPSEEKCODER,
        KindLiteLlmModel.LLAMA3,
        KindLiteLlmModel.MISTRAL,
        KindLiteLlmModel.MIXTRAL,
        KindLiteLlmModel.CLAUDE_3,
        KindLiteLlmModel.GPT,
        KindLiteLlmModel.CLAUDE_3_5,
        KindAmazonQModel.AMAZON_Q,
    },
}

SAAS_PROMPT_MODEL_MAP = {
    "^1.0.0": {
        "model_provider": ModelProvider.ANTHROPIC,
        "model_version": KindAnthropicModel.CLAUDE_3_5_SONNET_V2,
    },
    "1.0.0": {
        "model_provider": ModelProvider.ANTHROPIC,
        "model_version": KindAnthropicModel.CLAUDE_3_5_SONNET,
    },
    "1.1.0-dev": {
        "model_provider": ModelProvider.ANTHROPIC,
        "model_version": KindAnthropicModel.CLAUDE_SONNET_4,
    },
    "1.2.0-dev": {
        "model_provider": ModelProvider.VERTEX_AI,
        "model_version": KindVertexTextModel.GEMINI_2_5_FLASH,
    },
    "3.0.2-dev": {
        "model_provider": ModelProvider.ANTHROPIC,
        "model_version": KindAnthropicModel.CLAUDE_3_7_SONNET,
    },
    "2.0.0": {
        "model_provider": ModelProvider.VERTEX_AI,
        "model_version": KindAnthropicModel.CLAUDE_3_5_SONNET,
    },
    "2.0.1": {
        "model_provider": ModelProvider.VERTEX_AI,
        "model_version": KindAnthropicModel.CLAUDE_3_5_SONNET_V2,
    },
    "2.0.2-dev": {
        "model_provider": ModelProvider.VERTEX_AI,
        "model_version": KindAnthropicModel.CLAUDE_3_5_SONNET_V2,
    },
}


class CodeSuggestionsOutput(NamedTuple):
    class Metadata(NamedTuple):  # type: ignore[misc]
        tokens_consumption_metadata: Optional[TokensConsumptionMetadata] = None

    text: str
    model: ModelMetadata
    score: Optional[float] = None
    lang_id: Optional[LanguageId] = None
    metadata: Optional["CodeSuggestionsOutput.Metadata"] = None  # type: ignore[name-defined]

    @property
    def lang(self) -> str:
        return self.lang_id.name.lower() if self.lang_id else ""


class CodeSuggestionsChunk(NamedTuple):
    text: str


def resolve_lang_id(file_name: str, editor_lang: Optional[str] = None) -> Optional[LanguageId]:
    lang_id = lang_from_filename(file_name)

    if lang_id is None and editor_lang:
        lang_id = lang_from_editor_lang(editor_lang)

    return lang_id


def resolve_lang_name(file_name: str) -> Optional[str]:
    lang_name = lang_name_from_filename(file_name)

    return lang_name


def increment_lang_counter(
    filename: str,
    lang_id: Optional[LanguageId] = None,
    editor_lang_id: Optional[str] = None,
):
    labels: dict[str, Optional[str]] = {"lang": None, "editor_lang": None}

    if lang_id:
        labels["lang"] = lang_id.name.lower()

    if editor_lang_id:
        labels["editor_lang"] = editor_lang_id

    labels["extension"] = Path(filename).suffix[1:]

    LANGUAGE_COUNTER.labels(**labels).inc()
