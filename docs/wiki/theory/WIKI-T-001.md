---
ref_id: WIKI-T-001
title: "CCD Method: Design Rationale and O(h^6) Compactness"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/04_ccd.tex
    git_hash: 7328bf1
    description: "CCD formulation: locality argument, coefficient derivation, truncation error"
  - path: paper/sections/04b_ccd_bc.tex
    git_hash: 7328bf1
    description: "Boundary conditions, block tridiagonal matrix structure"
consumers:
  - domain: L
    usage: "ccd_solver.py implements block Thomas solve with these coefficients"
  - domain: A
    usage: "Paper sections reference CCD theory for all spatial discretization"
  - domain: E
    usage: "Convergence verification relies on O(h^6) expectation"
depends_on: []
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-07
---

## Core Design Rationale

Two-phase flow with sharp interfaces creates the **locality trap**: standard high-order FD (e.g., 6th-order central: 7-point stencil) spans across the interface, sampling discontinuous properties and triggering Gibbs oscillations. The CCD method resolves this by achieving O(h^6) accuracy with only a **3-point stencil** (compact).

### Why Not WENO5?

WENO5 achieves O(h^5) but uses a 5-point stencil. For CCD-based PPE (O(h^6) pressure gradient), WENO5 creates an accuracy mismatch in the Balanced-Force condition. CCD provides O(h^6) with a 3-point stencil, maintaining operator consistency across all spatial terms.

## CCD Formulation

At each grid point i, CCD solves simultaneously for f'_i and f''_i from neighboring values {f_{i-1}, f_i, f_{i+1}}:

**Equation-I** (first derivative): alpha_1 f'_{i-1} + f'_i + alpha_1 f'_{i+1} = a_1(f_{i+1}-f_{i-1})/(2h) + b_1(f''_{i+1}-f''_{i-1})h/2

**Equation-II** (second derivative): beta_2 f''_{i-1} + f''_i + beta_2 f''_{i+1} = a_2(f_{i+1}-2f_i+f_{i-1})/h^2 + b_2(f'_{i+1}-f'_{i-1})/(2h)

### Coefficients (O(h^6) Taylor matching)

| Coefficient | Value |
|-------------|-------|
| alpha_1 | 7/16 |
| a_1 | 15/16 |
| b_1 | 1/16 |
| beta_2 | -1/8 |
| a_2 | 3 |
| b_2 | -9/8 |

Truncation errors: O(h^6) for both Eq-I and Eq-II.

## Block Tridiagonal Structure

The coupled (f', f'') unknowns form a 2x2 block tridiagonal system per grid line. Boundary closure uses one-sided schemes (O(h^3) at endpoints). The global system is solved by block Thomas algorithm in O(N) operations.

## Key Properties

- **Spectral resolution**: CCD resolves up to ~6 points/wavelength with < 1% dispersion error
- **Zero numerical dissipation**: Pure imaginary modified wavenumber -- requires DCCD filter for stability (see [[WIKI-T-002]])
- **Dual role**: Same operator serves as differentiator (known f -> f', f'') and elliptic solver (unknown p from PPE) -- see [[WIKI-X-002]]
