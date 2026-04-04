# IIM (Immersed Interface Method) sub-package for CCD-based PPE solvers.
#
# Modules:
#   jump_conditions  — Systematic derivation of [p^(k)] for k=0..5
#   stencil_corrector — IIM RHS correction for CCD Hermite system
#
# Reference: docs/memo/IIM_CCD_PPE_ShortPaper.md

from .jump_conditions import JumpConditionCalculator
from .stencil_corrector import IIMStencilCorrector

__all__ = ["JumpConditionCalculator", "IIMStencilCorrector"]
