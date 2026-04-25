---
ref_id: WIKI-T-076
title: "Projection-Closure Theorem for Phase-Separated FCCD"
domain: theory
status: ACTIVE
superseded_by: null
tags: [fccd, ppe, projection, variable_density, phase_separated, nonuniform_grid]
compiled_by: Codex
compiled_at: "2026-04-25"
---

# Projection-Closure Theorem for Phase-Separated FCCD

## Statement

For a variable-density fractional-step method, the pressure solve and velocity
corrector form a discrete projection only when they share the same face-space
operator:

```text
L_h = D_f A_f G_f.
```

Here `G_f` maps nodal pressure to normal-face gradients, `A_f` is the
normal-face inverse-density coefficient, and `D_f` maps face fluxes to nodal
divergence. On non-uniform wall grids, `D_f` includes the wall
control-volume rows and physical node widths.

## Phase-separated coefficient

For phase-separated PPE,

```text
A_f = (1/rho)_f^sep
```

with cross-phase faces cut:

```text
A_f(i,j) =
  2/(rho_i + rho_j), if i and j are in the same phase,
  0,                otherwise.
```

This is not interchangeable with the harmonic mixture coefficient. Once the PPE
uses `A_f^sep`, the corrector must use `A_f^sep` too.

## Residual identity

If the PPE solves

```text
D_f A_f^PPE G_f p = D_f u_f^*/dt
```

but the corrector applies

```text
u_f^{n+1} = u_f^* - dt A_f^corr G_f p,
```

then

```text
D_f u_f^{n+1}
  = -dt D_f[(A_f^corr - A_f^PPE)G_f p].
```

For phase-separated PPE with mixture-density correction, this defect is
interface-supported. At water-air density ratios it becomes a stiff
projection-residual source.

## Non-uniform-grid corollary

Matching the symbolic method name is insufficient. The equality must hold with:

- the same physical coordinates,
- the same face gradient `G_f`,
- the same face divergence `D_f`,
- the same wall rows and node-control-volume widths,
- the same phase-cut policy in `A_f`.

This is why the clean fix adjusted both the FCCD projection divergence rows and
the phase-separated pressure-flux coefficient path.

## Debugging implication

Before interpreting blowup as a time-integrator, advection, level-set, or
buoyancy-model failure, test:

```text
projection-side D_f A_f G_f p == PPE-side apply(p)
```

for random `p` and representative `rho`, excluding gauge-pinned DOFs.

## Related

- short paper: `docs/memo/short_paper/SP-X_projection_closure_trial_synthesis.md`
- code contract: `docs/wiki/code/WIKI-L-033.md`
- experiment synthesis: `docs/wiki/experiment/WIKI-E-032.md`
- earlier closure note: `docs/wiki/code/WIKI-L-032.md`
