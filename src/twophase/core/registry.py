"""Shared scheme-registration helper for pluggable solver components."""

from __future__ import annotations

from typing import Any, ClassVar


class SchemeRegistryMixin:
    """Mixin for self-registering scheme interfaces.

    Concrete subclasses declare ``scheme_names`` and optionally
    ``_scheme_aliases``.  The interface class owns ``_registry`` and
    ``_aliases`` so callers depend on the abstract interface rather than
    importing concrete implementations directly.
    """

    _registry: ClassVar[dict[str, type[Any]]]
    _aliases: ClassVar[dict[str, str]]
    _scheme_kind: ClassVar[str] = "scheme"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        registry = getattr(cls, "_registry", None)
        aliases = getattr(cls, "_aliases", None)
        if registry is None or aliases is None:
            return
        for scheme_name in getattr(cls, "scheme_names", ()):
            registry[scheme_name] = cls
        for alias, canonical_name in getattr(cls, "_scheme_aliases", {}).items():
            aliases[alias] = canonical_name

    @classmethod
    def from_scheme(cls, name: str, ctx: object):
        """Instantiate the implementation registered under ``name``."""
        canonical_name = cls._aliases.get(name, name)
        registered_class = cls._registry.get(canonical_name)
        if registered_class is None:
            raise ValueError(
                f"Unknown {cls._scheme_kind} {name!r}. "
                f"Known: {sorted(cls._registry)}"
            )
        return registered_class._build(canonical_name, ctx)
