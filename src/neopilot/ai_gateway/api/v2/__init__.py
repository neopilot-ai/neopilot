from fastapi import APIRouter

from neopilot.ai_gateway.api.v2 import chat, code, prompts

__all__ = ["api_router"]

api_router = APIRouter()

# We don't include the `code` prefix here, as we need to support the legacy `/completions` endpoint.
api_router.include_router(code.router, tags=["completions"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
