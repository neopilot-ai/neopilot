from typing import Any, AsyncIterator, Callable, NamedTuple, Optional

import structlog

from neopilot.ai_gateway.code_suggestions.processing.base import (
    MINIMUM_CONFIDENCE_SCORE,
    ModelEngineBase,
    ModelEngineOutput,
    PromptBuilderBase,
)
from neopilot.ai_gateway.code_suggestions.processing.ops import remove_incomplete_block
from neopilot.ai_gateway.code_suggestions.processing.typing import (
    CodeContent,
    LanguageId,
    MetadataCodeContent,
    MetadataExtraInfo,
    MetadataPromptBuilder,
    Prompt,
)
from neopilot.ai_gateway.code_suggestions.prompts.parsers import CodeParser
from neopilot.ai_gateway.instrumentators import TextGenModelInstrumentator
from neopilot.ai_gateway.models import VertexAPIConnectionError, VertexAPIStatusError
from neopilot.ai_gateway.models.base import TokensConsumptionMetadata

log = structlog.stdlib.get_logger("codesuggestions")

__all__ = [
    "ModelEngineCompletions",
]

_KEY_EXAMPLE_LANG_ID = {
    "python": LanguageId.PYTHON,
}


class _CodeBody(NamedTuple):
    prefix: CodeContent
    suffix: CodeContent


class _CodeInfo(NamedTuple):
    content: list[CodeContent]

    @property
    def total_length_tokens(self):
        return sum(info.length_tokens for info in self.content)

    @property
    def total_length(self):
        return sum(len(info.text) for info in self.content)


def _double_slash_comment(comment: str) -> str:
    return f"// {comment}"


# TODO: Convert these to templates later
COMMENT_GENERATOR: dict[LanguageId, Callable[[str], str]] = {
    LanguageId.C: lambda comment: f"/* {comment} */",
    LanguageId.CPP: _double_slash_comment,
    LanguageId.CSHARP: _double_slash_comment,
    LanguageId.GO: _double_slash_comment,
    LanguageId.JAVA: _double_slash_comment,
    LanguageId.JS: _double_slash_comment,
    LanguageId.PHP: _double_slash_comment,
    LanguageId.PYTHON: lambda comment: f"# {comment}",
    LanguageId.RUBY: lambda comment: f"# {comment}",
    LanguageId.RUST: _double_slash_comment,
    LanguageId.SCALA: _double_slash_comment,
    LanguageId.TS: _double_slash_comment,
    LanguageId.KOTLIN: _double_slash_comment,
}


class _PromptBuilder(PromptBuilderBase):
    LANG_ID_TO_HUMAN_NAME = {
        LanguageId.C: "C",
        LanguageId.CPP: "C++",
        LanguageId.CSHARP: "C#",
        LanguageId.GO: "Go",
        LanguageId.JAVA: "Java",
        LanguageId.JS: "JavaScript",
        LanguageId.PHP: "PHP",
        LanguageId.PYTHON: "Python",
        LanguageId.RUBY: "Ruby",
        LanguageId.RUST: "Rust",
        LanguageId.SCALA: "Scala",
        LanguageId.TS: "TypeScript",
        LanguageId.KOTLIN: "Kotlin",
    }

    def __init__(
        self,
        prefix: CodeContent,
        suffix: CodeContent,
        file_name: str,
        lang_id: Optional[LanguageId] = None,
    ):
        super().__init__(prefix, suffix, lang_id)

        self.file_name = file_name

    def add_extra_info(self, extra_info: _CodeInfo, max_total_length_tokens: int, extra_info_name: str):
        total_length_tokens = 0
        tokens_used = 0
        total_length = 0

        # Only prepend the info if it's not present and we have room
        for info in extra_info.content:
            if info.text in self._prefix or info.text in self._suffix:
                continue

            total_length += len(info.text)
            total_length_tokens += info.length_tokens
            if max_total_length_tokens - total_length_tokens >= 0:
                self._prefix = f"{info.text}\n{self._prefix}"
                tokens_used = total_length_tokens

        self._metadata[extra_info_name] = MetadataExtraInfo(
            name=extra_info_name,
            pre=MetadataCodeContent(
                length=extra_info.total_length,
                length_tokens=extra_info.total_length_tokens,
            ),
            post=MetadataCodeContent(
                length=total_length,
                length_tokens=tokens_used,
            ),
        )

    def _prepend_comments(self) -> str:
        if self.lang_id not in COMMENT_GENERATOR:
            header = f"This code has a filename of {self.file_name}"
            return f"{header}\n{self._prefix}"

        comment = COMMENT_GENERATOR[self.lang_id]
        language = self.LANG_ID_TO_HUMAN_NAME[self.lang_id]
        header = comment(f"This code has a filename of {self.file_name} and is written in {language}.")
        return f"{header}\n{self._prefix}"

    def build(self) -> Prompt:
        new_prefix = self._prepend_comments()
        components = {}

        for key in ("prefix", "suffix"):
            value = self._metadata.get(key)
            if isinstance(value, MetadataCodeContent):
                components[key] = value

        imports_val = self._metadata.get("imports")
        imports = imports_val if isinstance(imports_val, MetadataExtraInfo) else None
        function_signatures_val = self._metadata.get("function_signatures")
        function_signatures = (
            function_signatures_val if isinstance(function_signatures_val, MetadataExtraInfo) else None
        )
        code_context_val = self._metadata.get("code_context")
        code_context = code_context_val if isinstance(code_context_val, MetadataExtraInfo) else None

        return Prompt(
            prefix=new_prefix,
            suffix=self._suffix,
            metadata=MetadataPromptBuilder(
                components=components,
                imports=imports,
                function_signatures=function_signatures,
                code_context=code_context,
            ),
        )


class ModelEngineCompletions(ModelEngineBase):
    MAX_TOKENS_IMPORTS_PERCENT = 0.12  # about 245 tokens for code-gecko
    MAX_TOKENS_SUFFIX_PERCENT = 0.07  # about 126 tokens for code-gecko, if "imports" takes up all the available space
    MAX_TOKENS_CONTEXT_PERCENT = 0.5  # about 1024 tokens for code-gecko

    async def _generate(
        self,
        prefix: str,
        suffix: str,
        file_name: str,
        lang_id: Optional[LanguageId] = None,
        editor_lang: Optional[str] = None,
        **kwargs: Any,
    ) -> list[ModelEngineOutput]:
        prompt = await self._build_prompt(prefix, file_name, suffix, lang_id, kwargs.get("code_context"))

        empty_output = [
            ModelEngineOutput(
                text="",
                score=0,
                model=self.model.metadata,
                metadata=MetadataPromptBuilder(components={}),
                tokens_consumption_metadata=TokensConsumptionMetadata(input_tokens=0, output_tokens=0),
            ),
        ]

        # TODO: keep watching the suffix length until logging ModelEngineOutput in the upper layer
        with self.instrumentator.watch(prompt, suffix_length=len(suffix)) as watch_container:
            try:
                # count symbols of the final prompt
                await self._count_symbols(prompt.get_normalized_prefix(), watch_container, lang_id)

                watch_container.register_lang(lang_id, editor_lang)

                if responses := await self.model.generate(
                    prompt.get_normalized_prefix(),
                    prompt.suffix if prompt.suffix else "",
                    **kwargs,
                ):
                    # TODO: Handle streamed output separately or ignore for now
                    if isinstance(responses, AsyncIterator):
                        log.warning("Streaming responses not yet handled in _generate")
                        return empty_output

                    if not isinstance(responses, list):
                        responses = [responses]

                    outputs = []
                    for res in responses:
                        watch_container.register_model_output_length(res.text)
                        watch_container.register_model_score(res.score)
                        watch_container.register_safety_attributes(res.safety_attributes)

                        if res.score is not None and res.score > MINIMUM_CONFIDENCE_SCORE:
                            completion = res.text
                        else:
                            watch_container.register_is_discarded()
                            completion = ""
                        context_tokens_sent = 0
                        context_tokens_used = 0
                        code_context = prompt.metadata.code_context
                        if isinstance(code_context, MetadataExtraInfo):
                            context_tokens_sent = code_context.pre.length_tokens
                            context_tokens_used = code_context.post.length_tokens

                        if res.metadata:
                            tokens_consumption_metadata = res.metadata
                            tokens_consumption_metadata.context_tokens_used = context_tokens_used
                            tokens_consumption_metadata.context_tokens_sent = context_tokens_sent
                            log.debug(
                                "token consumption metadata:",
                                metadata=tokens_consumption_metadata.model_dump(),
                            )
                        else:
                            log.debug("code completions: token consumption metadata is not available, using estimates")

                            tokens_consumption_metadata = TokensConsumptionMetadata(
                                output_tokens=self.tokenization_strategy.estimate_length(completion)[0],
                                input_tokens=sum(md.length_tokens for md in prompt.metadata.components.values()),
                                context_tokens_used=context_tokens_used,
                                context_tokens_sent=context_tokens_sent,
                            )
                            log.debug(
                                "token consumption metadata:",
                                metadata=tokens_consumption_metadata.model_dump(),
                            )
                        outputs.append(
                            ModelEngineOutput(
                                text=completion,
                                score=res.score if res.score is not None else 0.0,
                                model=self.model.metadata,
                                lang_id=lang_id,
                                metadata=prompt.metadata,
                                tokens_consumption_metadata=tokens_consumption_metadata,
                            )
                        )
                    return outputs
            except (VertexAPIConnectionError, VertexAPIStatusError) as ex:
                code = getattr(ex, "code", None)
                watch_container.register_model_exception(str(ex), code)
                raise

        return empty_output

    async def _build_prompt(
        self,
        prefix: str,
        file_name: str,
        suffix: str,
        lang_id: Optional[LanguageId] = None,
        code_context: Optional[list] = None,
    ) -> Prompt:
        imports = await self._get_imports(prefix, lang_id)
        prompt_len_imports_max = int(self.model.input_token_limit * self.MAX_TOKENS_IMPORTS_PERCENT)
        prompt_len_imports = min(imports.total_length_tokens, prompt_len_imports_max)

        func_signatures = await self._get_function_signatures(suffix, lang_id)
        prompt_len_func_signatures = min(func_signatures.total_length_tokens, 1024)  # max 1024 tokens

        prompt_len_body = self.model.input_token_limit - prompt_len_imports - prompt_len_func_signatures

        body = self._get_body(prefix, suffix, prompt_len_body)

        prompt_builder = _PromptBuilder(body.prefix, body.suffix, file_name, lang_id)
        # NOTE that the last thing we add here will appear first in the prefix
        prompt_builder.add_extra_info(
            func_signatures,
            prompt_len_func_signatures,
            extra_info_name="function_signatures",
        )
        prompt_builder.add_extra_info(imports, prompt_len_imports, extra_info_name="imports")

        # Add code context
        if code_context:
            prompt_context_imports_max = int(self.model.input_token_limit * self.MAX_TOKENS_CONTEXT_PERCENT)
            code_context_info = self._to_code_info(code_context, lang_id, as_comments=False)
            code_context_len = min(code_context_info.total_length_tokens, prompt_context_imports_max)
            prompt_builder.add_extra_info(
                code_context_info,
                code_context_len,
                extra_info_name="code_context",
            )

        prompt = prompt_builder.build()

        return prompt

    async def _get_imports(self, content: str, lang_id: Optional[LanguageId] = None) -> _CodeInfo:
        imports = await self._extract(content, "imports", lang_id)
        return self._to_code_info(imports, lang_id, as_comments=False)

    async def _get_function_signatures(self, content: str, lang_id: Optional[LanguageId] = None) -> _CodeInfo:
        signatures = await self._extract(content, "function_signatures", lang_id)
        return self._to_code_info(signatures, lang_id, as_comments=True)

    @staticmethod
    async def _extract(content: str, target: str, lang_id: Optional[LanguageId] = None) -> list[str]:
        extracted = []
        if lang_id:
            try:
                parser = await CodeParser.from_language_id(content, lang_id)
                if target == "imports":
                    extracted = parser.imports()
                elif target == "function_signatures":
                    extracted = parser.function_signatures()
                else:
                    raise ValueError(f"Unknown extraction target {target}")
            except ValueError as e:
                log.warning(f"Failed to parse code: {e}")

        return extracted

    def _to_code_info(
        self,
        contents: list[str],
        lang_id: Optional[LanguageId] = None,
        as_comments: bool = True,
    ) -> _CodeInfo:
        """Convert a list of code snippets into `_CodeInfo`, which includes metadata like text length and token
        length."""
        if len(contents) == 0:
            return _CodeInfo(content=[])

        if as_comments and lang_id is not None and lang_id in COMMENT_GENERATOR:
            comment_converter = COMMENT_GENERATOR[lang_id]
            contents = [comment_converter(content) for content in contents]

        content_lengths = self.tokenization_strategy.estimate_length(contents)

        code_contents = [
            CodeContent(text=text, length_tokens=length) for text, length in zip(contents, content_lengths)
        ]

        return _CodeInfo(content=code_contents)

    def _get_body(self, prefix: str, suffix: str, max_length: int) -> _CodeBody:
        suffix_len = int(max_length * self.MAX_TOKENS_SUFFIX_PERCENT)
        suffix_truncated = self.tokenization_strategy.truncate_content(
            suffix,
            max_length=suffix_len,
            truncation_side="right",
        )

        prefix_len = max_length - suffix_truncated.length_tokens
        prefix_truncated = self.tokenization_strategy.truncate_content(
            prefix,
            max_length=prefix_len,
            truncation_side="left",
        )

        prefix_trimmed = CodeContent(
            text=remove_incomplete_block(prefix_truncated.text),
            length_tokens=prefix_truncated.length_tokens,
        )

        return _CodeBody(prefix=prefix_trimmed, suffix=suffix_truncated)

    async def _count_symbols(
        self,
        prompt: str,
        watch_container: TextGenModelInstrumentator.WatchContainer,
        lang_id: Optional[LanguageId] = None,
    ) -> None:
        try:
            parser = await CodeParser.from_language_id(prompt, lang_id)
            symbol_map = parser.count_symbols()
            self.increment_code_symbol_counter(symbol_map, lang_id)
            self.log_symbol_map(watch_container, symbol_map)
        except ValueError as e:
            log.warning(f"Failed to parse code: {e}")
