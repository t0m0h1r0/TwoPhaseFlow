---
ref_id: WIKI-L-023
title: "R-1.5 Implementation Roadmap: Minimal FVM-face ψ Gradient (SPEC, code unchanged)"
domain: code
status: SPEC  # Specification only; implementation deferred to CHK-155
superseded_by: null
sources:
  - path: docs/wiki/theory/WIKI-T-052.md
    description: R-1.5 theory and decision matrix
depends_on:
  - "[[WIKI-T-052]]: R-1.5 — Minimal FVM-Face σκ∇ψ Unification (theory)"
  - "[[WIKI-L-022]]: G^adj FVM-Consistent Pressure Gradient (the helper R-1.5 reuses)"
  - "[[WIKI-L-001]]: Algorithm Flow: 7-Step Time Integration Loop"
  - "[[WIKI-L-015]]: CuPy / GPU Backend Unification"
tags: [ns_pipeline, csf, balanced_force, h01_remediation, immediate_fix, spec, gpu_compatible]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# R-1.5 Implementation Roadmap: Minimal FVM-face ψ Gradient

## Status

**SPEC.** No code change has been committed. This entry specifies the planned change for execution in a separate worktree (CHK-155). It exists so that the implementing agent in that future session has a complete, unambiguous edit plan.

The theory is in [WIKI-T-052](../theory/WIKI-T-052.md). The helper being reused is documented in [WIKI-L-022](WIKI-L-022.md).

## Phase 1 — Minimal change (3 lines edited, 1 branch added)

### Target

[`src/twophase/simulation/ns_pipeline.py`](../../../src/twophase/simulation/ns_pipeline.py), Step 2 (CSF assembly), currently at L753–767:

```python
# ── 2. Curvature + balanced-force CSF ──────────────────────────
if sigma > 0.0:
    kappa_raw = self._curv.compute(psi)
    kappa = self._hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi))
    if self._kappa_max is not None:
        kappa = xp.clip(kappa, -self._kappa_max, self._kappa_max)
    if self._debug_diag:
        _dbg_kappa_max = float(self._backend.to_host(xp.max(xp.abs(kappa))))
    dpsi_dx, _ = ccd.differentiate(psi, 0)        # ← R-0 (current)
    dpsi_dy, _ = ccd.differentiate(psi, 1)        # ← R-0 (current)
    f_x = sigma * kappa * dpsi_dx
    f_y = sigma * kappa * dpsi_dy
else:
    f_x = f_y = xp.zeros_like(psi)
```

### Replacement

```python
# ── 2. Curvature + balanced-force CSF ──────────────────────────
if sigma > 0.0:
    kappa_raw = self._curv.compute(psi)
    kappa = self._hfe.apply(xp.asarray(kappa_raw), xp.asarray(psi))
    if self._kappa_max is not None:
        kappa = xp.clip(kappa, -self._kappa_max, self._kappa_max)
    if self._debug_diag:
        _dbg_kappa_max = float(self._backend.to_host(xp.max(xp.abs(kappa))))
    if not self._grid.uniform and self.bc_type == "wall":
        # R-1.5: use face-average gradient to match corrector pressure-gradient operator
        # (see WIKI-T-052; helper from WIKI-L-022)
        dpsi_dx = self._fvm_pressure_grad(psi, 0)
        dpsi_dy = self._fvm_pressure_grad(psi, 1)
    else:
        dpsi_dx, _ = ccd.differentiate(psi, 0)
        dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_x = sigma * kappa * dpsi_dx
    f_y = sigma * kappa * dpsi_dy
else:
    f_x = f_y = xp.zeros_like(psi)
```

### Diff summary

- **Lines added**: 6 (the `if not self._grid.uniform...` branch + 2 comment lines)
- **Lines changed**: 0 (the `dpsi_dx, _ = ccd.differentiate` lines are moved into the `else` branch unchanged)
- **Symbols added**: none (re-uses existing `self._fvm_pressure_grad`, `self._grid.uniform`, `self.bc_type`)
- **API impact**: none (private method called internally; signature unchanged)

The activation guard `not self._grid.uniform and self.bc_type == "wall"` is **identical** to the corrector guard at L814 (see [WIKI-L-022](WIKI-L-022.md) §"Velocity Corrector Guard"). This ensures both branches activate together — the cornerstone of the BF consistency argument in [WIKI-T-052](../theory/WIKI-T-052.md).

### Backend note

`_fvm_pressure_grad` already uses `self._backend.xp` correctly (see [WIKI-L-022](WIKI-L-022.md) §"Backend Note"). No GPU-specific changes are needed; the path is bit-exact CPU/GPU on the existing PCR-Thomas + CuPy stack.

## Phase 2 (optional) — θ-weighted face κ

**Defer until Phase 1 verification completes.** If `bf_residual_max` post-Phase-1 still shows non-trivial residuals on smoothly-varying $\kappa$ benchmarks (e.g. capillary wave with curvature gradient), upgrade to a face-centred curvature evaluation:

$$
\kappa_f = (1 - \alpha)\,\kappa_a + \alpha\,\kappa_b,
$$

where $\kappa_a, \kappa_b$ are node curvatures and $\alpha$ is the IIM-style face-position weight. Pattern reference: [`src/twophase/ppe/iim/stencil_corrector.py:232`](../../../src/twophase/ppe/iim/stencil_corrector.py#L232) (existing project convention).

This brings the BF residual on variable $\kappa$ from $\mathcal{O}(\Delta x^2)$ to $\mathcal{O}(\Delta x^4)$ — but only if the CSF model floor allows it (likely no improvement; see [WIKI-T-052](../theory/WIKI-T-052.md) §"Order of accuracy on variable κ").

**Do not implement Phase 2 prophylactically.** Wait for Phase 1 measurements.

## Phase 3 (long-range) — R-1 (FCCD) migration

When the FCCD PoC programme ([WIKI-T-046](../theory/WIKI-T-046.md), [WIKI-T-050](../theory/WIKI-T-050.md), [WIKI-T-051](../theory/WIKI-T-051.md)) completes, replace the `_fvm_pressure_grad` helper with `_fccd_face_grad` (TBD signature). Because the R-1.5 wiring of CSF and corrector both call the same `_fvm_pressure_grad` symbol, the migration is a **one-symbol replacement** (and possibly a one-line `import` change) — the surrounding code does not need to know whether the underlying operator is $G^{\text{face}}$ or $D^{\text{FCCD}}$.

This is the architectural payoff of R-1.5: it puts the system in the **same operator-coupling shape** that R-1 will need, so the eventual migration is mechanical rather than disruptive.

## Verification battery (CHK-155 deliverables)

To be executed by the implementing agent in a separate worktree, after Phase 1 commit:

1. **Static droplet equilibrium** ([WIKI-E-007](../experiment/WIKI-E-007.md) protocol).
   - Config: `experiment/ch12/configs/static_droplet_alpha15.yaml` (or equivalent).
   - Expected: `bf_residual_max` reduces from $\mathcal{O}(10^2)$–$\mathcal{O}(10^3)$ (R-0 measurement: 884) to $\mathcal{O}(10^{-12})$ or below.
   - **Pass criterion**: `bf_residual_max < 1e-10`.

2. **Sigma-zero regression** (`experiment/ch13/configs/ch13_02_sigma0.yaml`).
   - Expected: bit-exact reproduction (the new branch is dead under $\sigma = 0$).
   - **Pass criterion**: `np.allclose(out_R1.5, out_R0, atol=0.0, rtol=0.0)` for all snapshots.

3. **Capillary-wave survival** (`experiment/ch13/configs/ch13_02_waterair_bubble.yaml`, $T = 20$, $\alpha = 1.5$).
   - Expected: no late blow-up (the R-0 case blows up at $T \approx 12.6$).
   - **Pass criterion**: simulation completes; KE remains bounded; `bf_residual_max` stays $< 10^{-8}$.

4. **N-convergence** (re-run #3 at $N = 32, 64, 128$).
   - Expected: stable scaling; no resolution-dependent regression.
   - **Pass criterion**: results match R-0 trends on uniform grid (which uses CCD path), and improve monotonically on $\alpha = 1.5$ (which uses R-1.5 path).

5. **Uniform-grid regression** (`experiment/ch11/configs/cap_wave_uniform.yaml` or similar).
   - Expected: bit-exact reproduction.
   - **Pass criterion**: same as #2.

6. **Periodic-BC regression** (any periodic-BC config).
   - Expected: bit-exact (guard preserves CCD path).
   - **Pass criterion**: same as #2.

## Rollback procedure

R-1.5 is gated by a runtime branch. If unexpected behaviour is observed:

1. Revert the Phase-1 commit (`git revert <hash>`).
2. The system returns to R-0 immediately; no migration state to clean up.
3. No data-format changes; existing `.npz` snapshots remain valid.

## Estimated effort

| Phase | Edit lines | Test lines | New benchmarks | Author hours |
|---|---|---|---|---|
| Phase 1 (this entry) | 6 | ~50 (verification battery) | 0 (reuse existing configs) | 1–2 |
| Phase 2 (optional) | ~30 (face κ helper) | ~30 | 0 | 2–4 |
| Phase 3 (FCCD migration) | varies (depends on PoC outcome) | substantial | 1–2 | weeks |

Phase 1 is a single afternoon of work for the implementing agent; the bulk of CHK-155 is verification, not coding.

## Cross-references

- Theory: [WIKI-T-052](../theory/WIKI-T-052.md), [WIKI-T-044](../theory/WIKI-T-044.md), [WIKI-T-046](../theory/WIKI-T-046.md), [WIKI-T-050](../theory/WIKI-T-050.md), [WIKI-T-051](../theory/WIKI-T-051.md)
- Code precedent: [WIKI-L-022](WIKI-L-022.md) (`_fvm_pressure_grad` impl)
- Pipeline structure: [WIKI-L-001](WIKI-L-001.md) (7-step loop)
- Cross-domain map: [WIKI-X-018](../cross-domain/WIKI-X-018.md)
- Related symptom: [WIKI-E-030](../experiment/WIKI-E-030.md), [WIKI-T-045](../theory/WIKI-T-045.md)

## Velocity-side companion (CHK-158 update)

[WIKI-L-024](WIKI-L-024.md) delivers the **velocity-side** FCCD library: `FCCDSolver` / `FCCDConvectionTerm` / `FCCDLevelSetAdvection`. It targets the advection term rather than the pressure-gradient helper this entry plans — it is the *other half* of the H-01 remediation programme.

- WIKI-L-023 (this entry): pressure-side R-1.5 (face-average $\psi$ gradient, reusing `_fvm_pressure_grad`). Fix the CSF/corrector operator mismatch.
- [WIKI-L-024](WIKI-L-024.md): velocity-side Option B flux divergence (and Option C node-output) — closes the advection-side residual that remains after R-1.5.

The two can be deployed independently: L-023 Phase 1 unblocks WIKI-E-030 for static/quasi-static flows; L-024 Option B is required for the non-zero-velocity case where advective residuals become the binding constraint. Together they implement the full face-locus closure anticipated by [WIKI-T-055](../theory/WIKI-T-055.md) §4.1 (BF-preservation theorem).
