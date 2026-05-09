from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MaterialiseContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workspace: Path
    sandbox: Any
    metadata: dict[str, Any] = Field(default_factory=dict)
