---
ref_id: WIKI-X-002
title: "CCD Dual Role: Differentiator and Elliptic Solver"
domain: cross-domain
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/04_ccd.tex
    git_hash: 7328bf1
    description: "CCD as differentiation operator"
  - path: paper/sections/09_ccd_poisson.tex
    git_hash: 7328bf1
    description: "CCD as elliptic solver (sec:ccd_elliptic)"
  - path: paper/sections/05_grid.tex
    git_hash: 7328bf1
    description: "Metric computation as self-referential CCD application"
consumers:
  - domain: L
    usage: "ccd_solver.py block Thomas machinery serves both roles"
  - domain: T
    usage: "Theoretical foundation for operator consistency"
  - domain: A
    usage: "Key design argument for monograph's unified CCD approach"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-012]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Role 1: Differentiation Operator (known f -> f', f'')

Given known function values {f_i}, the CCD block Thomas solve produces O(h^6) approximations of f'_i and f''_i simultaneously. Applications:

| Application | Input f | Output needed | Section |
|------------|---------|---------------|---------|
| CLS advection flux | psi (level set) | psi' (advection) | S7 |
| Curvature | psi | psi', psi'' (kappa formula) | S3 |
| NS convection | u, v | du/dx, du/dy (advective derivative) | S10 |
| Metric coefficients | x(xi) | dx/dxi, d^2x/dxi^2 (Jacobian) | S5 |
| Pressure gradient | p | dp/dx, dp/dy (corrector step) | S10 |

## Role 2: Elliptic Solver (unknown p from PPE)

The same CCD operator, when applied to the unknown pressure p, produces the CCD-Poisson operator L_CCD. The PPE becomes:

L_CCD(p) = q (RHS from divergence of predicted velocity)

This is a larger block system (coupling pressure, its first and second derivatives) but uses the **identical block Thomas machinery**.

### Variable-Density Extension

For div((1/rho) * grad(p)), the product-rule expansion gives two CCD-evaluated terms:
- (1/rho) * p'' (CCD second derivative of p)
- (d(1/rho)/dx) * p' (CCD first derivative of p, multiplied by density gradient)

Both p' and p'' are simultaneously available from the CCD solve -- no additional computation.

## Self-Referential Application: Metric Computation

In S5, CCD computes the grid Jacobian J = dx/dxi from the coordinate mapping x(xi). This means CCD evaluates the metric coefficients that define the non-uniform grid on which CCD itself operates -- a self-referential but well-posed application since x(xi) is known analytically or from the grid generation algorithm.

## Design Significance

This dual role is the central architectural argument of the monograph: a single compact operator (3-point stencil, O(h^6)) handles ALL spatial discretization tasks, maintaining **operator consistency** across the Balanced-Force condition (see [[WIKI-T-004]]). If different operators were used for pressure gradient vs surface tension, O(h^2) residual forces would appear as parasitic currents.
