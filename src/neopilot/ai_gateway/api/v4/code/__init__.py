from fastapi import APIRouter

from neopilot.ai_gateway.api.v4.code import suggestions

__all__ = [
    "router",
]


router = APIRouter()

router.include_router(suggestions.router)
