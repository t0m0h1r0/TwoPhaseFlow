#!/usr/bin/env python3
"""
EXP-12D: Density ratio sweep — §12.4

Tests CSF + smoothed Heaviside monolithic solver at increasing density ratios
to identify the dynamic breakdown threshold in the full NS pipeline.

Setup: Static droplet R=0.25, We=10, N=64, HFE ON, 200 steps
Density ratios: rho_l/rho_g = 2, 3, 5, 10

Requires: Full NS pipeline (SimulationBuilder) — NOT yet runnable.

Usage:
    python experiments/ch12_density_sweep.py
"""

EXPERIMENT_SPEC = {
    "name": "Density ratio sweep",
    "section": "§12.4",
    "domain": [0.0, 1.0, 0.0, 1.0],
    "droplet": {"center": [0.5, 0.5], "radius": 0.25},
    "weber_number": 10.0,
    "boundary": "wall",
    "gravity": False,
    "grid": 64,
    "steps": 200,
    "projection": "non-incremental",
    "extension_method": "hermite",
    "density_ratios": [2, 3, 5, 10],
    "metrics": [
        "parasitic_velocity_peak",
        "laplace_pressure_relative_error",
        "divergence_linf",
        "mass_error",
        "stable_bool",
        "breakdown_step",
    ],
}


def main():
    print("EXP-12D: Density ratio sweep")
    print("=" * 60)
    print()
    print("Experimental design:")
    for key, val in EXPERIMENT_SPEC.items():
        print(f"  {key}: {val}")
    print()
    print("Status: PENDING — requires NS pipeline execution")
    print()
    print("Expected output:")
    print("  Table: tab:density_limit (4 rows: rho = 2, 3, 5, 10)")
    print("  Expected: rho <= 5 PASS, rho = 10 FAIL (consistent with §11.5)")


if __name__ == "__main__":
    main()
