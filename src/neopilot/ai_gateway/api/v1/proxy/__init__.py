from fastapi import APIRouter

from neopilot.ai_gateway.api.v1.proxy import anthropic, openai, vertex_ai

__all__ = [
    "router",
]


router = APIRouter()
router.include_router(openai.router)
router.include_router(anthropic.router)
router.include_router(vertex_ai.router)
