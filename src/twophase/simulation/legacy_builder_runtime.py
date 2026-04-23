"""Assembly helpers for the legacy `SimulationBuilder` pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..backend import Backend
from ..ccd.ccd_solver import CCDSolver
from ..config import SimulationConfig
from ..core.boundary import BoundarySpec
from ..core.components import SimulationComponents
from ..core.grid import Grid
from ..coupling.gfm import GFMCorrector
from ..coupling.ppe_rhs_gfm import PPERHSBuilderGFM
from ..coupling.velocity_corrector import VelocityCorrector
from ..levelset.advection import DissipativeCCDAdvection, LevelSetAdvection
from ..levelset.closest_point_extender import ClosestPointExtender
from ..levelset.curvature_psi import CurvatureCalculatorPsi
from ..levelset.field_extender import FieldExtender, NullFieldExtender
from ..levelset.reinitialize import Reinitializer
from ..ppe.factory import create_ppe_solver
from ..spatial.dccd_ppe_filter import DCCDPPEFilter
from ..spatial.rhie_chow import RhieChowInterpolator
from ..time_integration.ab2_predictor import Predictor
from ..time_integration.cfl import CFLCalculator
from .boundary_condition import BoundaryConditionHandler
from .diagnostics import DiagnosticsReporter

if TYPE_CHECKING:
    from ..ns_terms.interfaces import INSTerm
    from ..ppe.interfaces import IPPESolver


def build_legacy_simulation_components(
    *,
    config: SimulationConfig,
    ppe_solver: "IPPESolver | None",
    convection_term: "INSTerm | None",
    viscous_term: "INSTerm | None",
    gravity_term: "INSTerm | None",
    surface_tension_term: "INSTerm | None",
) -> SimulationComponents:
    backend = Backend(use_gpu=config.use_gpu)
    grid = Grid(config.grid, backend)
    bc_spec = BoundarySpec(
        bc_type=config.numerics.bc_type,
        shape=grid.shape,
        N=grid.N,
    )
    dx_min = min(
        config.grid.L[axis] / config.grid.N[axis]
        for axis in range(config.grid.ndim)
    )
    eps = config.numerics.epsilon_factor * dx_min
    ccd = CCDSolver(grid, backend, bc_type=config.numerics.bc_type)

    ls_bc = "periodic" if config.numerics.bc_type == "periodic" else "neumann"

    fccd = None
    if (
        config.numerics.advection_scheme.startswith("fccd_")
        or config.numerics.convection_scheme.startswith("fccd_")
    ):
        from ..ccd.fccd import FCCDSolver

        fccd = FCCDSolver(
            grid,
            backend,
            bc_type=config.numerics.bc_type,
            ccd_solver=ccd,
        )

    adv_mode = {"fccd_nodal": "node", "fccd_flux": "flux"}
    if config.numerics.advection_scheme == "dissipative_ccd":
        ls_advect = DissipativeCCDAdvection(
            backend,
            grid,
            ccd,
            bc=ls_bc,
            mass_correction=True,
        )
    elif config.numerics.advection_scheme in adv_mode:
        from ..levelset.fccd_advection import FCCDLevelSetAdvection

        ls_advect = FCCDLevelSetAdvection(
            backend,
            grid,
            fccd,
            mode=adv_mode[config.numerics.advection_scheme],
            mass_correction=True,
        )
    else:
        ls_advect = LevelSetAdvection(backend, grid, bc=ls_bc)

    effective_convection = convection_term
    if effective_convection is None and config.numerics.convection_scheme in adv_mode:
        from ..ns_terms.fccd_convection import FCCDConvectionTerm

        effective_convection = FCCDConvectionTerm(
            backend,
            fccd,
            mode=adv_mode[config.numerics.convection_scheme],
        )
    if effective_convection is None and config.numerics.convection_scheme == "uccd6":
        from ..ns_terms.uccd6_convection import UCCD6ConvectionTerm

        effective_convection = UCCD6ConvectionTerm(
            backend,
            grid,
            ccd,
            sigma=config.numerics.uccd6_sigma,
        )

    ls_reinit = Reinitializer(
        backend,
        grid,
        ccd,
        eps,
        config.numerics.reinit_steps,
        bc=ls_bc,
        method=config.numerics.reinit_method,
        sigma_0=config.numerics.ridge_sigma_0,
    )
    curvature_calc = CurvatureCalculatorPsi(backend, ccd)
    use_gfm = config.numerics.surface_tension_model == "gfm"

    predictor = Predictor(
        backend,
        config,
        ccd,
        convection=effective_convection,
        viscous=viscous_term,
        gravity=gravity_term,
        surface_tension=surface_tension_term,
        use_gfm=use_gfm,
    )
    effective_ppe_solver = ppe_solver or create_ppe_solver(
        config,
        backend,
        grid,
        ccd=ccd,
        bc_spec=bc_spec,
    )

    rhie_chow = RhieChowInterpolator(backend, grid, ccd, bc_type=config.numerics.bc_type)
    vel_corrector = VelocityCorrector(backend, grid, ccd)

    ppe_rhs_gfm = None
    if use_gfm:
        gfm_corrector = GFMCorrector(backend, grid, config.fluid.We)
        dccd_ppe_filter = DCCDPPEFilter(backend, grid, ccd, bc_type=config.numerics.bc_type)
        ppe_rhs_gfm = PPERHSBuilderGFM(dccd_ppe_filter, gfm_corrector)

    method = config.numerics.extension_method
    if method == "hermite":
        field_extender = ClosestPointExtender(backend, grid, ccd)
    elif method == "upwind" and config.numerics.n_extend > 0:
        field_extender = FieldExtender(
            backend,
            grid,
            ccd,
            n_iter=config.numerics.n_extend,
        )
    else:
        field_extender = NullFieldExtender()

    cfl_calc = CFLCalculator(
        backend,
        grid,
        config.numerics.cfl_number,
        We=config.fluid.We,
        rho_ratio=config.fluid.rho_ratio,
        cn_viscous=config.numerics.cn_viscous,
    )
    bc_handler = BoundaryConditionHandler(config)
    diagnostics = DiagnosticsReporter(backend, grid)

    return SimulationComponents(
        config=config,
        backend=backend,
        grid=grid,
        eps=eps,
        ccd=ccd,
        ls_advect=ls_advect,
        ls_reinit=ls_reinit,
        curvature_calc=curvature_calc,
        predictor=predictor,
        ppe_solver=effective_ppe_solver,
        rhie_chow=rhie_chow,
        vel_corrector=vel_corrector,
        cfl_calc=cfl_calc,
        bc_handler=bc_handler,
        diagnostics=diagnostics,
        ppe_rhs_gfm=ppe_rhs_gfm,
        field_extender=field_extender,
    )
