"""
FCCD level-set advection: ∂_t ψ + ∇·(ψu) = 0 via FCCDSolver primitives.

Mirror of :class:`DissipativeCCDAdvection` with the inner operator replaced
by FCCD's face-centered scheme. Two modes (SP-D §10):

    mode='node'  (Option C)
        R_4 Hermite reconstructor on ∂_k ψ at nodes; nodal multiplication
        by u^(k) and sum. Drop-in shape-compatible with DissipativeCCDAdvection.

    mode='flux'  (Option B)
        Conservative single-face-value flux divergence; clamp-stage mass
        error is closed by the ψ-space transport mass correction.

TVD-RK3 time integration; optional per-stage clamp to keep ψ ∈ [0, 1].
The spectral filter ε_d (DissipativeCCDAdvection default 0.05) is kept as
an optional post-stage smoother for stability with under-resolved
interfaces (SP-D §10); disable when FCCD's natural 4th-order dissipation
is sufficient.

GPU/CPU unified via ``backend.xp``. Mass-correction hook is retained for
standalone ψ advection; solver transport applies the Ch6 ψ-space correction.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from ..core.array_checks import all_arrays_exact_zero
from ..core.boundary import is_periodic_axis, sync_periodic_image_nodes
from .interfaces import ILevelSetAdvection
from ..time_integration.tvd_rk3 import tvd_rk3
from .heaviside import apply_mass_correction
from .transport_ledger import TransportLedger, TransportStageLedger

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.fccd import FCCDSolver
    from ..simulation.scheme_build_ctx import AdvectionBuildCtx


class FCCDLevelSetAdvection(ILevelSetAdvection):
    """Advects ψ using FCCDSolver primitives + TVD-RK3.

    Parameters
    ----------
    backend          : Backend
    grid             : Grid
    fccd             : FCCDSolver (shares CCD LU internally)
    mode             : {'node', 'flux'}
    mass_correction  : bool — Lagrange-multiplier mass renormalisation
                       (same as DissipativeCCDAdvection).

    Notes
    -----
    API matches :class:`DissipativeCCDAdvection.advance`:
        ``advance(psi, velocity_components, dt, clip_bounds=(0.0, 1.0))``.
    """

    scheme_names     = ("fccd_flux", "fccd_nodal")
    _scheme_aliases  = {"fccd": "fccd_flux"}
    _modes = {"fccd_flux": "flux", "fccd_nodal": "node"}

    @classmethod
    def _build(cls, name: str, ctx: "AdvectionBuildCtx") -> "FCCDLevelSetAdvection":
        return cls(ctx.backend, ctx.grid, ctx.fccd, mode=cls._modes[name], mass_correction=False)

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        fccd: "FCCDSolver",
        mode: str = "flux",
        mass_correction: bool = False,
    ) -> None:
        if mode not in ("node", "flux"):
            raise ValueError(f"mode must be 'node' or 'flux', got {mode!r}")
        self._backend = backend
        self.xp = backend.xp
        self._grid = grid
        self._fccd = fccd
        self._mode = mode
        self._mass_correction = mass_correction
        self._dV = grid.cell_volumes() if mass_correction else None

    def advance(
        self,
        psi,
        velocity_components: List,
        dt: float,
        clip_bounds=(0.0, 1.0),
    ):
        """Advance ψ by one RK3 step."""
        xp = self.xp
        psi = xp.asarray(psi)
        velocity_components = [xp.asarray(vc) for vc in velocity_components]
        sync_periodic_image_nodes(psi, self._fccd.bc_type)

        if self._mass_correction:
            M_old = xp.sum(psi * self._dV)

        if not self._backend.is_gpu() and all_arrays_exact_zero(xp, velocity_components):
            q_new = psi
            if clip_bounds is not None:
                lo, hi = clip_bounds
                q_new = xp.clip(psi, lo, hi)
                sync_periodic_image_nodes(q_new, self._fccd.bc_type)
            if self._mass_correction:
                q_new = apply_mass_correction(xp, q_new, self._dV, M_old)
                sync_periodic_image_nodes(q_new, self._fccd.bc_type)
            return q_new

        def post_stage(q):
            if clip_bounds is not None:
                lo, hi = clip_bounds
                q = xp.clip(q, lo, hi)
            return sync_periodic_image_nodes(q, self._fccd.bc_type)

        q_new = tvd_rk3(
            xp, psi, dt,
            lambda q: self._rhs(q, velocity_components, skip_zero_check=True),
            post_stage=post_stage,
        )

        if self._mass_correction:
            q_new = apply_mass_correction(xp, q_new, self._dV, M_old)
            sync_periodic_image_nodes(q_new, self._fccd.bc_type)

        return q_new

    def advance_with_face_velocity(
        self,
        psi,
        face_velocity_components: List,
        dt: float,
        clip_bounds=(0.0, 1.0),
        *,
        bound_preserving: bool = False,
        face_divergence_operator=None,
        return_ledger: bool = False,
    ):
        r"""Advance ψ by ``-D_f(P_f ψ\,u_f)`` using projected face velocities.

        This is the projection-native conservative transport contract for
        sharp-interface pressure-jump runs.  The supplied ``u_f`` is already the
        face-normal velocity accepted by the PPE/projection operator; it must
        not be reconstructed to nodes and then sampled again.
        """
        xp = self.xp
        psi = xp.asarray(psi)
        if len(face_velocity_components) != self._grid.ndim:
            raise ValueError(
                "face_velocity_components must provide one face-normal field "
                f"per grid axis; got {len(face_velocity_components)} for "
                f"{self._grid.ndim}D grid"
            )
        face_velocity_components = [
            xp.asarray(component) for component in face_velocity_components
        ]
        sync_periodic_image_nodes(psi, self._fccd.bc_type)
        psi_before = xp.array(psi, copy=True) if return_ledger else None
        volume_fluxes = (
            tuple(xp.array(component, copy=True) for component in face_velocity_components)
            if return_ledger
            else ()
        )
        zero_face_templates = tuple(
            xp.zeros_like(component) for component in face_velocity_components
        )

        def conservative_rhs(face_fluxes):
            if face_divergence_operator is not None:
                return -face_divergence_operator.divergence_from_faces(list(face_fluxes))
            total_rhs = xp.zeros_like(psi)
            for axis, flux_face in enumerate(face_fluxes):
                total_rhs = total_rhs - self._fccd.face_divergence(flux_face, axis)
            return total_rhs

        def axis_conservative_rhs(face_flux, axis: int):
            if face_divergence_operator is not None:
                faces = list(zero_face_templates)
                faces[axis] = face_flux
                return -face_divergence_operator.divergence_from_faces(faces)
            return -self._fccd.face_divergence(face_flux, axis)

        if self._mass_correction:
            M_old = xp.sum(psi * self._dV)

        if (
            not self._backend.is_gpu()
            and all_arrays_exact_zero(xp, face_velocity_components)
        ):
            q_new = psi
            if clip_bounds is not None:
                lo, hi = clip_bounds
                q_new = xp.clip(psi, lo, hi)
                sync_periodic_image_nodes(q_new, self._fccd.bc_type)
            if self._mass_correction:
                q_new = apply_mass_correction(xp, q_new, self._dV, M_old)
                sync_periodic_image_nodes(q_new, self._fccd.bc_type)
            if return_ledger:
                ledger = TransportLedger(
                    dt=float(dt),
                    face_volume_fluxes=volume_fluxes,
                    stages=(),
                    psi_before=psi_before,
                    psi_after_transport=xp.array(q_new, copy=True),
                    clip_bounds=clip_bounds,
                    mass_correction_applied=bool(self._mass_correction),
                    zero_velocity=True,
                )
                return q_new, ledger
            return q_new

        def rhs(q, *, record_stage: bool = False):
            phase_fluxes = []
            for axis, face_velocity in enumerate(face_velocity_components):
                psi_face = self._fccd.face_value(q, axis)
                flux_face = psi_face * face_velocity
                if record_stage:
                    phase_fluxes.append(xp.array(flux_face, copy=True))
            if record_stage:
                total = conservative_rhs(tuple(phase_fluxes))
                return total, tuple(phase_fluxes)
            return conservative_rhs(
                tuple(
                    self._fccd.face_value(q, axis) * face_velocity
                    for axis, face_velocity in enumerate(face_velocity_components)
                )
            )

        def donor_face_value(q, face_velocity, axis: int):
            q_axis = xp.moveaxis(xp.asarray(q), axis, 0)
            velocity_axis = xp.moveaxis(xp.asarray(face_velocity), axis, 0)
            if is_periodic_axis(self._fccd.bc_type, axis, self._grid.ndim):
                n_axis = self._grid.N[axis]
                q_lo = q_axis[:n_axis]
                q_hi = xp.roll(q_lo, -1, axis=0)
            else:
                q_lo = q_axis[:-1]
                q_hi = q_axis[1:]
            donor = xp.where(velocity_axis >= 0.0, q_lo, q_hi)
            return xp.moveaxis(donor, 0, axis)

        def low_order_fluxes(q):
            return tuple(
                donor_face_value(q, face_velocity, axis) * face_velocity
                for axis, face_velocity in enumerate(face_velocity_components)
            )

        def divergence(face_fluxes):
            return conservative_rhs(face_fluxes)

        def cell_capacity_ratios(q_low, correction_fluxes):
            pos = xp.zeros_like(q_low)
            neg = xp.zeros_like(q_low)
            for axis, flux in enumerate(correction_fluxes):
                delta = dt * axis_conservative_rhs(flux, axis)
                pos = pos + xp.maximum(delta, 0.0)
                neg = neg + xp.minimum(delta, 0.0)
            one = xp.asarray(1.0, dtype=q_low.dtype)
            zero = xp.asarray(0.0, dtype=q_low.dtype)
            pos_den = xp.where(pos > 0.0, pos, one)
            neg_den = xp.where(neg < 0.0, neg, -one)
            r_pos = xp.where(pos > 0.0, xp.minimum(one, (one - q_low) / pos_den), one)
            r_neg = xp.where(neg < 0.0, xp.minimum(one, (zero - q_low) / neg_den), one)
            return xp.clip(r_pos, 0.0, 1.0), xp.clip(r_neg, 0.0, 1.0)

        def face_capacity_ratio(r_pos, r_neg, correction_flux, axis: int):
            rpos_axis = xp.moveaxis(r_pos, axis, 0)
            rneg_axis = xp.moveaxis(r_neg, axis, 0)
            flux_axis = xp.moveaxis(correction_flux, axis, 0)
            if is_periodic_axis(self._fccd.bc_type, axis, self._grid.ndim):
                n_axis = self._grid.N[axis]
                left_pos = rpos_axis[:n_axis]
                left_neg = rneg_axis[:n_axis]
                right_pos = xp.roll(left_pos, -1, axis=0)
                right_neg = xp.roll(left_neg, -1, axis=0)
            else:
                left_pos = rpos_axis[:-1]
                left_neg = rneg_axis[:-1]
                right_pos = rpos_axis[1:]
                right_neg = rneg_axis[1:]
            alpha_axis = xp.where(
                flux_axis >= 0.0,
                xp.minimum(left_neg, right_pos),
                xp.minimum(left_pos, right_neg),
            )
            return xp.moveaxis(alpha_axis, 0, axis)

        def limited_rhs(q, *, record_stage: bool = False):
            high_rhs, high_fluxes = rhs(q, record_stage=True)
            low_fluxes = low_order_fluxes(q)
            low_rhs = divergence(low_fluxes)
            q_low = q + dt * low_rhs
            correction_fluxes = tuple(
                high_flux - low_flux
                for low_flux, high_flux in zip(low_fluxes, high_fluxes)
            )
            r_pos, r_neg = cell_capacity_ratios(q_low, correction_fluxes)
            limited_fluxes = tuple(
                low_flux
                + face_capacity_ratio(r_pos, r_neg, correction_flux, axis)
                * correction_flux
                for axis, (low_flux, correction_flux) in enumerate(
                    zip(low_fluxes, correction_fluxes, strict=True)
                )
            )
            total = divergence(limited_fluxes)
            if record_stage:
                return total, tuple(xp.array(flux, copy=True) for flux in limited_fluxes)
            return total

        def post_stage(q):
            if clip_bounds is not None:
                lo, hi = clip_bounds
                q = xp.clip(q, lo, hi)
            return sync_periodic_image_nodes(q, self._fccd.bc_type)

        if return_ledger:
            project_stage = clip_bounds is not None
            q0 = psi
            stage_rhs = limited_rhs if bound_preserving else rhs
            rhs0, fluxes0 = stage_rhs(q0, record_stage=True)
            q1 = post_stage(q0 + dt * rhs0)
            rhs1, fluxes1 = stage_rhs(q1, record_stage=True)
            q2 = post_stage(0.75 * q0 + 0.25 * (q1 + dt * rhs1))
            rhs2, fluxes2 = stage_rhs(q2, record_stage=True)
            q_new = post_stage(
                (1.0 / 3.0) * q0 + (2.0 / 3.0) * (q2 + dt * rhs2)
            )
            stages = (
                TransportStageLedger(
                    name="rk3_stage1",
                    phase_state=xp.array(q0, copy=True),
                    phase_fluxes=fluxes0,
                    base_weight=0.0,
                    candidate_weight=1.0,
                    post_stage_projected=project_stage,
                ),
                TransportStageLedger(
                    name="rk3_stage2",
                    phase_state=xp.array(q1, copy=True),
                    phase_fluxes=fluxes1,
                    base_weight=0.75,
                    candidate_weight=0.25,
                    post_stage_projected=project_stage,
                ),
                TransportStageLedger(
                    name="rk3_stage3",
                    phase_state=xp.array(q2, copy=True),
                    phase_fluxes=fluxes2,
                    base_weight=(1.0 / 3.0),
                    candidate_weight=(2.0 / 3.0),
                    post_stage_projected=project_stage,
                ),
            )
        else:
            q_new = tvd_rk3(
                xp,
                psi,
                dt,
                limited_rhs if bound_preserving else rhs,
                post_stage=post_stage,
            )

        if self._mass_correction:
            q_new = apply_mass_correction(xp, q_new, self._dV, M_old)
            sync_periodic_image_nodes(q_new, self._fccd.bc_type)

        if return_ledger:
            ledger = TransportLedger(
                dt=float(dt),
                face_volume_fluxes=volume_fluxes,
                stages=stages,
                psi_before=psi_before,
                psi_after_transport=xp.array(q_new, copy=True),
                clip_bounds=clip_bounds,
                mass_correction_applied=bool(self._mass_correction),
                zero_velocity=False,
            )
            return q_new, ledger
        return q_new

    # ── RHS: −∇·(ψu) via FCCD ───────────────────────────────────────────

    def _rhs(self, psi, vel, *, skip_zero_check: bool = False):
        """−∇·(ψu) in flux mode, or −u·∇ψ in nodal mode."""
        return self._fccd.advection_rhs(
            vel,
            scalar=psi,
            mode=self._mode,
            skip_zero_check=skip_zero_check,
        )[0]
