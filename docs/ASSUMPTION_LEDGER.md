# ASSUMPTION LEDGER

| ASM-ID | Assumption | Scope | Risk | Status |
|---|---|---|---|---|
| ASM-001 | `SimulationBuilder` is the sole construction path — no direct `__init__` construction | `src/twophase/` | HIGH | ACTIVE |
| ASM-002 | PPE Kronecker-product Laplacian has an 8-dimensional null space — `‖Lp−q‖₂` is NOT a valid pass/fail metric | `src/twophase/solver/ppe` | HIGH | ACTIVE |
| ASM-003 | `"pseudotime"` PPE solver (CCD Laplacian) is the consistent production solver; `"bicgstab"` (FVM matrix) is testing-only and approximate O(h²) | `src/twophase/solver/ppe` | HIGH | ACTIVE |
| ASM-004 | CCD boundary-limited orders: d1 ≥ 3.5 on L∞ is PASS; d2 ≥ 2.5 on L∞ is PASS — NOT interior O(h⁶)/O(h⁵) | `src/twophase/solver/ccd` | MEDIUM | ACTIVE |
| ASM-005 | Global PPE sparse system: LGMRES primary, `spsolve` (sparse LU) automatic fallback on non-convergence | `src/twophase/solver/ppe` | MEDIUM | ACTIVE |
| ASM-006 | Banded/block-tridiagonal systems (CCD Thomas, Helmholtz sweeps): direct LU — O(N) fill-in, efficient | `src/twophase/solver/ccd` | LOW | ACTIVE |
| ASM-007 | `SimulationConfig` is pure sub-config composition — no monolithic config class | `src/twophase/` | MEDIUM | ACTIVE |
| ASM-008 | Three symmetry-breaking root causes identified and fixed (2026-03-22): (1) Rhie-Chow FVM div at wall node N_ax, (2) PPE gauge pin at center (N/2,N/2), (3) capillary CFL safety factor | `src/twophase/` | HIGH | FIXED |
| ASM-009 | FVM/CCD mismatch in IPC+corrector fixed (2026-03-22): CCD replaced with FD in velocity_corrector.py and predictor.py IPC term | `src/twophase/` | HIGH | FIXED |
| ASM-010 | `docs/LATEX_RULES.md §1` is the authoritative LaTeX standard — all paper agents depend on it | `paper/` | MEDIUM | TODO: not yet populated |

## Format reference

`ASM-ID | assumption | scope: file/module path | risk: HIGH/MEDIUM/LOW | status: ACTIVE/FIXED/DEPRECATED/TODO`
