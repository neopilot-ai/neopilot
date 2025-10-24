import os
from typing import Annotated, Optional, Set, TypedDict

import litellm
from dotenv import find_dotenv
from pydantic import BaseModel, Field, RootModel
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "Config",
    "ConfigLogging",
    "ConfigFastApi",
    "ConfigAuth",
    "ConfigGoogleCloudProfiler",
    "ConfigSnowplow",
    "ConfigInstrumentator",
    "ConfigVertexTextModel",
    "ConfigModelLimits",
    "ConfigCustomModels",
    "ConfigModelKeys",
    "ConfigModelEndpoints",
]

ENV_PREFIX = "AIGW"


class ConfigLogging(BaseModel):
    level: str = "INFO"
    format_json: bool = True
    to_file: Optional[str] = None
    enable_request_logging: bool = False
    enable_litellm_logging: bool = False


class ConfigSelfSignedJwt(BaseModel):
    signing_key: str = ""
    validation_key: str = ""


class ConfigFastApi(BaseModel):
    api_host: str = "0.0.0.0"
    api_port: int = 5000
    metrics_host: str = "0.0.0.0"
    metrics_port: int = 8082
    uvicorn_logger: dict = {"version": 1, "disable_existing_loggers": False}
    docs_url: Optional[str] = None
    openapi_url: Optional[str] = None
    redoc_url: Optional[str] = None
    reload: bool = False


class ConfigAuth(BaseModel):
    bypass_external: bool = False
    bypass_external_with_header: bool = False
    bypass_jwt_signature: bool = False


class ConfigGoogleCloudProfiler(BaseModel):
    enabled: bool = False
    verbose: int = 2
    period_ms: int = 10


class ConfigInstrumentator(BaseModel):
    thread_monitoring_enabled: bool = False
    thread_monitoring_interval: int = 60


class ConfigInternalEvent(BaseModel):
    enabled: bool = False
    app_id: str = "gitlab_ai_gateway"
    namespace: str = "gl"
    endpoint: Optional[str] = None
    batch_size: Optional[int] = 1
    thread_count: Optional[int] = 1


class ConfigBillingEvent(BaseModel):
    enabled: bool = False
    app_id: str = "gitlab_ai_gateway"
    namespace: str = "gl"
    endpoint: Optional[str] = None
    batch_size: Optional[int] = 1
    thread_count: Optional[int] = 1


# TODO: Migrate to InternalEvent
# See https://github.com/neopilot-ai/neopilot/-/issues/698
class ConfigSnowplow(ConfigInternalEvent):
    enabled: bool = False
    endpoint: Optional[str] = None
    batch_size: Optional[int] = 1
    thread_count: Optional[int] = 1


class ConfigCustomModels(BaseModel):
    enabled: bool = False
    disable_streaming: bool = False


class ConfigAbuseDetection(BaseModel):
    enabled: bool = False
    sampling_rate: float = 0.1  # 1/10 of requests are sampled


class ConfigModelKeys(BaseModel):
    mistral_api_key: Optional[str] = None
    fireworks_api_key: Optional[str] = None


def _build_location(default: str = "us-central1") -> str:
    """Reads the GCP region from the environment.

    Returns the default argument when not configured.
    """
    # pylint: disable=direct-environment-variable-reference
    return os.getenv("RUNWAY_REGION", default)
    # pylint: enable=direct-environment-variable-reference


def _build_endpoint() -> str:
    """Returns the default endpoint for Vertex AI.

    This code assumes that the Runway region (i.e. Cloud Run region) is the same as the Vertex AI region. To support
    other Cloud Run regions, this code will need to be updated to map to a nearby Vertex AI region instead.
    """
    return f"{_build_location()}-aiplatform.googleapis.com"


class ConfigModelEndpoints(BaseModel):
    def update_fireworks_current_region_endpoint(self, location: str):
        regional_endpoints = self.fireworks_regional_endpoints or {}

        matching_regions = [region for region in regional_endpoints if location.startswith(region)]
        # Default to us if configuration not found for this region
        selected_region = matching_regions[0] if matching_regions else "us"
        self.fireworks_current_region_endpoint = regional_endpoints.get(selected_region, {})

    # legacy, unused
    fireworks_completion_endpoint: Optional[str] = None
    fireworks_completion_identifier: Optional[str] = None
    # current per-region configuration
    fireworks_regional_endpoints: Optional[dict[str, dict[str, dict[str, str]]]] = {}
    # dynamic based on GCP location
    fireworks_current_region_endpoint: Optional[dict[str, dict[str, str]]] = {}


class ConfigGoogleCloudPlatform(BaseModel):
    project: str = ""
    service_account_json_key: str = ""
    location: str = Field(default_factory=_build_location)


class ConfigVertexTextModel(ConfigGoogleCloudPlatform):
    endpoint: str = Field(default_factory=_build_endpoint)


class ConfigVertexSearch(ConfigGoogleCloudPlatform):
    fallback_datastore_version: str = ""


class ConfigAmazonQ(BaseModel):
    region: str = ""
    endpoint_url: str = ""


class ConfigFeatureFlags(BaseModel):
    disallowed_flags: dict[str, Set[str]] = {}
    excl_post_process: list[str] = []
    fireworks_score_threshold: dict[str, float] = {}


class ModelLimits(TypedDict, total=False):
    concurrency: int
    input_tokens: int
    output_tokens: int


class ConfigModelLimits(RootModel):
    root: dict[str, dict[str, ModelLimits]] = {}

    def for_model(self, engine: str, name: str) -> Optional[ModelLimits]:
        return self.root.get(engine, {}).get(name, None)


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_prefix=f"{ENV_PREFIX}_",
        protected_namespaces=(),
        env_file=find_dotenv(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "production"
    gitlab_url: str = "https://gitlab.com"
    gitlab_api_url: str = "https://gitlab.com/api/v4/"
    customer_portal_url: str = "https://customers.gitlab.com"
    glgo_base_url: str = "http://auth.token.gitlab.com"
    cloud_connector_service_name: str = "gitlab-ai-gateway"
    mock_model_responses: bool = False
    use_agentic_mock: bool = False

    logging: Annotated[ConfigLogging, Field(default_factory=ConfigLogging)] = ConfigLogging()
    self_signed_jwt: Annotated[ConfigSelfSignedJwt, Field(default_factory=ConfigSelfSignedJwt)] = ConfigSelfSignedJwt()
    fastapi: Annotated[ConfigFastApi, Field(default_factory=ConfigFastApi)] = ConfigFastApi()
    auth: Annotated[ConfigAuth, Field(default_factory=ConfigAuth)] = ConfigAuth()
    google_cloud_profiler: Annotated[ConfigGoogleCloudProfiler, Field(default_factory=ConfigGoogleCloudProfiler)] = (
        ConfigGoogleCloudProfiler()
    )
    instrumentator: Annotated[ConfigInstrumentator, Field(default_factory=ConfigInstrumentator)] = (
        ConfigInstrumentator()
    )
    snowplow: Annotated[ConfigSnowplow, Field(default_factory=ConfigSnowplow)] = ConfigSnowplow()
    internal_event: Annotated[ConfigInternalEvent, Field(default_factory=ConfigInternalEvent)] = ConfigInternalEvent()
    billing_event: Annotated[ConfigBillingEvent, Field(default_factory=ConfigBillingEvent)] = ConfigBillingEvent()
    google_cloud_platform: Annotated[ConfigGoogleCloudPlatform, Field(default_factory=ConfigGoogleCloudPlatform)] = (
        ConfigGoogleCloudPlatform()
    )
    amazon_q: Annotated[ConfigAmazonQ, Field(default_factory=ConfigAmazonQ)] = ConfigAmazonQ()
    custom_models: Annotated[ConfigCustomModels, Field(default_factory=ConfigCustomModels)] = ConfigCustomModels()
    model_keys: Annotated[ConfigModelKeys, Field(default_factory=ConfigModelKeys)] = ConfigModelKeys()
    model_endpoints: Annotated[ConfigModelEndpoints, Field(default_factory=ConfigModelEndpoints)] = (
        ConfigModelEndpoints()
    )
    vertex_text_model: Annotated[ConfigVertexTextModel, Field(default_factory=ConfigVertexTextModel)] = (
        ConfigVertexTextModel()
    )
    vertex_search: Annotated[ConfigVertexSearch, Field(default_factory=ConfigVertexSearch)] = ConfigVertexSearch()
    model_engine_limits: Annotated[ConfigModelLimits, Field(default_factory=ConfigModelLimits)] = ConfigModelLimits()
    abuse_detection: Annotated[ConfigAbuseDetection, Field(default_factory=ConfigAbuseDetection)] = (
        ConfigAbuseDetection()
    )
    feature_flags: Annotated[ConfigFeatureFlags, Field(default_factory=ConfigFeatureFlags)] = ConfigFeatureFlags()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._apply_global_configs(
            parent=self.google_cloud_platform,
            children=[self.vertex_text_model, self.vertex_search],
        )

        # pylint: disable=direct-environment-variable-reference
        os.environ["CLOUD_CONNECTOR_SERVICE_NAME"] = self.cloud_connector_service_name
        # pylint: enable=direct-environment-variable-reference

        self.model_endpoints.update_fireworks_current_region_endpoint(self.google_cloud_platform.location)

    def _apply_global_configs(self, parent: BaseModel, children: list[BaseModel]):
        """Set a parent config to child configs if the field value is not specified."""
        for field in parent.model_fields_set:
            parent_value = getattr(parent, field)

            if not parent_value:
                continue

            for child in children:
                if field in child.model_fields_set:
                    continue

                setattr(child, field, parent_value)


def setup_litellm(config: Config):
    litellm.vertex_project = config.google_cloud_platform.project
