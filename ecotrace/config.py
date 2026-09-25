"""EcoTrace configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ecotrace.exceptions import ConfigurationError


@dataclass
class EcoTraceConfig:
    """Configuration for the EcoTrace SDK.

    Attributes:
        api_key: Optional API key for EcoTrace services.
        project: Optional project name for grouping tracked events.
        storage: Storage backend type ('memory' or 'sqlite').
        storage_path: Path for SQLite database file.
        enabled: Whether tracking is active.
        debug: Whether debug logging is enabled.
        metadata: Additional configuration metadata.
    """

    api_key: Optional[str] = None
    project: Optional[str] = None
    storage: str = "memory"
    storage_path: str = "ecotrace.db"
    enabled: bool = True
    debug: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.storage not in ("memory", "sqlite"):
            raise ConfigurationError(
                f"Unsupported storage backend: {self.storage!r}. "
                f"Supported: 'memory', 'sqlite'"
            )

    @classmethod
    def from_env(cls) -> EcoTraceConfig:
        """Create configuration from environment variables.

        Reads:
            ECOTRACE_API_KEY
            ECOTRACE_PROJECT
            ECOTRACE_STORAGE
            ECOTRACE_STORAGE_PATH
            ECOTRACE_ENABLED
            ECOTRACE_DEBUG
        """
        return cls(
            api_key=os.environ.get("ECOTRACE_API_KEY"),
            project=os.environ.get("ECOTRACE_PROJECT"),
            storage=os.environ.get("ECOTRACE_STORAGE", "memory"),
            storage_path=os.environ.get("ECOTRACE_STORAGE_PATH", "ecotrace.db"),
            enabled=os.environ.get("ECOTRACE_ENABLED", "true").lower() == "true",
            debug=os.environ.get("ECOTRACE_DEBUG", "false").lower() == "true",
        )

    def __repr__(self) -> str:
        """Safe repr that does not expose API key."""
        return (
            f"EcoTraceConfig("
            f"api_key={'***' if self.api_key else None}, "
            f"project={self.project!r}, "
            f"storage={self.storage!r}, "
            f"enabled={self.enabled})"
        )
