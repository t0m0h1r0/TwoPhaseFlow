# DO NOT DELETE — C2 backward-compatible re-export stub.
# Factory has been moved to pressure/solvers/factory.py.
from .solvers.factory import (  # noqa: F401
    create_ppe_solver,
    register_ppe_solver,
)

__all__ = ["create_ppe_solver", "register_ppe_solver"]
