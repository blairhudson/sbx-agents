class SbxAgentsError(Exception):
    """Base error for sbx-agents."""


class SandboxError(SbxAgentsError):
    """Raised when sandbox lifecycle or command execution fails."""


class UnsupportedFeatureError(SbxAgentsError):
    """Raised when strict mode sees unsupported backend feature."""
