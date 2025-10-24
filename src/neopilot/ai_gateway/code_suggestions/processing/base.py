from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, NamedTuple, Optional, Union

from prometheus_client import Counter

from neopilot.ai_gateway.code_suggestions.processing.ops import (
    lang_from_editor_lang,
    lang_from_filename,
)
from neopilot.ai_gateway.code_suggestions.processing.typing import (
    CodeContent,
    LanguageId,
    MetadataCodeContent,
    MetadataExtraInfo,
    MetadataPromptBuilder,
    Prompt,
    TokenStrategyBase,
)
from neopilot.ai_gateway.instrumentators import TextGenModelInstrumentator
from neopilot.ai_gateway.models import ModelMetadata, PalmCodeGenBaseModel
from neopilot.ai_gateway.models.base import TokensConsumptionMetadata

__all__ = [
    "ModelEngineOutput",
    "ModelEngineBase",
    "Prompt",
    "PromptBuilderBase",
]

LANGUAGE_COUNTER = Counter(
    "code_suggestions_prompt_language",
    "Language count by number",
    ["lang", "extension", "editor_lang"],
)

CODE_SYMBOL_COUNTER = Counter("code_suggestions_prompt_symbols", "Prompt symbols count", ["lang", "symbol"])

MINIMUM_CONFIDENCE_SCORE = -10


class ModelEngineOutput(NamedTuple):
    text: str
    score: float
    model: ModelMetadata
    metadata: MetadataPromptBuilder
    tokens_consumption_metadata: TokensConsumptionMetadata
    lang_id: Optional[LanguageId] = None

    @property
    def lang(self) -> str:
        return self.lang_id.name.lower() if self.lang_id else ""


class ModelEngineBase(ABC):
    def __init__(self, model: PalmCodeGenBaseModel, tokenization_strategy: TokenStrategyBase):
        self.model = model
        self.tokenization_strategy = tokenization_strategy
        self.instrumentator = TextGenModelInstrumentator(model.metadata.engine, model.metadata.name)

    async def generate(
        self,
        prefix: str,
        suffix: str,
        file_name: str,
        editor_lang_id: Optional[str] = None,
        **kwargs: Any,
    ) -> list[ModelEngineOutput]:
        lang_id = lang_from_filename(file_name)
        self.increment_lang_counter(file_name, lang_id, editor_lang_id)

        if lang_id is None and editor_lang_id:
            lang_id = lang_from_editor_lang(editor_lang_id)

        return await self._generate(prefix, suffix, file_name, lang_id, editor_lang_id, **kwargs)

    def increment_lang_counter(
        self,
        filename: str,
        lang_id: Optional[LanguageId] = None,
        editor_lang_id: Optional[str] = None,
    ):

        labels = {
            "lang": lang_id.name.lower() if lang_id else None,
            "editor_lang": editor_lang_id,
            "extension": Path(filename).suffix[1:],
        }

        LANGUAGE_COUNTER.labels(**labels).inc()

    @abstractmethod
    async def _generate(
        self,
        prefix: str,
        suffix: str,
        file_name: str,
        lang_id: Optional[LanguageId] = None,
        editor_lang: Optional[str] = None,
        **kwargs: Any,
    ) -> list[ModelEngineOutput]:
        pass

    def increment_code_symbol_counter(self, symbol_map: dict, lang_id: Optional[LanguageId] = None):
        for symbol, count in symbol_map.items():
            CODE_SYMBOL_COUNTER.labels(lang=lang_id.name.lower() if lang_id else "", symbol=symbol).inc(count)

    def log_symbol_map(
        self,
        watch_container: TextGenModelInstrumentator.WatchContainer,
        symbol_map: dict,
    ) -> None:
        watch_container.register_prompt_symbols(symbol_map)


class PromptBuilderBase(ABC):
    def __init__(
        self,
        prefix: CodeContent,
        suffix: Optional[CodeContent] = None,
        lang_id: Optional[LanguageId] = None,
    ):
        self.lang_id = lang_id
        self._prefix = prefix.text

        self._metadata: Dict[str, Union[MetadataCodeContent, MetadataExtraInfo]] = {
            "prefix": MetadataCodeContent(
                length=len(prefix.text),
                length_tokens=prefix.length_tokens,
            ),
        }

        if suffix:
            self._suffix = suffix.text
            self._metadata["suffix"] = MetadataCodeContent(
                length=len(suffix.text),
                length_tokens=suffix.length_tokens,
            )

    @abstractmethod
    def build(self) -> Prompt:
        pass
