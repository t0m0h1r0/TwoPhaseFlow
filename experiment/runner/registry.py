"""Central registry for experiment handlers (ch13 NS-simulation)."""

from __future__ import annotations

from typing import Any


class ExperimentHandler:
    """Base for all experiment handlers.  Subclasses implement run() and plot()."""

    @classmethod
    def load_config(cls, path: Any) -> Any:
        """Load YAML at ``path`` into the handler's expected config type.

        Subclasses must override (e.g. ns_simulation handlers use
        ``twophase.simulation.config_io.load_experiment_config``).
        """
        raise NotImplementedError("subclass must implement load_config")

    def run(self, cfg: Any, outdir: Any) -> dict:
        raise NotImplementedError

    def plot(self, cfg: Any, outdir: Any, results: dict | None = None) -> None:
        """When results is None, load from outdir/data.npz."""
        raise NotImplementedError


HANDLER_REGISTRY: dict[str, ExperimentHandler] = {}


def register_handler(type_name: str):
    """Class decorator: @register_handler("capillary_wave")"""
    def decorator(cls):
        HANDLER_REGISTRY[type_name] = cls()
        return cls
    return decorator
