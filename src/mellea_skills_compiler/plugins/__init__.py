"""Runtime governance hooks for Mellea pipelines."""

from abc import ABC, abstractmethod
from pathlib import Path

from mellea import plugins as mellea_plugins

from mellea_skills_compiler.toolkit.logging import configure_logger


LOGGER = configure_logger()


class BasePlugin(ABC):
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    @abstractmethod
    def summary() -> dict:
        raise NotImplementedError

    def register(self):
        mellea_plugins.register(self)

    def deregister(self) -> None:
        """Remove all plugins from the global registry."""
        try:
            mellea_plugins.unregister(self)
        except (ImportError, Exception):
            pass
