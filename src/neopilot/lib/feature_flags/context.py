from contextvars import ContextVar
from enum import StrEnum
from typing import Set

__all__ = ["is_feature_enabled", "current_feature_flag_context", "FeatureFlag"]


class FeatureFlag(StrEnum):
    # Definition: https://gitlab.com/gitlab-org/gitlab/-/blob/master/config/feature_flags/ops/expanded_ai_logging.yml
    EXPANDED_AI_LOGGING = "expanded_ai_logging"
    USE_DUO_CONTEXT_EXCLUSION = "use_duo_context_exclusion"
    STREAM_DURING_TOOL_CALL_GENERATION = (
        "duo_workflow_stream_during_tool_call_generation"
    )


def is_feature_enabled(feature_name: FeatureFlag | str) -> bool:
    """Check if a feature is enabled.

    Args:
        feature_name: The name of the feature. See:
        https://github.com/neopilot-ai/neopilot/-/blob/main/docs/feature_flags.md
    """
    enabled_feature_flags: Set[str] = current_feature_flag_context.get()
    if isinstance(feature_name, FeatureFlag):
        feature_name = feature_name.value
    return feature_name in enabled_feature_flags


current_feature_flag_context: ContextVar[Set[str]] = ContextVar(
    "current_feature_flag_context", default=set()
)
