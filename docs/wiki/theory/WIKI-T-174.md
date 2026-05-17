---
ref_id: WIKI-T-174
title: "Capillary State Ownership: Interface Configuration or Cell Volume"
domain: theory
status: ACTIVE
tags: [ch14, capillary_wave, oscillating_droplet, state_ownership, interface_configuration, cell_volume, variational_geometry, q_phi_compatibility]
sources:
  - path: docs/wiki/theory/WIKI-T-077.md
    description: "Variational capillary energy and projection-native surface tension"
  - path: docs/wiki/theory/WIKI-T-173.md
    description: "Capillary-wave literature route and AO-Fast operator consistency"
  - path: docs/wiki/cross-domain/WIKI-X-055.md
    description: "Theory-first deliberation and hypothesis/falsification protocol"
  - path: artifacts/A/ch14_origin_reset_handoff_CHK-RA-CH14-ORIGIN-RESET-001.md
    description: "Extracted Ch14 origin-reset handoff and negative evidence from the oscillating-droplet branch"
  - path: docs/wiki/experiment/WIKI-E-064.md
    description: "Concrete baseline/screened graph-q runtime evidence preserved from the discarded source branch"
  - branch: codex/ra-ch14-osc-droplet-eighth-20260516
    commit: b0d36536
    description: "Screened graph-q runtime probe branch; not merged here because this card extracts theory knowledge only"
depends_on:
  - "[[WIKI-T-077]]"
  - "[[WIKI-T-173]]"
  - "[[WIKI-X-055]]"
  - "[[WIKI-E-064]]"
consumers:
  - domain: theory
    usage: "Use before designing a new capillary-wave or closed-droplet route after q/phi rebuild failures"
  - domain: code
    usage: "Use before implementing q/phi compatibility projection, graph rebuild, or capillary force ownership changes"
  - domain: experiment
    usage: "Use to define oracle probes that precede long T/8 droplet or capillary-wave runs"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Capillary State Ownership: Interface Configuration or Cell Volume

## Knowledge Card

The origin-reset lesson is that a capillary scheme must choose its owned
configuration before it chooses a q/phi reconstruction algorithm.

The continuous problem is governed by a material interface `Gamma(t)`, volume
conservation, incompressibility, and the surface energy
`E[Gamma] = sigma |Gamma|`.  A level-set field `phi` is a coordinate chart for
geometry.  A cell volume fraction field `q` is a finite-volume measurement of
where that geometry cuts the mesh.  Neither `phi` nor `q` is automatically the
physical owner unless the scheme says so and derives transport, capillary
variation, projection, and diagnostics from that choice.

The rejected hybrid is:

```text
transport q as if it is primary
  -> rebuild a smooth phi/graph as if geometry is primary
  -> compute capillary force from the rebuilt geometry
  -> require exact q compatibility afterward
```

This hybrid can be overconstrained.  A transported high-dimensional `q` field
may not lie on the smooth-interface manifold represented by the chosen
`phi`/graph chart.  Enforcing all of `q` exactly can make the interface jagged;
discarding incompatible q modes can make the graph smooth but change the
conserved object.  Tolerance weakening, smoothing, rebuild skipping, or CFL
retuning does not answer this state-ownership question.

## Two Admissible Formulations

### A. Interface-Configuration Primary

Own a smooth discrete interface configuration `Gamma_h`.

```text
Gamma_h^n
  -> advect/project Gamma_h under the material velocity
  -> enforce volume constraints on Gamma_h
  -> compute q_h = Q_h(Gamma_h) only as a derived measure
  -> compute capillary work as delta E[Gamma_h]
  -> project velocity/pressure in the matching face metric
```

This formulation is natural for smooth capillary waves and oscillating
droplets.  A graph capillary wave and a closed droplet are different charts of
the same principle, not different physics branches.  The chart may be
`eta(x)`, a closed curve `Gamma(theta)`, a spline, or another interface
coordinate; the energy variation and volume constraint remain the same.

The first oracle for this route should be small:

```text
graph capillary wave: eta(x) -> Q_h(eta), E[eta], delta E/delta eta
closed droplet: r(theta) or Gamma(theta) -> Q_h(Gamma), E[Gamma], volume
```

The oracle must predict force sign, symmetry, energy trend, and T/8 phase
before production runtime wiring is attempted.

### B. Cell-Volume Primary

Own the conservative cell-volume field `q`.

```text
q^n
  -> conservative transport of q
  -> define a discrete perimeter/surface energy E_h[q]
  -> compute capillary force as a variational derivative in q-space
  -> project velocity/pressure using the same q-space metric
```

This formulation treats exact cell-volume conservation as the primary law.
It must not reconstruct `phi` merely to borrow curvature from a different
state space.  If this path is selected, the hard problem is the design of
`E_h[q]` and its discrete variation, not a smoother q-to-phi postprocessor.

## Root Hypotheses to Carry Forward

| Hypothesis | Theory Prediction | Falsifying Probe |
|---|---|---|
| Transported `q` has incompatible modes for the chosen smooth chart. | Exact q projection makes `phi` jagged or needs topology movement. | Project analytic chart-derived q and transported q through the same constrained solve; only transported q fails. |
| Graph rebuild appears compatible because it redefines q from the graph. | `compat_linf=0` can hide q erasure if q is recomputed after rebuild. | Compare pre-rebuild q, post-rebuild q, and `Q_h(phi)` before any diagnostic overwrite. |
| Screened q/phi projection is solving the wrong problem. | Better metrics improve smoothness but still fail hard compatibility or topology gates. | Direct constrained optimization succeeds where residual projection fails without relaxing tolerance. |
| Capillary force and transport are derived from different state variables. | Symmetry or energy fails even when q/phi residuals are small. | Configuration-primary oracle gives correct force sign/phase while hybrid runtime does not. |
| Closed droplet and capillary wave are being treated as separate fixes. | Branch-specific conditions accumulate and fail outside their chart. | Same variational interface oracle supports both graph and closed-curve charts. |

## Decision Gate

Before the next implementation, answer:

```text
1. What is the owned capillary configuration: Gamma_h or q?
2. Which object is conserved by construction, and which object is derived?
3. Where is surface energy defined?
4. In which metric is the energy variation converted to face acceleration?
5. Which chart represents capillary waves?
6. Which chart represents closed droplets?
7. What proves that both charts implement the same variational principle?
8. What diagnostic can expose q erasure or phi jaggedness before long runs?
```

If these answers are missing, more q/phi rebuild code is premature.

## Forbidden Shortcuts

- Treating "closed surface Riesz is active" as a special condition that changes
  the theory.
- Solving capillary waves and closed droplets with unrelated code paths unless
  they are explicitly different charts of the same variational law.
- Relaxing q/phi tolerance, skipping rebuild, smoothing curvature, adding
  damping, or retuning CFL as the primary fix.
- Replacing the paper's pressure/projection family with FD, WENO, monolithic
  PPE, or hidden CPU fallback to make a run survive.
- Accepting a visually smooth interface without pre/post q and energy checks.
