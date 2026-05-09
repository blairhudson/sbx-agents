from typing import Literal

from pydantic import BaseModel, Field

PermissionAction = Literal["allow", "ask", "deny"]
PermissionRule = PermissionAction | dict[str, PermissionAction]


class PermissionPolicy(BaseModel):
    default: PermissionAction | None = None
    tools: dict[str, PermissionRule] = Field(default_factory=dict)

    def to_opencode(self) -> PermissionAction | dict[str, PermissionRule]:
        if self.default is not None and not self.tools:
            return self.default
        rendered: dict[str, PermissionRule] = dict(self.tools)
        if self.default is not None:
            rendered.setdefault("*", self.default)
        return rendered
