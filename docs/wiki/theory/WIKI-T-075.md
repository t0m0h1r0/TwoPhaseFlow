---
ref_id: WIKI-T-075
title: Discrete Operator Contract for the Stage-Split Buoyancy Predictor
category: theory
status: active
last_updated: 2026-04-25
---

# WIKI-T-075 — Discrete Operator Contract for the Stage-Split Buoyancy Predictor

## Purpose

This entry states the redesign as a discrete operator contract.

The relevant operators are:

- material maps `ρ_h(ψ_h), μ_h(ψ_h)`,
- explicit branches `C_h, V_h, B_h`,
- interface-band mask `I_{1,h}`,
- vertical assembly repair `T_{y,h}^{I₁}`,
- horizontal post-stage repair `S_{x,h}^{I₁}`,
- pressure closure `D_h β_h G_h`.

## Discrete Predictor Form

\[
u_{B,h}^{\dagger}
=
T_{y,h}^{I_1}
\left(
u_h^n + \Delta t\,B_h(\psi_h^n)
\right),
\]

\[
u_{\mathrm{pred},h}^{(0)}
=
u_{B,h}^{\dagger}
+
\Delta t\left(
C_h(u_h^n) + V_h(u_h^n)
\right),
\]

\[
u_{\mathrm{pred},h}^{(1)}
=
S_{x,h}^{I_1}
\left(
u_{\mathrm{pred},h}^{(0)}
\right),
\]

then use `V_h(u_pred^(1))` in the CN/Picard corrector.

## Required Invariants

1. **Identity outside the full dilated interface band**
2. **Same-locus closure with `β_h`, `G_h`, `D_h`**
3. **Protection against gradient-compatible buoyancy pollution**
4. **Multidimensional interface consistency**
5. **Stage separation between vertical assembly and horizontal `V(u_pred)` coupling**

## Current Best Realizations

- strongest: `buoyancy_stagesplit_fullbandx`
- cheaper approximation: `buoyancy_stagesplit_sharpx`

These are first-class solver modes and are bit-identical to the earlier
two-flag implementations.

## Cross-links

- mathematical foundation: `SP-U_buoyancy_predictor_well_balanced_foundation.md`
- discrete operator spec: `SP-V_discrete_buoyancy_predictor_operator_spec.md`
- stage-split redesign: `SP-T_stage_split_buoyancy_predictor_redesign.md`
- experiment verdicts: `WIKI-E-031`
