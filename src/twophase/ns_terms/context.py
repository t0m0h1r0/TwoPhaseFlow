from dataclasses import dataclass
from typing import Optional, List, Any


@dataclass
class NSComputeContext:
    """Context bag for all arguments needed by NS term compute() methods.

    This allows uniform compute(ctx) signatures across all INSTerm implementations
    without requiring each to declare unused parameters.

    Fields are np.ndarray on CPU, cupy.ndarray on GPU — use backend.xp for all ops.
    """
    velocity: List[Any]  # [u, v] or [u, v, w]
    ccd: 'CCDSolver'  # Always present
    rho: Any   # Density field (node-centered)
    mu: Any    # Dynamic viscosity field (scalar or array)
    kappa: Optional[Any] = None  # Interface curvature
    psi: Optional[Any] = None    # Level-set (Heaviside)
    fccd: Optional['FCCDSolver'] = None  # For FCCD-based terms only
