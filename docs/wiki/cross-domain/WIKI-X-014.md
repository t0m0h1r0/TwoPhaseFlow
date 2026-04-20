---
ref_id: WIKI-X-014
title: "Non-Uniform Grid + Dynamic Interface: Stability Map and Recommended Defaults"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - path: "docs/memo/適用戦略_非一様格子動的界面_実問題導入プロトコル.md"
    description: "Real-problem deployment protocol: 3-phase on-boarding"
  - path: "docs/memo/実験計画_非一様格子動的界面ゲート.md"
    description: "Dynamic gate experiment plan and chronological log"
  - path: "docs/memo/検証_ch13_非一様格子へのconsistent_iim適用可否.md"
    description: "Ch13 applicability check for consistent_iim"
consumers:
  - domain: E
    usage: "Configuration reference for all non-uniform grid experiments"
  - domain: A
    usage: "Paper §12–§13: non-uniform grid deployment boundary documentation"
depends_on:
  - "[[WIKI-T-034]]"
  - "[[WIKI-T-035]]"
  - "[[WIKI-T-036]]"
  - "[[WIKI-E-023]]"
  - "[[WIKI-E-024]]"
  - "[[WIKI-E-025]]"
  - "[[WIKI-X-012]]"
  - "[[WIKI-E-020]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-16
---

# Non-Uniform Grid + Dynamic Interface: Stability Map and Recommended Defaults

Cross-cutting reference synthesizing theory ([[WIKI-T-034]], [[WIKI-T-035]]) and
experiment ([[WIKI-E-023]], [[WIKI-E-024]]) into actionable defaults, monitoring
protocols, and deployment boundaries.

---

## 1. Applicability Scope

| Dimension | Supported |
|---|---|
| 2D, wall-BC-primary, two-phase flow | Yes |
| $\alpha_\text{grid} > 1$ (non-uniform) | Yes |
| Dynamic interface (translation, capillary) | Yes |
| 3D | Not tested |
| $\rho_l/\rho_g > 20$ | Not stable |
| `consistent_gfm` mode | Not yet implemented (skeleton) |

---

## 2. Recommended Defaults

| Parameter | Value | Rationale |
|---|---|---|
| `reproject_mode` | `consistent_iim` | [[WIKI-E-023]]: zero rejects, $u_\text{peak}$ reduction |
| `reinit_method` | `dgr` | [[WIKI-T-030]]: local grid-width reinitialization |
| `grid_rebuild_freq` | $\ge 10$ | [[WIKI-E-023]] exp12_21: $10^{17}$ reduction in $u_\text{peak}$ |
| `eps_factor` | 1.0 | [[WIKI-E-024]] exp13_90: 38% sharpening vs 1.5, stable |
| `phi_primary_transport` | `True` (recommended) | [[WIKI-E-025]] exp13_91: machine-precision mass conservation |
| `CFL` | $\le 0.05$ (default), $\le 0.03$ (high-$\sigma$) | exp12_22, exp13_90 |

Auto-guard: `alpha_grid > 1.0` with `rebuild_freq == 1` is automatically bumped
to `rebuild_freq = 10` by the pipeline.

---

## 3. Density Ratio Stability Map

| $\rho_l / \rho_g$ | Status | Configuration |
|---|---|---|
| $\le 10$ | Well-tested; both legacy and IIM stable | Default |
| $= 20$ | Stable with tuning | CFL $\le$ 0.04, reinit_every=2, rebuild_freq $\ge$ 12 |
| $= 50$ | **Beyond current stable regime** | — |

Evidence: [[WIKI-E-023]] exp12_22.

---

## 4. Three-Phase On-Boarding Protocol

### Phase A: Representative Case Mapping (1--2 days)

1. Map target Re, We, $\rho$-ratio to exp12_20 gate configuration.
2. Simplify initial interface to translate/capillary minimum pair.
3. Run on remote GPU (`make cycle`).
4. **Acceptance:** no crash, $\text{mass\_err} \le 10^{-2}$, $\max|u| \le 10^3$.

### Phase B: Near-Real Sweep (2--4 days)

1. Sweep $N$ and $\alpha$ for grid sensitivity.
2. Map `rebuild_freq` vs CFL stability region.
3. Identify `iim_backtrack_accepts` high-frequency zones.

### Phase C: Template Fixation (1--2 days)

1. Produce YAML template with finalized settings.
2. Fix alert thresholds.
3. Define fail-fast + fallback policy.

---

## 5. Runtime Monitoring Protocol

### Minimum required metrics

| Category | Metrics |
|---|---|
| Physical | `mass_err(t)`, `u_peak(t)`, `div_l2(t)` |
| Reprojection | `accept_ratio`, `backtrack_ratio` |

where:
- `accept_ratio = iim_accepts / iim_attempts`
- `backtrack_ratio = iim_backtrack_accepts / iim_accepts`

### Alert thresholds

| Condition | Action |
|---|---|
| `accept_ratio < 0.7` for 3 consecutive intervals | Adjust config (reduce CFL or increase rebuild_freq) |
| `backtrack_ratio > 0.5` sustained | Enter conservative mode |
| `mass_err` growth + `backtrack_ratio` rise simultaneous | Return to Phase A diagnosis |

Evidence: [[WIKI-E-024]] exp13_90 showed backtrack_ratio jumping from 6% to 43%
immediately before numerical failure.

---

## 6. Fallback Sequence

1. `consistent_iim` with line-search backtracking (primary)
2. `legacy` reprojection (same step, temporary)
3. Relax `rebuild_freq` cadence

**Never use** `variable_density_only` — see [[WIKI-T-034]] §5.

---

## 7. Open Items

1. `consistent_gfm` mode instantiation (currently skeleton, falls back to legacy).
2. 3D / high-density-ratio extrapolation verification.
3. Theoretical basis for acceptance gate threshold (currently $1.05 \times \text{div}_\text{base}$, empirical).
4. Adaptive rebuild trigger based on interface displacement rather than fixed step count.
5. Rising bubble full $T=1.2$ on non-uniform grid — collapses before $t < 10^{-3}$
   ([[WIKI-E-025]]).

---

## One-Line Summary

Non-uniform dynamic interface deployment is feasible with `consistent_iim` + DGR +
`rebuild_freq` $\ge 10$, bounded by $\rho \le 20$; requires 3-phase on-boarding
and runtime monitoring of `accept_ratio`/`backtrack_ratio`.

## Related research proposals (2026-04-20)

The $\rho \le 20$ bound and `accept_ratio` mechanics are effects of the H-01 metric
mismatch ([[WIKI-T-045]], [[WIKI-E-030]]). Candidate remediations raising the bound:

- [[WIKI-T-046]] — FCCD face-unified gradient ([SP-A](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md))
- [[WIKI-X-018]] — H-01 remediation map
- [[WIKI-T-047]] / [[WIKI-T-048]] — ridge–Eikonal hybrid for topology change ([SP-B](../../memo/short_paper/SP-B_ridge_eikonal_hybrid.md))
