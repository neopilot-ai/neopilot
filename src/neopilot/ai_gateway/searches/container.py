from dependency_injector import containers, providers
from google.cloud import discoveryengine

from .search import VertexAISearch
from .sqlite_search import SqliteSearch

__all__ = ["ContainerSearches"]


def _init_vertex_search_service_client(
    mock_model_responses: bool,
    custom_models_enabled: bool,
) -> discoveryengine.SearchServiceAsyncClient | None:
    if mock_model_responses or custom_models_enabled:
        return None

    return discoveryengine.SearchServiceAsyncClient()


class ContainerSearches(containers.DeclarativeContainer):
    config = providers.Configuration(strict=True)
    _mock_selector = providers.Callable(
        lambda mock_model_responses: "mocked" if mock_model_responses else "original",
        config.mock_model_responses,
    )

    _local_or_vertex = providers.Callable(
        lambda custom_models_enabled: "local" if custom_models_enabled else "vertex",
        config.custom_models.enabled,
    )

    grpc_client_vertex = providers.Singleton(
        _init_vertex_search_service_client,
        mock_model_responses=config.mock_model_responses,
        custom_models_enabled=config.custom_models.enabled,
    )

    search_provider = providers.Selector(
        _local_or_vertex,
        local=providers.Factory(SqliteSearch),
        vertex=providers.Factory(
            VertexAISearch,
            client=grpc_client_vertex,
            project=config.vertex_search.project,
            fallback_datastore_version=config.vertex_search.fallback_datastore_version,
        ),
    )
