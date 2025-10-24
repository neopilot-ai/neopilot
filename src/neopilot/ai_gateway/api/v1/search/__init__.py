from fastapi import APIRouter

from neopilot.ai_gateway.api.v1.search import docs

__all__ = [
    "router",
]

router = APIRouter()
router.include_router(docs.router)
