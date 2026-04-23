"""Concrete registration imports for the modern NS pipeline.

This module centralizes side-effect imports that populate registries used by
`TwoPhaseNSSolver` construction, keeping the solver facade lighter.
"""

from ..levelset.advection import DissipativeCCDAdvection, LevelSetAdvection
from ..levelset.fccd_advection import FCCDLevelSetAdvection
from ..ns_terms.convection import ConvectionTerm
from ..ns_terms.fccd_convection import FCCDConvectionTerm
from ..ns_terms.uccd6_convection import UCCD6ConvectionTerm
from ..ppe.fccd_matrixfree import PPESolverFCCDMatrixFree
from ..ppe.fvm_matrixfree import PPESolverFVMMatrixFree
from ..ppe.fvm_spsolve import PPESolverFVMSpsolve
from .gradient_operator import (
    CCDGradientOperator,
    CCDDivergenceOperator,
    FCCDGradientOperator,
    FCCDDivergenceOperator,
    FVMGradientOperator,
    FVMDivergenceOperator,
)
from .surface_tension_strategy import (
    NullSurfaceTensionForce,
    PressureJumpSurfaceTension,
    SurfaceTensionForce,
)
from .velocity_reprojector import (
    ConsistentGFMReprojector,
    ConsistentIIMReprojector,
    LegacyReprojector,
    VariableDensityReprojector,
)
from .viscous_predictor import CNViscousPredictor, ExplicitViscousPredictor

__all__ = [
    "LevelSetAdvection",
    "DissipativeCCDAdvection",
    "FCCDLevelSetAdvection",
    "ConvectionTerm",
    "FCCDConvectionTerm",
    "UCCD6ConvectionTerm",
    "PPESolverFCCDMatrixFree",
    "PPESolverFVMMatrixFree",
    "PPESolverFVMSpsolve",
    "CCDGradientOperator",
    "CCDDivergenceOperator",
    "FCCDGradientOperator",
    "FCCDDivergenceOperator",
    "FVMGradientOperator",
    "FVMDivergenceOperator",
    "SurfaceTensionForce",
    "NullSurfaceTensionForce",
    "PressureJumpSurfaceTension",
    "LegacyReprojector",
    "VariableDensityReprojector",
    "ConsistentGFMReprojector",
    "ConsistentIIMReprojector",
    "ExplicitViscousPredictor",
    "CNViscousPredictor",
]
