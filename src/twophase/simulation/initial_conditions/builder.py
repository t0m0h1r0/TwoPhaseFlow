"""
InitialConditionBuilder — compose shape primitives into a CLS ψ field.

Algorithm
---------
1. Separate shapes by interior_phase into 'liquid' and 'gas' sets.
2. For each set, compute the union SDF via element-wise min over all SDFs.
3. Combine liquid/gas SDFs:
       φ_final = max(φ_liquid, −φ_gas)
   This keeps the region that is liquid AND not inside a gas shape.
4. Convert to CLS smooth Heaviside:
       ψ = 1 / (1 + exp(φ_final / ε))

Background phase
----------------
'gas'    → φ_liquid starts at +∞ (no liquid, all gas unless shapes say otherwise)
'liquid' → φ_liquid starts at −∞ (all liquid unless shapes carve out gas regions)

Usage
-----
Python API::

    from twophase.simulation.initial_conditions import InitialConditionBuilder, Circle

    builder = InitialConditionBuilder(background_phase='gas')
    builder.add(Circle(center=(0.5, 0.5), radius=0.25, interior_phase='liquid'))
    psi = builder.build(grid, eps)
    sim.psi.data = sim.backend.to_device(psi)

YAML API::

    from twophase.simulation.initial_conditions import InitialConditionBuilder

    builder = InitialConditionBuilder.from_dict({
        'background_phase': 'gas',
        'shapes': [
            {'type': 'circle', 'center': [0.5, 0.5], 'radius': 0.25,
             'interior_phase': 'liquid'},
        ]
    })
    psi = builder.build(grid, eps)
"""

from __future__ import annotations

from typing import List, TYPE_CHECKING

import numpy as np

from .shapes import ShapePrimitive, shape_from_dict

if TYPE_CHECKING:
    from ..core.grid import Grid


class InitialConditionBuilder:
    """Builds the initial CLS ψ field from a list of shape primitives.

    Parameters
    ----------
    background_phase : str
        Phase that fills the domain before any shapes are applied.
        'gas' (default) — domain starts as all gas (ψ = 0).
        'liquid'        — domain starts as all liquid (ψ = 1).

    Attributes
    ----------
    shapes : list of ShapePrimitive
        Registered shape primitives (in order of addition).
    """

    def __init__(self, background_phase: str = "gas") -> None:
        if background_phase not in ("liquid", "gas"):
            raise ValueError(
                f"background_phase must be 'liquid' or 'gas', "
                f"got '{background_phase}'."
            )
        self.background_phase = background_phase
        self.shapes: List[ShapePrimitive] = []

    # ── 登録 API ──────────────────────────────────────────────────────────────

    def add(self, shape: ShapePrimitive) -> "InitialConditionBuilder":
        """Register a shape primitive.

        Parameters
        ----------
        shape : ShapePrimitive
            Any Circle, Rectangle, or HalfSpace instance.

        Returns
        -------
        self : allows chaining.
        """
        self.shapes.append(shape)
        return self

    # ── ビルド ────────────────────────────────────────────────────────────────

    def build(self, grid: "Grid", eps: float) -> np.ndarray:
        """Compute the initial CLS ψ field on the given grid.

        Parameters
        ----------
        grid : Grid
            Grid instance (provides ``meshgrid()`` and ``ndim``).
        eps  : float
            Interface half-width ε (same units as grid coordinates).
            Typically ``epsilon_factor × dx_min``.

        Returns
        -------
        psi : np.ndarray
            CLS field ψ ∈ [0, 1], shape ``grid.shape``.
            ψ ≈ 1 in liquid, ψ ≈ 0 in gas.
        """
        coords = grid.meshgrid()  # tuple of ndarrays
        shape_tuple = grid.shape

        # 背景フェーズに基づく初期 SDF:
        #   background=gas    → φ_liquid = +∞ (液体領域なし)
        #   background=liquid → φ_liquid = -∞ (全域が液体)
        if self.background_phase == "gas":
            phi_liquid = np.full(shape_tuple, +np.inf)
        else:  # "liquid"
            phi_liquid = np.full(shape_tuple, -np.inf)

        # 気泡（気相領域）の SDF: 初期は +∞（気泡なし）
        phi_gas = np.full(shape_tuple, +np.inf)

        # 各シェイプの SDF を計算し、フェーズ別にユニオン合成（element-wise min）
        for shape in self.shapes:
            phi_s = shape.sdf(*coords)
            if shape.interior_phase == "liquid":
                # 液体ユニオン: 少なくとも 1 つの液体形状の内側 → 液体
                phi_liquid = np.minimum(phi_liquid, phi_s)
            else:  # "gas"
                # 気泡ユニオン: 少なくとも 1 つの気泡の内側 → 気体
                phi_gas = np.minimum(phi_gas, phi_s)

        # 最終 SDF: 「液体領域 かつ 気泡外」の領域を液体とする
        #   φ_final = max(φ_liquid, −φ_gas)
        #   φ_final < 0 ⟺ φ_liquid < 0（液体内） かつ −φ_gas < 0（気泡外）
        phi_final = np.maximum(phi_liquid, -phi_gas)

        # CLS スムーズ Heaviside: ψ = 1/(1 + exp(φ/ε))
        # ψ → 1 inside (φ < 0), ψ → 0 outside (φ > 0)
        psi = 1.0 / (1.0 + np.exp(np.clip(phi_final / eps, -500.0, 500.0)))
        return psi.astype(np.float64)

    # ── YAML / dict からの構築 ─────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, d: dict) -> "InitialConditionBuilder":
        """Construct an InitialConditionBuilder from a plain dict (YAML fragment).

        Parameters
        ----------
        d : dict
            Expected structure::

                {
                    'background_phase': 'gas',   # optional, default 'gas'
                    'shapes': [
                        {'type': 'circle', 'center': [0.5, 0.5],
                         'radius': 0.25, 'interior_phase': 'liquid'},
                        ...
                    ]
                }

        Returns
        -------
        builder : InitialConditionBuilder
        """
        bg = d.get("background_phase", "gas")
        builder = cls(background_phase=bg)
        for shape_dict in d.get("shapes", []):
            builder.add(shape_from_dict(shape_dict))
        return builder
