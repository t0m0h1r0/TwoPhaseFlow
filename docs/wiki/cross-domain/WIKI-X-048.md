---
ref_id: WIKI-X-048
title: "Ch14 Capillary Hodge Trial Ledger: Knowledge, Failures, and Falsified Routes"
domain: cross-domain
status: ACTIVE
tags: [capillary, hodge_projection, pressure_reaction, reinit, negative_knowledge, rca, trial_ledger]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
    description: "Chronological ResearchArchitect CHK rows through the capillary Hodge and variational pressure work"
  - path: docs/wiki/theory/WIKI-T-162.md
    description: "Current closed-interface capillary discretization policy"
  - path: artifacts/A/ch14_oscillating_droplet_zero_drive_rca_CHK-RA-CH14-OSC-ZERO-DRIVE-001.md
  - path: artifacts/A/capillary_variational_hodge_theory_verification_CHK-RA-CAP-HODGE-VERIFY-001.md
  - path: artifacts/A/capillary_static_dynamic_gate_verification_CHK-RA-CAP-STATIC-DYNAMIC-GATE-001.md
  - path: artifacts/A/capillary_variational_hodge_pitfalls_CHK-RA-CAP-HODGE-PITFALL-001.md
  - path: artifacts/A/ch14_component_hodge_n32_t1_validation_CHK-RA-CH14-CAP-IMPLEMENT-N32T1-001.md
  - path: artifacts/A/ch14_component_hodge_long_validation_CHK-RA-CH14-CAP-LONG-VFY-001.md
  - path: artifacts/A/ch14_reinit_endpoint_ledger_CHK-RA-CH14-REINIT-LEDGER-001.md
  - path: artifacts/A/ch14_phase_error_rca_CHK-RA-CH14-PHASE-RCA-001.md
  - path: artifacts/A/ch14_pressure_adjoint_residual_rca_CHK-RA-CH14-PRESSURE-ADJOINT-RCA-001.md
  - path: artifacts/A/ch14_pressure_adjoint_remedy_decision_CHK-RA-CH14-PRESSURE-ADJOINT-REMEDY-DECISION-001.md
  - path: artifacts/A/ch14_variational_pressure_impl_n32t1_CHK-RA-CH14-VARIATIONAL-PRESSURE-IMPL-N32T1-001.md
  - path: artifacts/A/ch14_variational_pressure_n32_t10_validation_CHK-RA-CH14-VARIATIONAL-PRESSURE-N32T10-001.md
  - path: artifacts/A/ch14_trace_riesz_runtime_n32_t1_CHK-RA-CH14-TRACE-RIESZ-N32T1-001.md
  - path: artifacts/A/ch14_hodge_solve_fix_verification_CHK-RA-CH14-HODGE-SOLVE-FIX-001.md
  - path: artifacts/A/ch14_hodge_norm_rca_CHK-RA-CH14-HODGE-NORM-001.md
depends_on:
  - "[[WIKI-X-041]]"
  - "[[WIKI-X-045]]"
  - "[[WIKI-X-046]]"
  - "[[WIKI-X-047]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-160]]"
  - "[[WIKI-T-161]]"
  - "[[WIKI-T-162]]"
  - "[[WIKI-T-163]]"
consumers:
  - domain: theory
    usage: "Read before proposing another capillary, Hodge, or reinit remedy"
  - domain: code
    usage: "Use as fail-close and diagnostic checklist for pressure/capillary implementations"
  - domain: experiment
    usage: "Use to distinguish falsified controls from current acceptance gates"
  - domain: paper
    usage: "Keep failures in wiki while preserving the paper's successful derivation narrative"
compiled_by: ResearchArchitect
compiled_at: 2026-05-07
---

# Ch14 Capillary Hodge Trial Ledger

## Purpose

This card compiles the reusable knowledge from the ch14 capillary Hodge
sequence: what was learned, what failed, which hypotheses were falsified, and
which trial routes must stay as negative knowledge.  It is not the active
scheme definition.  Use [[WIKI-T-162]] for the current theorem and implementation
policy; use this card to avoid repeating already-falsified reasoning.

## Final Reading

The core failure was never "the droplet is circular" or "the droplet is
elliptical".  The correct object is a finite-dimensional constrained
surface-energy variation on the same face complex used by projection and
transport:

```text
s = -M_f^{-1} T_f(q_c)^T d_q(sigma S_h)^T,
B =  M_f^{-1} T_f(q_c)^T d_q V_h^T,
h = s - G_A p - B mu,
D_f h = 0,
B^T M_f h = 0.
```

Any route that changes curvature samples, damping, CFL, smoothing, or benchmark
branches without closing this virtual-work identity is a symptom treatment, not
a solution.

## Trial Chronology

| Stage | What was tried or observed | Result | Retained knowledge |
|---|---|---|---|
| Zero-drive RCA | N32/T1 oscillating droplet with `range_projected` completed, conserved volume, but KE stayed `~1e-37` and velocity Linf stayed `3.57e-19`. | The capillary jump existed, but the production corrector received zero face acceleration. | Replacing `c_sigma` by `Pi_R c_sigma` in production constructs algebraic rest. Range projection is diagnostic/static-gate material only. |
| `none` control | `capillary_range_projection:none` produced nonzero one-step velocity and capillary face acceleration. | It proved that a drive existed, not that the raw cochain was physical. | "It moves" is weaker than "it is the Riesz representative of surface-energy work". |
| Component-Hodge slice | `component_hodge_augmented` removed the constant component reaction and restored oscillating-droplet motion. | Static KE became small and oscillating N32/T1 moved, but static Hodge residual was not theorem-grade and N16/N32/N64 residuals were nonmonotone. | Component reaction removal is necessary, but the raw curvature/affine cochain still needs a transport-adjoint Riesz proof. |
| Reinit endpoint ledger | Stored `q^n -> q_T -> q^{n+1}` fields. | Reinit could change apparent deformation even with zero velocity; in one smoke, `|q^{n+1}-q_T|` dominated `|q_T-q^n|`. | Shape change after reinit is not capillary work. Every capillary validation must split physical transport and profile projection. |
| Retired entropy-dual retraction | A fixed-stratum trace-preserving entropy-dual retraction candidate was explored. | N32/T10 produced abnormal shape behavior. | Retain [[WIKI-T-161]] as negative knowledge only; do not expose or implement its YAML surface. |
| Phase-error RCA | No-reinit oscillation was too slow/damped; reinit-on crossed too early. Grid-remap, physical viscosity, reference formula, and component over-removal were tested. | Current scalar `face_implicit` cochain plus one-component augmentation was under-stiff and non-Riesz; reinit separately contaminated phase measurement. | Phase error needs a surface-energy Hessian/transport VJP gate, not damping or Rayleigh rescaling. |
| Pressure representative RCA | FCCD scalar PPE looked symmetric, but face pressure reaction failed the kinetic Green identity. | `pressure_fluxes` returned a divergence-equivalent representative `G_var+Z` with `D_f Z=0`, not the pressure-work representative. | Scalar PPE closure alone is insufficient. Production pressure reaction must satisfy `G_A=-M_A^{-1}D_f^T W_p` and `L_A=D_fG_A`. |
| Variational pressure implementation | `pressure_force_contract: variational_adjoint` introduced a pressure-complex SSoT. | N32/T1 and N32/T10 static/oscillating runs moved and conserved volume much better than the frozen path. | Pressure reaction is a constrained-force representative, not a raw compact gradient chosen after the scalar solve. |
| Trace-Riesz runtime slice | `closed_interface_riesz` built a trace-vertex cochain and passed the same corrected cochain to PPE RHS and corrector. | Zero-drive was removed, but static circle still had finite-grid spurious current. | The force cochain must be critical for the discrete geometry and endpoint actually used; sampled continuum circles are not roundoff static oracles. |
| Hodge solve fix | Manufactured pure-range cochains were recovered to near roundoff after gauge-pinned Hodge solve. | Old large Hodge divergence was partly a solve artifact; remaining nonzero Hodge norm was not. | Separate projection algebra failure from force-cochain/static-critical failure. |
| Static-critical RCA | The finite-dimensional Euler--Lagrange residual of the sampled analytic circle was measured. | N32 sampled circle had a sizable vertex criticality ratio and was not a discrete constrained critical point. | Static validation must be shape-free and discrete: test constrained first variation, not visual roundness. |
| Conservative endpoint theory | The current solver transports nodal `psi` with conservative face fluxes, not trace vertices as a primary state. | The trace-vertex cochain was self-consistent under `C_K` but not under the solver's conservative endpoint. | Production must make the capillary VJP and transport endpoint identical, or fail closed on endpoint mismatch. |

## Falsified Hypotheses

| Hypothesis | Efficient test | Verdict | Lesson |
|---|---|---|---|
| The Rayleigh-Lamb reference is wrong. | Compare early no-reinit acceleration, zero crossing, and analytic reference. | Not the root cause. | Reference checks are controls, not a license to rescale stiffness. |
| Physical viscosity explains damping. | Fit the observed damping rate. | Rejected: fitted damping was much larger than physical viscosity. | Do not introduce artificial damping to match phase. |
| Dynamic grid remap causes early phase error. | Compare static-grid and dynamic-grid no-reinit probes. | Rejected for the early error: both showed similar early stiffness. | Grid controls are useful, but the force cochain remained central. |
| Component projection over-removes the oscillating mode. | Compare `none` and component mode one-step/short runs. | Rejected for early stiffness: dynamic drive remained. | Component projection removes the constant reaction; it is not the whole theorem. |
| PPE tolerance or scalar residual explains the residual. | Manufactured pure-range Hodge solve and gauge-pinned system. | Partly true for old divergence residual, false for remaining Hodge norm. | Always split linear algebra residual from physical force residual. |
| Shape recognition can identify static equilibrium. | Measure discrete constrained first variation on the sampled trace. | Rejected. | The scheme must work for arbitrary resolved nonconstant curvature modes and arbitrary fixed strata. |
| Visualization proves volume loss or symmetry breaking. | Check volume metrics, face cochains, velocity fields, and endpoint ledgers. | Visual inspection alone is insufficient. | Plots are diagnostics; conserved measures and face-space identities are the authority. |
| Near-singular faces should silently fall back. | Active-face/metric/rank gates. | Rejected as default. | The policy is fail-close unless the singularity is part of a proven quotient-space removal. |
| A high-order raw compact pressure gradient is automatically better. | Test Green identity and divergence-equivalent representative differences. | Rejected. | High order must be an SBP/Riesz pair; otherwise it can inject nonphysical pressure work. |
| `capillary_range_projection:none` is the production fix. | Static droplet residual and variational cochain checks. | Rejected. | Raw motion is not the same as discrete surface-energy consistency. |

## Negative Knowledge To Preserve

Do not re-promote these routes without a new theorem and a new falsification
artifact:

```text
damping,
blind CFL tuning,
curvature caps,
curvature smoothing,
FD/WENO/PPE fallback,
benchmark-name branches,
blanket c -> Pi_R c in production,
raw capillary_range_projection:none as final physics,
QP or least-squares minimization as physical law,
static circle/ellipse classification as an equilibrium gate,
post-reinit deformation as capillary work,
scalar PPE success as pressure-work success,
raw interface-band pressure images as pressure evidence.
```

## Current Positive Knowledge

The surviving contract is:

1. Build capillary work from a discrete surface-energy first variation, not from
   a standalone curvature sample.
2. Pull that first variation back through the same transport endpoint used by
   the solver.
3. Use the same face metric, divergence, pressure representative, and component
   columns in the Hodge projection and in the production corrector.
4. Treat pressure as a constraint reaction with a unique kinetic Green-adjoint
   representative, not as any divergence-equivalent face gradient.
5. Split reinit/profile motion from physical capillary work in every
   validation.
6. Fail closed when endpoint, material coefficients, active faces, metric,
   rank, or sign-power gates do not match the theorem object.

## CCD/FCCD/UCCD Connection

The capillary route must remain orthogonal to the choice of transport stencil
family.  CCD, FCCD, and UCCD may differ in interpolation, dissipation, and
boundary closures, but the capillary/projection contract is shared:

```text
same active face space,
same D_f,
same pressure action G_A,
same metric M_A,
same corrected capillary cochain in PPE RHS and corrector,
same endpoint ledger.
```

A high-order family is admissible only when it supplies the matching
SBP/Riesz-adjoint pair.  A raw high-order gradient that only gives the same
scalar divergence is not equivalent because `G_A+Z` with `D_f Z=0` can still
change pressure work and capillary release.

## How To Use This Card

For a new capillary proposal, first answer:

```text
What is the discrete energy S_h?
What is the transported state q_c?
What is T_f(q_c)?
What metric defines face work?
What is the active pressure reaction G_A?
Which component constraints B are removed?
Where is q^n -> q_T -> q^{n+1} recorded?
Which falsified shortcut does this proposal risk reintroducing?
```

If any answer is missing, keep the work in RCA/design space.  Do not implement
or document it as production physics.
