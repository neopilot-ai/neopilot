from typing import Any, NamedTuple, Optional

from starlette_context import context

from neopilot.ai_gateway.code_suggestions.processing import ModelEngineBase

__all__ = [
    "CodeCompletionsInternalUseCase",
]


class CodeCompletionsInternalModel(NamedTuple):
    # TODO: replace with enum values
    engine: str
    name: str
    lang: str


class CodeCompletionsInternal(NamedTuple):

    text: str
    model: CodeCompletionsInternalModel
    finish_reason: str = "length"


class CodeCompletionsInternalUseCase:
    def __init__(self, engine: ModelEngineBase):
        self.engine = engine

    async def __call__(
        self, prefix: str, suffix: str, file_name: Optional[str] = None, **kwargs: Any
    ) -> list[CodeCompletionsInternal]:
        file_name = file_name if file_name else ""

        completions = await self.engine.generate(
            prefix,
            suffix,
            file_name,
            **kwargs,
        )

        return [
            CodeCompletionsInternal(
                text=c.text,
                model=CodeCompletionsInternalModel(
                    # TODO: return props from the target engine instead of using glob var
                    engine=context.get("model_engine", ""),
                    name=context.get("model_name", ""),
                    lang=c.lang,
                ),
            )
            for c in completions
        ]
