from fastapi import APIRouter

from neopilot.ai_gateway.api.v2.chat import agent

__all__ = [
    "router",
]


router = APIRouter()

# Please, include your sub-routes here to have a single `api_router` exposed.
#
# Example:
# ```python
# router.include_router(agent.router)
# router.include_router(tool_calculator.router)
# ```

router.include_router(agent.router)
