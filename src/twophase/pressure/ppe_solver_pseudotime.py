# Backward-compat re-export (A7): moved to pressure/legacy/ppe_solver_pseudotime.py
from .legacy.ppe_solver_pseudotime import PPESolverPseudoTime  # noqa: F401

# Re-export _CCDPPEBase for backward compat (used by ppe_solver_ccd_lu.py etc.)
from .ccd_ppe_base import _CCDPPEBase  # noqa: F401
