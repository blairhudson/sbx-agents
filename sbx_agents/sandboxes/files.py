from pathlib import Path


class WorkspaceFileMixin:
    workspace: Path

    def put_file(self, path: str | Path, content: str, *, encoding: str = "utf-8") -> Path:
        target = self._workspace_file_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding=encoding)
        return target

    def get_file(self, path: str | Path, *, encoding: str = "utf-8") -> str:
        return self._workspace_file_path(path).read_text(encoding=encoding)

    def put_bytes(self, path: str | Path, content: bytes) -> Path:
        target = self._workspace_file_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def get_bytes(self, path: str | Path) -> bytes:
        return self._workspace_file_path(path).read_bytes()

    def list_files(self, pattern: str = "**/*") -> list[Path]:
        root = self.workspace.resolve()
        return sorted(
            path.relative_to(root)
            for path in root.glob(pattern)
            if path.is_file() and _is_within(root, path.resolve())
        )

    def delete_file(self, path: str | Path) -> None:
        self._workspace_file_path(path).unlink()

    def _workspace_file_path(self, path: str | Path) -> Path:
        root = self.workspace.resolve()
        target = (root / path).resolve()
        if not _is_within(root, target):
            raise ValueError(f"Sandbox file path escapes workspace: {path}")
        return target


def _is_within(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
    except ValueError:
        return False
    return True
