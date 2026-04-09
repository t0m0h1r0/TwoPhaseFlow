# Zalesak Disk: Role in a Balanced-Force CLS Framework

## Problem

The Zalesak slotted disk is a standard advection benchmark, but its relevance
to a solver built on the Balanced-Force (BF) premise requires justification.
Two questions arise:

1. BF balances pressure gradient against surface tension (σκδ). Zalesak has
   σ=0 — does the test have meaning in this context?
2. CLS uses H_ε(φ), which cannot represent sub-ε features. The slot corners
   are inherently unresolvable. Is this a fundamental limitation or a
   practical one?

## Analysis

### Why Zalesak is still meaningful (as a component test)

BF assumes that κ is accurately computed from φ. If the advection/reinit
subsystem degrades φ, then κ degrades, and BF fails regardless of pressure
balancing. Zalesak tests whether this subsystem is robust — it is a
**precondition test** for BF, not a BF test itself.

### Why Zalesak is NOT a performance benchmark for this research

In any σ≠0 system, surface tension smooths corners on the capillary time
scale. The slotted-disk geometry with sharp right-angle corners cannot
physically exist when surface tension is present. Therefore:

- Shape preservation of sharp corners is **not a relevant performance metric**
  for a BF solver
- The smooth single vortex (LeVeque 1996) is the representative benchmark
  for real interface deformation

### CLS fundamental limit

CLS maps φ → ψ = H_ε(φ) with profile thickness ~2ε. Both sharp corners
(Zalesak) and thin filaments (single vortex) encounter the same fundamental
resolution limit: features < ε are unresolvable. The geometric manifestation
differs but the cause is identical.

### Reinitialization method choice

Experiments show split (Comp-Diff) favors Zalesak while hybrid (Comp-Diff +
DGR) favors single vortex. Requiring different methods for different
geometries undermines generality. Resolution:

- **Hybrid is the default method** — optimized for the physically relevant
  case (smooth interfaces with σ≠0)
- Zalesak results with hybrid are reported as a **stress test** showing the
  method does not catastrophically fail on sharp features, even though it is
  not optimized for them

## Conclusion

| Aspect | Zalesak | Single vortex |
|--------|---------|---------------|
| σ relevance | σ=0 (artificial) | σ-independent (deformation) |
| Geometry | sharp corners (unphysical for σ≠0) | smooth filaments (representative) |
| Role in §11 | stress test / robustness check | **primary performance benchmark** |
| Reinit method | split acceptable | hybrid recommended |
| Paper framing | "does not break" | "how well does it preserve" |

**Decision**: Hybrid reinitialization is the single recommended method.
Zalesak is positioned as a stress test with acknowledged CLS limitations,
not as a method selection criterion.
