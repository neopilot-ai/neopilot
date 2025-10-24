from abc import ABC, abstractmethod
from typing import Optional

from gitlab_cloud_connector import GitLabUnitPrimitive
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict

from neopilot.ai_gateway.api.auth_utils import StarletteUser
from neopilot.ai_gateway.chat.tools import BaseTool

__all__ = [
    "UnitPrimitiveToolset",
    "BaseToolsRegistry",
]


class UnitPrimitiveToolset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: GitLabUnitPrimitive
    tools: list[BaseTool]

    # Minimum required GitLab version to use the tools.
    # If it's not set, the tools are available for all GitLab versions.
    min_required_gl_version: Optional[str] = None

    def is_available_for(self, unit_primitives: list[GitLabUnitPrimitive], gl_version: str):
        if self.name not in unit_primitives:
            return False

        if not self.min_required_gl_version:
            return True

        if not gl_version:
            return False

        try:
            return Version(self.min_required_gl_version) <= Version(gl_version)
        except InvalidVersion:
            return False


class BaseToolsRegistry(ABC):
    @abstractmethod
    def get_on_behalf(self, user: StarletteUser, gl_version: str) -> list[BaseTool]:
        pass

    @abstractmethod
    def get_all(self) -> list[BaseTool]:
        pass
