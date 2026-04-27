"""Central registries for experiment handlers, schemes, and reference solutions."""

from __future__ import annotations

from typing import Any, Callable


# ── Base class ────────────────────────────────────────────────────────────────

class ExperimentHandler:
    """Base for all experiment handlers.  Subclasses implement run() and plot()."""

    @classmethod
    def load_config(cls, path: Any) -> Any:
        """Load YAML at ``path`` into the handler's expected config type.

        Default: ch11/ch12 ``ComponentConfig`` via ``load_component_config``.
        Override for ch13-style ``ExperimentConfig`` schemas.
        """
        from .config_loader import load_component_config
        return load_component_config(path)

    def run(self, cfg: Any, outdir: Any) -> dict:
        raise NotImplementedError

    def plot(self, cfg: Any, outdir: Any, results: dict | None = None) -> None:
        """When results is None, load from outdir/data.npz."""
        raise NotImplementedError


# ── Handler registry ──────────────────────────────────────────────────────────

HANDLER_REGISTRY: dict[str, ExperimentHandler] = {}


def register_handler(type_name: str):
    """Class decorator: @register_handler("convergence_study")"""
    def decorator(cls):
        HANDLER_REGISTRY[type_name] = cls()
        return cls
    return decorator


# ── Scheme registry ───────────────────────────────────────────────────────────

SCHEME_REGISTRY: dict[str, Callable[..., Any]] = {}


def register_scheme(name: str):
    """Function decorator: @register_scheme("ccd")"""
    def decorator(fn):
        SCHEME_REGISTRY[name] = fn
        return fn
    return decorator


# ── Reference solution registry ───────────────────────────────────────────────

SOLUTION_REGISTRY: dict[str, Callable] = {}


def register_solution(name: str):
    """Function decorator: @register_solution("sin_2pi")"""
    def decorator(fn):
        SOLUTION_REGISTRY[name] = fn
        return fn
    return decorator
