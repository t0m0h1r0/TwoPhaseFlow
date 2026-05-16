---
id: WIKI-L-009
title: "Interface Contracts: Runtime Scheme Interfaces and PPE Solver Boundary"
status: ACTIVE
created: 2026-04-10
updated: 2026-05-16
depends_on: [WIKI-L-010, WIKI-L-046, WIKI-X-054]
---

# Interface Contracts Reference

This card records the current code-facing abstraction map.  Older April
readings that list CCD-LU/IIM/iterative PPE solvers as the public production
set are historical; the active runtime path is selected through scheme
registration and the `SolverPPEOptions` stack.

## Core Interfaces

| Interface | File | Current role |
|---|---|---|
| `IPPESolver` | `src/twophase/ppe/interfaces.py` | Common PPE solve/update/cache/context interface. Matrix-free solvers are valid implementations and raise `MatrixAssemblyUnavailable` when a sparse matrix is intentionally unavailable. |
| `ILevelSetAdvection` | `src/twophase/levelset/interfaces.py` | Self-registering CLS transport schemes. Current production routes include `fccd_flux` / `fccd_nodal`; WENO5 remains reference-only. |
| `IReinitializer` | `src/twophase/levelset/interfaces.py` | Reinitialization interface with `update_grid()` for grid-aware implementations. |
| `ICurvatureCalculator` | `src/twophase/levelset/interfaces.py` | Curvature computation interface; psi-direct curvature is the active route, phi inversion is retained as legacy/reference. |
| `IFieldExtension` | `src/twophase/hfe/interfaces.py` | HFE/field-extension contract for smooth one-sided pressure or scalar extension across an interface. |
| `INSTerm` | `src/twophase/ns_terms/interfaces.py` | Navier--Stokes term interface with `compute(ctx)` for RHS contributions. |
| `IConvectionTerm` | `src/twophase/ns_terms/interfaces.py` | Self-registering momentum-convection scheme interface, including `uccd6` and `fccd_flux`/`fccd_nodal`. |

## PPE Runtime Boundary

The current pressure route has two layers:

| Layer | Active objects | Contract |
|---|---|---|
| High-order operator | `PPESolverFCCDMatrixFree` (`fccd_iterative`, aliases `fccd_matrixfree`, `fccd`) | Applies the phase-separated FCCD face operator, affine jump closure, direct boundary face space, and current interface-stress context. |
| Defect correction wrapper | `PPESolverDefectCorrection` | Iterates on high-order residuals; acceptance is residual convergence, not a fixed correction count. |
| Low-order bases | `PPESolverFDDirect`, `PPESolverFDMatrixFree` | Supply `L_L` for DC and must approximate the same physical PPE as the high-order route, including affine cut-face coefficients and boundary face space. |
| FVM public routes | `PPESolverFVMMatrixFree`, `PPESolverFVMSpsolve` | Explicit FVM projection routes for non-FCCD configurations and references; not a hidden fallback for failed active-geometry capillary runs. |

The YAML/front-door defaults now pass through
`src/twophase/simulation/ns_solver_builder.py` and
`src/twophase/simulation/ns_runtime_factories.py`, where
`ppe_solver=fccd_iterative`, `pressure_scheme=fccd_matrixfree`,
`ppe_dc_base_solver=fd_direct`, `ppe_coefficient_scheme=phase_separated`,
`ppe_interface_coupling_scheme=affine_jump`, and `boundary_face_space` are
assembled into the solver stack.  The older `src/twophase/ppe/factory.py`
registry remains the public factory for FVM/FD keyed solvers.

## Implementation Review Rule

For established theory changes, do not review only the concrete class that was
edited.  Follow [[WIKI-L-046]]:

- identify the exact discrete object and its owner;
- list every producer and consumer across YAML, builder, high-order operator,
  low-order base, RHS transform, corrector, diagnostics, and runner;
- check nonuniform, periodic, wall, cut-face, and rebuild paths;
- require fail-closed behavior when affine or boundary context is absent;
- add a regression that would fail for the wrong producer/consumer contract.

## Negative Knowledge

- Do not select CCD-LU, IIM, old iterative CCD, or legacy FVM paths as silent
  production fallbacks when the active phase-separated FCCD/HFE/DC route fails.
- Do not loosen DC tolerances or increase correction caps when `L_L` and `L_H`
  are different physical operators.
- Do not treat diagnostics that construct a different mathematical problem as
  evidence that the production route is correct.
