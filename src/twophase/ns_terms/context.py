from dataclasses import dataclass
from typing import Optional, List

import numpy as np


@dataclass
class NSComputeContext:
    """Context bag for all arguments needed by NS term compute() methods.

    This allows uniform compute(ctx) signatures across all INSTerm implementations
    without requiring each to declare unused parameters.
    """
    velocity: List[np.ndarray]  # [u, v] or [u, v, w]
    ccd: 'CCDSolver'  # Always present
    rho: np.ndarray   # Density field (node-centered)
    mu: np.ndarray    # Dynamic viscosity field (scalar or array)
    kappa: Optional[np.ndarray] = None  # Interface curvature
    psi: Optional[np.ndarray] = None    # Level-set (Heaviside)
    fccd: Optional['FCCDSolver'] = None  # For FCCD-based terms only
