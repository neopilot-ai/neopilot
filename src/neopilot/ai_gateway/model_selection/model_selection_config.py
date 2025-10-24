from itertools import chain
from pathlib import Path
from typing import Any, Iterable, Optional

import yaml
from gitlab_cloud_connector import GitLabUnitPrimitive
from pydantic import BaseModel, ConfigDict

BASE_PATH = Path(__file__).parent
MODELS_CONFIG_PATH = BASE_PATH / "models.yml"
UNIT_PRIMITIVE_CONFIG_PATH = BASE_PATH / "unit_primitives.yml"


class LLMDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    gitlab_identifier: str
    params: dict[str, Any] = {}
    family: list[str] = []


class UnitPrimitiveConfig(BaseModel):
    feature_setting: str
    unit_primitives: list[GitLabUnitPrimitive]
    default_model: str
    selectable_models: list[str] = []
    beta_models: list[str] = []


class ModelSelectionConfig:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(ModelSelectionConfig, cls).__new__(cls)
        return cls.__instance

    def __init__(self) -> None:
        self._llm_definitions: Optional[dict[str, LLMDefinition]] = None
        self._unit_primitive_configs: Optional[dict[str, UnitPrimitiveConfig]] = None

    def get_llm_definitions(self) -> dict[str, LLMDefinition]:
        if not self._llm_definitions:

            with open(MODELS_CONFIG_PATH, "r") as f:
                config_data = yaml.safe_load(f)

            self._llm_definitions = {
                model_data["gitlab_identifier"]: LLMDefinition(**model_data) for model_data in config_data["models"]
            }

        return self._llm_definitions

    def get_unit_primitive_config_map(self) -> dict[str, UnitPrimitiveConfig]:
        if not self._unit_primitive_configs:
            with open(UNIT_PRIMITIVE_CONFIG_PATH, "r") as f:
                config_data = yaml.safe_load(f)

            self._unit_primitive_configs = {
                data["feature_setting"]: UnitPrimitiveConfig(**data)
                for data in config_data["configurable_unit_primitives"]
            }

        return self._unit_primitive_configs

    def get_unit_primitive_config(self) -> Iterable[UnitPrimitiveConfig]:
        return self.get_unit_primitive_config_map().values()

    def validate(self) -> None:
        unit_primitive_configs = self.get_unit_primitive_config()
        models = self.get_llm_definitions()
        models_ids = models.keys()

        errors: set[str] = set()
        default_model_not_selectable_errors: list[str] = []

        for unit_primitive_config in unit_primitive_configs:
            ids = chain(
                [unit_primitive_config.default_model],
                unit_primitive_config.selectable_models,
                unit_primitive_config.beta_models,
            )

            errors.update(model_id for model_id in ids if model_id not in models_ids)

            # Validate that the default model is also included in selectable_models
            if unit_primitive_config.default_model not in unit_primitive_config.selectable_models:
                default_model_not_selectable_errors.append(
                    f"Feature '{unit_primitive_config.feature_setting}' has default model "
                    f"'{unit_primitive_config.default_model}' that is not in selectable_models."
                )

        error_messages = []
        if errors:
            error_messages.append(
                f"The following models ids are used but are not defined in models.yml: {', '.join(errors)}"
            )

        if default_model_not_selectable_errors:
            error_messages.append(
                "Default models must be included in selectable_models:\n"
                + "\n".join(f"  - {error}" for error in default_model_not_selectable_errors)
            )

        if error_messages:
            raise ValueError("\n".join(error_messages))

    def refresh(self):
        """Refresh the configuration by reloading from source files."""
        self._llm_definitions = None
        self._unit_primitive_configs = None

    def get_model(self, model_id: str) -> LLMDefinition:
        if model := self.get_llm_definitions().get(model_id, None):
            return model
        raise ValueError(f"Invalid model identifier: {model_id}")

    def get_model_for_feature(self, feature_setting_name: str) -> LLMDefinition:
        if feature_setting := self.get_unit_primitive_config_map().get(feature_setting_name, None):
            return self.get_model(feature_setting.default_model)
        raise ValueError(f"Invalid feature setting: {feature_setting_name}")


def validate_model_selection_config():
    ModelSelectionConfig().validate()
