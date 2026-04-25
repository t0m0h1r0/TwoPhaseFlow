---
ref_id: WIKI-X-036
title: Stage-Split Buoyancy Predictor Redesign: Vertical Assembly Repair and V(u_pred)-Stage Horizontal Coupling
category: cross-domain
status: active
last_updated: 2026-04-25
---

# WIKI-X-036 — Stage-Split Buoyancy Predictor Redesign

## Core Statement

The latest ch13 predictor-closure ladder supports a **stage-split** redesign:

- the dominant **vertical** buoyancy mismatch is created during predictor
  assembly;
- the missing **horizontal** coupling becomes important mainly when
  `V(u_pred)` is evaluated.

So the admissible redesign is not a single uniform repair. It is:

1. full-band vertical repair during buoyancy predictor assembly,
2. x-side post-transform on the intermediate state seen by `V(u_pred)`,
3. unchanged final projection.

## Minimal Discrete Form

\[
\mathbf{u}_{B}^{\dagger}
=
T_y^{I_1}\!\left(
\mathbf{u}^n + \Delta t\,\mathbf{B}^n
\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}^{(0)}
=
\mathcal{A}\!\left(
\mathbf{u}^n,\,
\mathbf{C}^n,\,
\mathbf{V}(\mathbf{u}^n),\,
\mathbf{u}_{B}^{\dagger}
\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}^{(1)}
=
S_x^{I_1}\!\left(
\mathbf{u}_{\mathrm{pred}}^{(0)}
\right),
\]

\[
\mathbf{u}_\star
=
\mathbf{u}^n
+
\Delta t\left(
\mathbf{C}^n
+
\tfrac12 \mathbf{V}(\mathbf{u}^n)
+
\tfrac12 \mathbf{V}\!\left(\mathbf{u}_{\mathrm{pred}}^{(1)}\right)
+
\mathbf{B}^n
\right).
\]

Here `I₁` is the hard full two-axis dilated interface band.

## Why This Form

Empirical constraints:

- `buoyancy_fullband_local` is the best full predictor-side branch
- `buoyancy_fullband_local_y` captures most of the useful signal
- `mappedx` / `sharpx` added in assembly do not recover the missing x-side
  coupling
- `postfullbandx` recovers most of the gap
- `postsharpx` also recovers a substantial fraction of the gap

Therefore:

- y-side repair belongs in predictor assembly
- x-side residual belongs mainly at the `V(u_pred)` stage

## Design Consequence

The remaining problem is not a global “buoyancy stabilization” problem. It is a
more specific operator-design problem:

> how to construct the x-side post-stage transform `S_x^{I₁}` cheaply while
> preserving the beneficial coupling seen in `postfullbandx`.

The stage-split design is now also available as first-class solver modes:

- `buoyancy_stagesplit_fullbandx`
- `buoyancy_stagesplit_sharpx`

and these are bit-identical to the original explicit flag combinations.

## References

- detailed derivation: `SP-T_stage_split_buoyancy_predictor_redesign.md`
- predictor-side theory: `SP-Q_buoyancy_driven_predictor_assembly.md`
- redesign theorem baseline: `SP-S_buoyancy_predictor_redesign_theorem.md`
- experiment ladder: `WIKI-E-031`
