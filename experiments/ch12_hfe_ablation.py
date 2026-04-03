#!/usr/bin/env python3
"""
EXP-12C: HFE ablation study — §12.3

Compares 3 field extension methods on static droplet:
  1. HFE (Hermite, O(h^6) 1D / O(h^3) 2D)
  2. Upwind (nearest-source, O(h^1))
  3. None (no extension, Gibbs oscillation)

Setup: R=0.25, rho_l/rho_g=2, We=10, N=64/128, 200 steps

Requires: Full NS pipeline (SimulationBuilder) — NOT yet runnable.
This script documents the experimental design and will be executed
once the NS pipeline supports configurable extension methods.

Usage:
    python experiments/ch12_hfe_ablation.py
"""

# ── Experimental Design (to be connected to NS pipeline) ────────────────

EXPERIMENT_SPEC = {
    "name": "HFE ablation study",
    "section": "§12.3",
    "domain": [0.0, 1.0, 0.0, 1.0],
    "droplet": {"center": [0.5, 0.5], "radius": 0.25},
    "density_ratio": 2.0,
    "weber_number": 10.0,
    "boundary": "wall",
    "gravity": False,
    "grids": [64, 128],
    "steps": 200,
    "projection": "non-incremental",
    "extension_methods": ["hermite", "upwind", "none"],
    "metrics": [
        "parasitic_velocity_peak",
        "laplace_pressure_relative_error",
        "divergence_linf",
        "mass_error",
    ],
}


def run_single(N, extension_method):
    """Run a single static droplet simulation.

    Parameters
    ----------
    N : int
        Grid resolution.
    extension_method : str
        "hermite", "upwind", or "none".

    Returns
    -------
    results : dict
        Keys: u_para_peak, dp_rel_error, div_linf, mass_error, stable
    """
    # TODO: Connect to SimulationBuilder once extension_method is configurable
    #
    # Pseudocode:
    #   builder = SimulationBuilder()
    #   builder.set_grid(N, N, 1.0, 1.0)
    #   builder.set_density_ratio(2.0)
    #   builder.set_weber(10.0)
    #   builder.set_extension_method(extension_method)  # <-- new config
    #   builder.set_initial_condition("static_droplet", R=0.25)
    #   sim = builder.build()
    #   for step in range(200):
    #       sim.step_forward(dt)
    #   return sim.diagnostics()
    raise NotImplementedError(
        f"NS pipeline integration pending for extension_method={extension_method}"
    )


def main():
    print("EXP-12C: HFE ablation study")
    print("=" * 60)
    print()
    print("Experimental design:")
    for key, val in EXPERIMENT_SPEC.items():
        print(f"  {key}: {val}")
    print()
    print("Status: PENDING — requires NS pipeline with configurable extension method")
    print()
    print("Expected output:")
    print("  Table: tab:hfe_ablation (6 rows: 2 grids × 3 methods)")
    print("  Figure: fig:hfe_ablation (parasitic velocity time series)")


if __name__ == "__main__":
    main()
