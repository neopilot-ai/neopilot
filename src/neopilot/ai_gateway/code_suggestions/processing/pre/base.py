from abc import ABC, abstractmethod
from typing import Any, Optional

from neopilot.ai_gateway.code_suggestions.processing.typing import (
    MetadataCodeContent,
    MetadataPromptBuilder,
    Prompt,
    TokenStrategyBase,
)
from neopilot.ai_gateway.code_suggestions.prompts import PromptTemplateBase
from neopilot.ai_gateway.models import Message

__all__ = [
    "PromptBuilderBase",
]


class PromptBuilderBase(ABC):
    def __init__(self, total_max_len: int, tkn_strategy: TokenStrategyBase):
        self.total_max_len = max(total_max_len, 0)
        self.tkn_strategy = tkn_strategy

        self.always_len = 0

        self.tpl: Optional[PromptTemplateBase] = None
        self.tpl_args: dict = {}

    def add_template(self, tpl: PromptTemplateBase, **kwargs: Any) -> int:
        self.tpl = tpl
        self.tpl_args.update(kwargs)

        # Apply all known arguments to get the number of reserved tokens
        tpl_raw = self.tpl.apply(**self.tpl_args)
        tpl_len = self.tkn_strategy.estimate_length(tpl_raw)[0]
        if tpl_len > self.total_max_len:
            raise ValueError("the template size exceeds overall maximum length")

        self.always_len = tpl_len

        return tpl_len

    def wrap(self, prompt: str | list[Message], ignore_exception: bool = False) -> Prompt:
        if isinstance(prompt, list):
            prompt_text = "".join(m.content for m in prompt)
        else:
            prompt_text = prompt
        token_length = self.tkn_strategy.estimate_length(prompt_text)[0]
        if token_length > self.total_max_len and not ignore_exception:
            raise ValueError("the prompt size exceeds overall maximum length")

        return Prompt(
            prefix=prompt,
            metadata=MetadataPromptBuilder(
                components={
                    "prompt": MetadataCodeContent(
                        length=len(prompt_text),
                        length_tokens=token_length,
                    ),
                }
            ),
        )

    @abstractmethod
    def add_content(self, *text: str, **_kwargs: Any):
        pass

    @abstractmethod
    def build(self) -> Prompt:
        pass
