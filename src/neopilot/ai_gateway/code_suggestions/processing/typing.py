from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Mapping, NamedTuple, Optional

__all__ = [
    "LanguageId",
    "MetadataCodeContent",
    "MetadataExtraInfo",
    "MetadataPromptBuilder",
    "CodeContent",
    "Prompt",
    "TokenStrategyBase",
]


class LanguageId(IntEnum):
    C = 1
    CPP = 2
    CSHARP = 3
    GO = 4
    JAVA = 5
    JS = 6
    PHP = 7
    PYTHON = 8
    RUBY = 9
    RUST = 10
    SCALA = 11
    TS = 12
    KOTLIN = 13


class MetadataCodeContent(NamedTuple):
    length: int
    length_tokens: int


class MetadataExtraInfo(NamedTuple):
    name: str
    pre: MetadataCodeContent
    post: MetadataCodeContent


class MetadataPromptBuilder(NamedTuple):
    components: Mapping[str, MetadataCodeContent]
    imports: Optional[MetadataExtraInfo] = None
    function_signatures: Optional[MetadataExtraInfo] = None
    code_context: Optional[MetadataExtraInfo] = None


class CodeContent(NamedTuple):
    text: str
    length_tokens: int


class Prompt(NamedTuple):
    prefix: str | list
    metadata: MetadataPromptBuilder
    suffix: Optional[str] = None

    def get_normalized_prefix(self) -> str:
        if isinstance(self.prefix, list):
            return "".join(map(str, self.prefix))
        return self.prefix


class TokenStrategyBase(ABC):
    @abstractmethod
    def truncate_content(self, text: str, max_length: int, truncation_side: str = "left") -> CodeContent:
        pass

    @abstractmethod
    def estimate_length(self, text: str | list[str]) -> list[int]:
        pass
