import json
import re
import typing
from abc import ABC, abstractmethod

import fastapi
import httpx
from fastapi import status
from starlette.background import BackgroundTask

from neopilot.ai_gateway.config import ConfigModelLimits
from neopilot.ai_gateway.instrumentators.model_requests import ModelRequestInstrumentator


class BaseProxyClient(ABC):
    def __init__(self, client: httpx.AsyncClient, limits: ConfigModelLimits):
        self.client = client
        self.limits = limits

    async def proxy(self, request: fastapi.Request) -> fastapi.Response:
        upstream_path = self._extract_upstream_path(request.url.__str__())
        json_body = await self._extract_json_body(request)
        model_name = self._extract_model_name(upstream_path, json_body)

        if model_name not in self._allowed_upstream_models():
            raise fastapi.HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported model")

        stream = self._extract_stream_flag(upstream_path, json_body)
        headers_to_upstream = self._create_headers_to_upstream(request.headers)
        self._update_headers_to_upstream(headers_to_upstream)

        request_to_upstream = self.client.build_request(
            request.method,
            httpx.URL(upstream_path),
            headers=headers_to_upstream,
            json=json_body,
        )

        try:
            with ModelRequestInstrumentator(
                model_engine=self._upstream_service(),
                model_name=model_name,
                limits=self.limits.for_model(engine=self._upstream_service(), name=model_name),
            ).watch(stream=stream) as watcher:
                response_from_upstream = await self.client.send(request_to_upstream, stream=stream)
        except Exception:
            raise fastapi.HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bad Gateway")

        headers_to_downstream = self._create_headers_to_downstream(response_from_upstream.headers)

        if stream:
            return fastapi.responses.StreamingResponse(
                response_from_upstream.aiter_text(),
                status_code=response_from_upstream.status_code,
                headers=headers_to_downstream,
                background=BackgroundTask(func=watcher.afinish),
            )

        return fastapi.Response(
            content=response_from_upstream.content,
            status_code=response_from_upstream.status_code,
            headers=headers_to_downstream,
        )

    @abstractmethod
    def _allowed_upstream_paths(self) -> list[str]:
        """Allowed paths to the upstream service."""
        pass

    @abstractmethod
    def _allowed_headers_to_upstream(self) -> list[str]:
        """Allowed request headers to the upstream service."""
        pass

    @abstractmethod
    def _allowed_headers_to_downstream(self) -> list[str]:
        """Allowed response headers to the downstream service."""
        pass

    @abstractmethod
    def _upstream_service(self) -> str:
        """Name of the upstream service."""
        pass

    @abstractmethod
    def _allowed_upstream_models(self) -> list[str]:
        """Allowed models to the upstream service."""
        pass

    @abstractmethod
    def _extract_model_name(self, upstream_path: str, json_body: typing.Any) -> str:
        """Extract model name from the request."""
        pass

    @abstractmethod
    def _extract_stream_flag(self, upstream_path: str, json_body: typing.Any) -> bool:
        """Extract stream flag from the request."""
        pass

    @abstractmethod
    def _update_headers_to_upstream(self, headers: dict[str, str]) -> None:
        """Update headers for vendor specific requirements."""
        pass

    def _extract_upstream_path(self, request_path: str) -> str:
        path = re.sub(f"^(.*?)/{self._upstream_service()}/", "/", request_path)

        if path not in self._allowed_upstream_paths():
            raise fastapi.HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

        return path

    async def _extract_json_body(self, request: fastapi.Request) -> typing.Any:
        body = await request.body()

        try:
            json_body = json.loads(body)
        except json.JSONDecodeError:
            raise fastapi.HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

        return json_body

    def _create_headers_to_upstream(self, headers_from_downstream) -> dict[str, str]:
        return {
            key: headers_from_downstream[key]
            for key in self._allowed_headers_to_upstream()
            if key in headers_from_downstream
        }

    def _create_headers_to_downstream(self, headers_from_upstream) -> dict[str, str]:
        return {
            key: headers_from_upstream.get(key)
            for key in self._allowed_headers_to_downstream()
            if key in headers_from_upstream
        }
