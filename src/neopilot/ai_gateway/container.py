from dependency_injector import containers, providers
from py_grpc_prometheus.prometheus_client_interceptor import PromClientInterceptor

from neopilot.ai_gateway.abuse_detection.container import ContainerAbuseDetection
from neopilot.ai_gateway.auth.container import ContainerSelfSignedJwt
from neopilot.ai_gateway.chat.container import ContainerChat
from neopilot.ai_gateway.code_suggestions.container import ContainerCodeSuggestions
from neopilot.ai_gateway.integrations.container import ContainerIntegrations
from neopilot.ai_gateway.models.container import ContainerModels
from neopilot.ai_gateway.models.v2.container import ContainerModels as ContainerModelsV2
from neopilot.ai_gateway.prompts.container import ContainerPrompts
from neopilot.ai_gateway.searches.container import ContainerSearches
from neopilot.ai_gateway.tracking.container import ContainerTracking
from neopilot.ai_gateway.x_ray.container import ContainerXRay
from lib.billing_events import ContainerBillingEvent
from lib.internal_events import ContainerInternalEvent

__all__ = [
    "ContainerApplication",
]


class ContainerApplication(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)

    interceptor: providers.Singleton = providers.Singleton(
        PromClientInterceptor,
        enable_client_handling_time_histogram=True,
        enable_client_stream_receive_time_histogram=True,
        enable_client_stream_send_time_histogram=True,
    )

    searches = providers.Container(
        ContainerSearches,
        config=config,
    )

    snowplow = providers.Container(ContainerTracking, config=config.snowplow)

    internal_event = providers.Container(ContainerInternalEvent, config=config.internal_event)

    billing_event = providers.Container(
        ContainerBillingEvent,
        config=config.billing_event,
        internal_event=internal_event,
    )

    integrations = providers.Container(
        ContainerIntegrations,
        config=config,
    )

    pkg_models = providers.Container(
        ContainerModels,
        config=config,
        integrations=integrations,
    )
    pkg_models_v2 = providers.Container(
        ContainerModelsV2,
        config=config,
        integrations=integrations,
    )
    pkg_prompts = providers.Container(
        ContainerPrompts,
        models=pkg_models_v2,
        internal_event=internal_event,
        config=config,
    )

    code_suggestions = providers.Container(
        ContainerCodeSuggestions,
        models=pkg_models,
        config=config.feature_flags,
        snowplow=snowplow,
    )
    x_ray = providers.Container(
        ContainerXRay,
        models=pkg_models,
    )
    chat = providers.Container(
        ContainerChat,
        prompts=pkg_prompts,
        models=pkg_models,
        internal_event=internal_event,
        config=config,
    )
    self_signed_jwt = providers.Container(
        ContainerSelfSignedJwt,
        config=config,
    )
    abuse_detection = providers.Container(
        ContainerAbuseDetection,
        config=config.abuse_detection,
        models=pkg_models,
    )
