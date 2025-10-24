from __future__ import annotations

import copy
import logging
import sys
from pathlib import Path

import litellm
import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from lib.feature_flags import FeatureFlag, is_feature_enabled
from lib.verbose_ai_logs import enabled_instance_verbose_ai_logs
from structlog.types import EventDict, Processor

from neopilot.ai_gateway.config import ConfigLogging
from neopilot.ai_gateway.model_metadata import ModelMetadata

access_logger = structlog.stdlib.get_logger("api.access")
ENABLE_REQUEST_LOGGING = False
CUSTOM_MODELS_ENABLED = False


# https://github.com/hynek/structlog/issues/35#issuecomment-591321744
def rename_event_key(_, __, event_dict: EventDict) -> EventDict:
    """Log entries keep the text message in the `event` field, but Elasticsearch uses the `message` field.

    This processor moves the value from one field to the other. See
    https://github.com/hynek/structlog/issues/35#issuecomment-591321744
    """
    event_dict["message"] = event_dict.pop("event")

    return event_dict


def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """Uvicorn logs the message a second time in the extra `color_message`, but we don't need it.

    This processor drops the key from the event dict if it exists.
    """
    event_dict.pop("color_message", None)
    return event_dict


def add_custom_keys(_, __, event_dict: EventDict) -> EventDict:
    """Add fields that are expected by our logging infrastructure."""
    event_dict["type"] = "mlops"
    event_dict["stage"] = "main"
    return event_dict


def setup_app_logging(app: FastAPI):
    app.add_middleware(CorrelationIdMiddleware, validator=None)


def setup_logging(
    logging_config: ConfigLogging,
    custom_models_enabled: bool,
    cache_logger_on_first_use: bool = True,
):
    global ENABLE_REQUEST_LOGGING  # pylint: disable=global-statement
    global CUSTOM_MODELS_ENABLED  # pylint: disable=global-statement
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    ENABLE_REQUEST_LOGGING = logging_config.enable_request_logging
    CUSTOM_MODELS_ENABLED = custom_models_enabled

    if logging_config.enable_litellm_logging:
        litellm._turn_on_debug()

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        add_custom_keys,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    if logging_config.format_json:
        # We rename the `event` key to `message` only in JSON logs, as Elasticsearch looks for the
        # `message` key but the pretty ConsoleRenderer looks for `event`
        shared_processors.append(rename_event_key)
        # Format the exception only for JSON logs, as we want to pretty-print them when
        # using the ConsoleRenderer
        shared_processors.append(structlog.processors.format_exc_info)

    structlog.configure(
        processors=shared_processors
        + [
            # Prepare event dict for `ProcessorFormatter`.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=cache_logger_on_first_use,
    )

    log_renderer: structlog.types.Processor
    if logging_config.format_json:
        log_renderer = structlog.processors.JSONRenderer()
    else:
        log_renderer = structlog.dev.ConsoleRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        # These run ONLY on `logging` entries that do NOT originate within
        # structlog.
        foreign_pre_chain=shared_processors,
        # These run on ALL entries after the pre_chain is done.
        processors=[
            # Remove _record & _from_structlog.
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
    )

    handler: logging.Handler
    if logging_config.to_file:
        file = Path(logging_config.to_file).resolve()
        handler = logging.FileHandler(filename=str(file), mode="a")
    else:
        handler = logging.StreamHandler()

    # Use OUR `ProcessorFormatter` to format all `logging` entries.
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()

    # `snowplow_tracker` calls logging.basicConfig(), which adds a handler
    # to the root logger, in multiple places. To avoid having duplicate
    # messages in the root logger, clear out its handlers.
    root_logger.handlers.clear()

    root_logger.addHandler(handler)
    root_logger.setLevel(logging_config.level.upper())

    for _log in ["uvicorn", "uvicorn.error"]:
        # Clear the log handlers for uvicorn loggers, and enable propagation
        # so the messages are caught by our root logger and formatted correctly
        # by structlog
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True

    # Since we re-create the access logs ourselves, to add all
    # information in the structured log, we clear the handlers and
    # prevent the logs to propagate to a logger higher up in the
    # hierarchy (effectively rendering them silent).
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False

    def handle_exception(exc_type, exc_value, exc_traceback):
        """
        Log any uncaught exception instead of letting it be printed by Python
        (but leave KeyboardInterrupt untouched to allow users to Ctrl+C to stop)
        See https://stackoverflow.com/a/16993115/3641865
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        root_logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception


def can_log_request_data():
    return (
        ENABLE_REQUEST_LOGGING
        or (CUSTOM_MODELS_ENABLED and enabled_instance_verbose_ai_logs())
        or (not CUSTOM_MODELS_ENABLED and is_feature_enabled(FeatureFlag.EXPANDED_AI_LOGGING))
    )


def prevent_logging_if_disabled(_, __, event_dict: EventDict) -> EventDict:
    if can_log_request_data():
        return event_dict

    raise structlog.DropEvent


def sanitize_logs(_, __, event_dict: EventDict) -> EventDict:
    sanitized_value = "*" * 10

    event_dict["api_key"] = sanitized_value if "api_key" in event_dict else None

    if "inputs" in event_dict and hasattr(event_dict["inputs"], "model_metadata"):
        sanitized_inputs = copy.copy(event_dict["inputs"])

        if sanitized_inputs.model_metadata:
            model_metadata = copy.copy(sanitized_inputs.model_metadata)

            if isinstance(model_metadata, ModelMetadata):
                model_metadata.api_key = sanitized_value if model_metadata.api_key else None

            sanitized_inputs.model_metadata = model_metadata

        event_dict["inputs"] = sanitized_inputs

    return event_dict


def get_request_logger(name: str):
    return structlog.wrap_logger(
        structlog.get_logger(name),
        processors=[prevent_logging_if_disabled, sanitize_logs],
    )
