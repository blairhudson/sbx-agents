import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Skill(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str = ""
    instructions: str
    license: str | None = None
    compatibility: str | None = None
    path: Path | None = None
    assets: list[Path] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_dir(cls, path: str | Path) -> "Skill":
        skill_dir = Path(path)
        skill_file = skill_dir / "SKILL.md"
        raw = skill_file.read_text(encoding="utf-8")
        frontmatter, instructions = _split_frontmatter(raw)
        return cls(
            name=str(frontmatter.get("name") or skill_dir.name),
            description=str(frontmatter.get("description") or _first_heading_or_line(instructions)),
            instructions=instructions,
            license=_optional_str(frontmatter.get("license")),
            compatibility=_optional_str(frontmatter.get("compatibility")),
            path=skill_dir,
            assets=[item for item in skill_dir.iterdir() if item.name != "SKILL.md"],
            metadata=_metadata(frontmatter.get("metadata")),
        )

    def validate_opencode_name(self) -> None:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", self.name):
            msg = f"OpenCode skill name must match ^[a-z0-9]+(-[a-z0-9]+)*$: {self.name}"
            raise ValueError(msg)

    def to_skill_md(self, *, frontmatter: bool = False) -> str:
        if not frontmatter:
            return self.instructions
        lines = ["---", f"name: {self.name}", f"description: {self.description}"]
        if self.license is not None:
            lines.append(f"license: {self.license}")
        if self.compatibility is not None:
            lines.append(f"compatibility: {self.compatibility}")
        if self.metadata:
            lines.append("metadata:")
            for key, value in self.metadata.items():
                lines.append(f"  {key}: {value}")
        lines.extend(["---", self.instructions.lstrip()])
        return "\n".join(lines)


def _first_heading_or_line(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped:
            return stripped
    return ""


def _split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, content
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return {}, content
    return _parse_frontmatter(lines[1:end]), "\n".join(lines[end + 1 :]).lstrip("\n")


def _parse_frontmatter(lines: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    current_map: str | None = None
    for line in lines:
        if not line.strip():
            continue
        if line.startswith("  ") and current_map is not None:
            key, _, value = line.strip().partition(":")
            if key and value:
                metadata = parsed.setdefault(current_map, {})
                if isinstance(metadata, dict):
                    metadata[key.strip()] = value.strip()
            continue
        key, _, value = line.partition(":")
        if not key:
            continue
        if value.strip():
            parsed[key.strip()] = value.strip()
            current_map = None
        else:
            parsed[key.strip()] = {}
            current_map = key.strip()
    return parsed


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _metadata(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
