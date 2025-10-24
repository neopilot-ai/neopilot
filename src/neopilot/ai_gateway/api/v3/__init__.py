from fastapi import APIRouter

from neopilot.ai_gateway.api.v3 import code

__all__ = ["api_router"]

api_router = APIRouter()

api_router.include_router(code.router, prefix="/code", tags=["completions"])
