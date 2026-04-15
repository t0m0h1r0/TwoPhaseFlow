---
ref_id: WIKI-E-021
title: "Ch12 Re-Run Result Deltas: 3 Changed Values, 1 Reversed Finding"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - commit: "a65995e"
    description: "ch12 Group E: nonuniform grid + capillary + parasitic re-run (18/18)"
  - commit: "752b9f3"
    description: "paper: sync ch12 tables with re-run results"
  - commit: "bc98906"
    description: "fix: benchmarks use absolute imports to avoid tools/simulation mismatch"
depends_on:
  - "[[WIKI-E-014]]"
  - "[[WIKI-M-009]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-15
---

# Ch12 Re-Run Result Deltas

[[WIKI-E-014]] (2026-04-10) documented the design of four gap-filling
experiments. On 2026-04-15, ch12 underwent a complete clean-state re-run
(Groups A-E, 18 experiments, commits `728aefc` to `a65995e`). Three numerical
results changed significantly; one qualitative finding reversed.

---

## Delta 1 — Parasitic Flow Ratio (Exp 12-16): 11x to 69x

| Metric | Old (WIKI-E-014) | Re-run |
|--------|------------------|--------|
| FD/CCD parasitic current ratio (N=64) | 11x | **69x** |
| CCD slope | — | 2.4 |

**Root cause:** Previous run had stale partial results that contaminated
the comparison. Clean-state baseline confirms CCD balanced-force advantage
is much larger than previously measured.

**Paper impact:** Updated in sections 12a (force balance) and 12h (error
budget), commit `752b9f3`.

---

## Delta 2 — Capillary CFL Scaling Exponent (Exp 12-15): 1.505 to 1.82

| Source | Exponent |
|--------|----------|
| Theory (exact) | 1.500 (= 3/2) |
| Old (WIKI-E-014) | 1.505 |
| Re-run (clean state) | **1.82** |

The old value (1.505) was numerically coincident with the theoretical 3/2.
The re-run value (1.82) deviates, indicating the CCD discretization
introduces a higher effective CFL constraint than the continuous dispersion
relation predicts.

**Paper impact:** Updated in sections 12d and 12h, commit `752b9f3`. Paper
now reports the measured 1.82 with a note that theoretical 3/2 is the lower
bound.

---

## Delta 3 — Nonuniform-Grid Mass Conservation: Improvement to Degradation

**Reversed qualitative finding.**

| Source | alpha=2 Mass Conservation |
|--------|--------------------------|
| Old (WIKI-E-014 context) | Improvement over alpha=1 |
| Re-run (Exp 12-17) | **Degradation** |

[[WIKI-E-017]] showed 100-300x improvement for the NS grid-rebuild scenario
(100 steps, N=32, per-step mass correction). The ch12 re-run used different
parameters where interpolation diffusion accumulates faster than the
correction saves, reversing the finding.

**Paper impact:** Updated in sections 12g (nonuniform grid) and 12h (error
budget), commit `752b9f3`.

---

## Delta 4 — Absolute Import Fix (Benchmarks)

Not a numerical delta but a correctness fix affecting all ch12 benchmark
scripts.

**Problem:** `from ..simulation import TwoPhaseNSSolver` in
`src/twophase/tools/benchmarks/` resolved to `twophase/tools/simulation`
(non-existent) instead of `twophase/simulation`. Python relative import
resolution at package depth >1 landed in the wrong sibling.

**Fix** (commit `bc98906`): Replace all relative imports with absolute
imports in 5 benchmark files:

- `presets.py`
- `rayleigh_taylor.py`
- `rising_bubble.py`
- `stationary_droplet.py`
- `zalesak_disk.py`

**Rule:** Any module more than 1 level deep inside a package must use
absolute imports when the package root is on `sys.path`.

---

## Paper Impact Summary

| Section | Change |
|---------|--------|
| 12a force balance | Hydrostatic table values updated |
| 12c time accuracy | C_cross 0.23 to 0.22; viscous O(dt^2.0) confirmed |
| 12d high-Re DCCD | Capillary CFL exponent 1.505 to 1.82; Galilean N=128 row removed |
| 12g nonuniform grid | Mass conservation finding reversed |
| 12h error budget | HFE, curvature, parasitic ratio, CFL exponent all updated |

---

## Cross-References

- [[WIKI-E-014]] — Original entry documenting experiment designs
- [[WIKI-E-017]] — NS grid-rebuild (improvement finding partially contradicted)
- [[WIKI-E-018]] — Nonuniform grid NS convergence (related context)
- [[WIKI-M-009]] — Re-run methodology that generated these results
- [[WIKI-L-017]] — GPU patterns including N+1 and absolute import fixes
- [[WIKI-P-007]] — Formal review corrections also affecting 12h on same day
