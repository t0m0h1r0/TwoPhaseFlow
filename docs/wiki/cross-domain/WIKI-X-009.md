---
id: WIKI-X-009
title: "PPE Solver Policy: CCD Kronecker+LU Restricted to §11 Component Tests"
status: ACTIVE
created: 2026-04-15
depends_on: [WIKI-T-012, WIKI-T-024, WIKI-X-005]
---

# PPE Solver Policy: CCD Kronecker+LU ch11-Only Restriction

## Decision (2026-04-15, commit 050a900)

**PPESolverCCDLU (`ppe/ccd_lu.py`) is restricted to §11 component verification
experiments.** It MUST NOT be used in §12+ integration tests or §13 benchmarks.

## Root Cause: CCD D2 Indefiniteness

Analysis documented in [[WIKI-T-024]] found that the CCD second-derivative
operator D2 has **2 wrong-sign eigenvalues per axis**. The Kronecker product
2D PPE operator A = D2_x ⊗ I + I ⊗ D2_y therefore inherits indefiniteness.

Consequences:
- **Direct LU**: Factorization succeeds, but solution may amplify wrong-sign
  eigenmodes → pressure blow-up on real two-phase flows (ρ_l/ρ_g ≫ 1)
- **DC (defect correction)**: Stalls at O(h²) instead of expected O(h⁴⁺)
  because the iterative correction cannot converge past the indefinite modes

## Policy Codification

| Rule | Source | Content |
|------|--------|---------|
| PR-2 | `docs/03_PROJECT_RULES.md` | PPE ch12+ uses FVM (FD 2nd-order) only |
| PR-6 | `docs/03_PROJECT_RULES.md` | CCD Kronecker+LU = ch11 component scope |
| ASM-003 | Ledger | DEPRECATED — CCD-PPE solver is viable → FALSE for ch12+ |
| ASM-005 | Ledger | DEPRECATED — DC k=3 guarantees convergence → FALSE (indefinite) |

## Why CCD-LU Remains in §11

§11 component tests isolate the Poisson equation with **smooth manufactured
solutions** (known exact p, single-phase ρ=const). Under these conditions:
- Wrong-sign modes are not excited (smooth RHS has negligible projection)
- O(h⁶) spatial accuracy is verifiable (DC k=3 converges for smooth fields)
- The CCD differentiation kernel is being tested, not the PPE solver stability

The tests verify that the CCD spatial operator *itself* achieves the expected
accuracy order, independent of whether the solver is stable for two-phase PPE.

## Approved PPE Solvers for ch12+

| Solver | Key | Description |
|--------|-----|-------------|
| FD-LU | `"fd_lu"` | FVM O(h²) with direct LU — stable, default |
| GMRES+DC | `"gmres_dc"` | GMRES with FD-LU preconditioner + DC — 3D path |

## Known Violation

`experiment/ch12/exp12_crc_static_droplet.py` still uses `PPESolverCCDLU` —
flagged for migration to FD-LU.
