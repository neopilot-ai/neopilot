from __future__ import annotations

from dependency_injector import containers, providers

from neopilot.ai_gateway.tracking.instrumentator import SnowplowInstrumentator
from neopilot.ai_gateway.tracking.snowplow import (SnowplowClient,
                                                   SnowplowClientConfiguration,
                                                   SnowplowClientStub)

__all__ = [
    "ContainerTracking",
]


def _init_snowplow_client(
    enabled: bool, configuration: SnowplowClientConfiguration
) -> SnowplowClient | SnowplowClientStub:
    if not enabled:
        return SnowplowClientStub()

    return SnowplowClient(configuration)


class ContainerTracking(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)

    client = providers.Singleton(
        _init_snowplow_client,
        enabled=config.enabled,
        configuration=providers.Singleton(
            SnowplowClientConfiguration,
            endpoint=config.endpoint,
            batch_size=config.batch_size,
            thread_count=config.thread_count,
        ),
    )

    instrumentator = providers.Singleton(
        SnowplowInstrumentator,
        client=client,
    )
