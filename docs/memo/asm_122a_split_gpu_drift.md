# ASM-122-A — SplitReinitializer GPU/CPU Pointwise Drift (CHK-124)

**Status:** CLOSED — **FUNDAMENTAL** (chaos-dominated, no structural root cause)
**Date:** 2026-04-11
**Scope:** diagnosis only, zero `src/twophase/` edits
**Probe:** `scripts/asm_122a_probe.py`
**Data:** `scripts/data/asm_122a/*.csv` (five {probe}_gpu.csv files; 旧 `experiment/ch11/results/asm_122a/` は CHK-235 で削除. 再現は `scripts/asm_122a_probe.py` を再実行)
**Depends on:** [[WIKI-T-028]], CHK-122 ledger row

## 1. Observation

CHK-122 (2026-04-12) recorded that `SplitReinitializer` on the GPU backend drifts pointwise from the CPU reference by up to ~3% (max_rel 3–7%) in `psi_*_split` on long exp11_21 Zalesak runs (N=128, ~1788 advect+reinit cycles). The drift is pre-existing (not introduced by CHK-122's `cn_diffusion_axis` dense-inverse) and physically benign: `L2_psi` matches the CPU trace to 4 sig figs, `mass_err` and `slot_psi` are unchanged, all 6 ε/h × method cases yield identical physical conclusions on both backends. `HybridReinitizer` on the same inputs shows only ~1e-9 drift.

Root-cause investigation was deferred in CHK-122 and taken up here as CHK-124.

## 2. Phase A — Small-N reproducer

Built `scripts/asm_122a_probe.py`: a two-pass harness that mirrors the exp11_21 step loop at `N=64` / `eps_ratio=1.0` / `method=split` / `reinit_freq=20`, running pass A on CPU and pass B on GPU (or CPU on local smoke), comparing ψ snapshots every 40 advect steps for 800 steps total. Mass, clip-boundary counts, max-abs, max-rel, and L₂-abs are recorded per checkpoint.

**Reproducer gate passed.** At step 800 on RTX 3080 Ti the baseline probe reports max_abs 2.978e-02, max_rel 3.250e-02, L₂-abs 8.574e-04 — a direct qualitative match to the exp11_21 N=128 observation (3–7% max_rel, L₂ matches to 4 sig figs). The mechanism is active at N=64; no escalation needed.

## 3. Phase B — Binary-search noise source

Five monkey-patched probes, each a runtime branch of the Phase A harness (no `src/` edits):

| # | Probe | Patch target | Hypothesis tested |
|---|---|---|---|
| 1 | `baseline` | — | Current Split hot path, measurement reference |
| 2 | `clip-deadband` | `reinit_split.reinitialize` | ψ~0/1 clip-boundary branch causes chaotic amplification |
| 3 | `cn-adi-cpu` | `reinit_ops.cn_diffusion_axis` cached `A_inv_dev` → `None` | CN-ADI dense-inverse (CHK-122) is the noise source |
| 4 | `ccd-no-ainv` | `ccd_solver._solvers[*]['A_inv_dev']` → `lu_solve` proxy | CCD wall-BC cached inverse (CHK-119) is the noise source |
| 5 | `matmul-all-cpu` | probes 3+4 active together | Additivity cross-check: if the two matmul sources compose linearly, drift = sum of individual drops |

Probe 4 replaces `info['A_inv_dev']` with a proxy object whose `__matmul__` delegates to `backend.linalg.lu_solve((info['lu'], info['piv']), rhs_flat)`. This leaves `_differentiate_wall_raw` byte-for-byte unmodified and avoids the dispatch-spoofing approach that would have broken the backend's `linalg` routing.

## 4. Results (RTX 3080 Ti, 2026-04-11)

### 4.1 Final-checkpoint drift vs probe

| probe | max_abs | max_rel | L₂-abs | Δ vs baseline | mass_diff |
|---|---|---|---|---|---|
| baseline | 2.978e-02 | 3.250e-02 | 8.574e-04 | — | −5.7e-15 |
| clip-deadband | 2.978e-02 | 3.250e-02 | 8.574e-04 | **0.0%** (identical) | −5.7e-15 |
| cn-adi-cpu | 2.560e-02 | 2.793e-02 | 7.178e-04 | −14.0% | +5.6e-16 |
| ccd-no-ainv | 2.600e-02 | 2.837e-02 | 7.328e-04 | −12.7% | −2.7e-15 |
| matmul-all-cpu | **3.258e-02** | **3.743e-02** | **1.739e-03** | **+9.4% max_abs, +103% L₂** | +2.0e-15 |

Every probe preserves mass to float64 precision (mass_diff at the O(1e-15) floor). Physical conservation holds across the entire probe matrix.

### 4.2 Drift curve (exponential growth)

At all five probes, drift grows **exponentially** from the float64 floor (~1e-13 at step 40) to O(1e-2) at step 800, spanning ~11 orders of magnitude in 760 steps. Empirical doubling time ≈ 20 advect steps, which is one reinit cycle. This is a clean chaotic Lyapunov-exponent signature: a constant noise floor injected at each reinit is amplified by a factor of e ≈ 2.72 per reinit cycle.

```
step   baseline    cn-adi-cpu  ccd-no-ainv  matmul-all-cpu
 160   1.58e-12    1.08e-12    1.57e-12     4.03e-12
 320   5.36e-11    4.18e-11    1.00e-10     5.42e-10
 480   2.07e-08    1.66e-08    1.73e-08     4.30e-08
 640   1.83e-05    1.41e-05    1.48e-05     7.41e-05
 800   2.98e-02    2.56e-02    2.60e-02     3.26e-02
```

## 5. Falsifications and classification

**H1 — Clip-boundary chaos (primary suspect going in).** Clip-deadband replaces `xp.clip(q, 0, 1)` with a variant that treats `[0, 1e-9] ∪ [1-1e-9, 1]` as a dead band, then falls back to clip. If the clip-branch decision were the amplifier, disabling the near-boundary branch would have suppressed the drift. **Result: bit-identical to baseline at every checkpoint.** The clip is never hit at the Zalesak slot edges in this trajectory — the interface is interior (`0 + ε ≤ ψ ≤ 1 − ε`) throughout. **Hypothesis falsified.**

**H2 — CN-ADI dense-inverse noise (CHK-122 secondary suspect).** `cn-adi-cpu` forces the GPU hot path through the Python Thomas sweep. Drift drops by 14%. **Non-zero contribution, but not dominant.**

**H3 — CCD wall-BC dense-inverse noise (CHK-119 secondary suspect).** `ccd-no-ainv` forces every CCD wall-BC solve — on the reinit AND on the upstream DissipativeCCDAdvection — through `lu_solve`. Drift drops by 13%. **Non-zero contribution, not dominant.**

**H4 — Linear additivity of the two matmul sources.** If H2 and H3 were independent structural sources, combining them should drop drift by roughly the sum: −14% − 13% ≈ −27% from baseline. **Result: drift _increases_ by +9% max_abs and +103% L₂.** Combining the two perturbations seeds a _different_ chaotic trajectory that drifts further from the CPU reference than baseline did. **H4 falsified; the two sources do not compose linearly because there is no linear structure to compose.**

**Conclusion — FUNDAMENTAL.** The ~3% pointwise drift is not attributable to any single op. No structural root cause exists. The mechanism is:

1. Noise seed: NumPy and CuPy implement `solve`, `lu_solve`, and `matmul` on different BLAS backends with different reduction trees. Every solve introduces O(1e-14 to 1e-11) relative FP rounding disagreement. This noise is at the float64 IEEE floor — it cannot be made smaller without changing the arithmetic.
2. Amplifier: the Zalesak slot edges are high-curvature, high-gradient regions where the DCCD compression flux and CN-ADI diffusion operator form a contractive-but-sensitive dynamical system. Reinit injects a small perturbation in each cycle; advection redistributes it. The effective Lyapunov exponent is ≈ ln(e)/20 steps ≈ 0.05 per step — modest, but multiplied by 800 steps yields an amplification factor of e^40 ≈ 2×10^17. A 1e-15 seed becomes an O(1) disagreement.
3. Why Hybrid is immune (order of magnitude): `HybridReinitizer` = `SplitReinitizer` then `DGRReinitizer`. DGR inverts ψ via the Heaviside logit (`invert_heaviside`), rescales to the canonical ε thickness, and re-applies the smooth heaviside. This step is a **Lyapunov-contractive projection**: it maps the current ψ onto the 1-parameter family `H_ε(φ)` of canonical profiles, erasing any pointwise perturbation that is not directly a shift of the signed distance function φ. It acts once per reinit cycle (i.e., once per ~20 advect steps), which is the same rate at which the noise seed is injected. The chaotic amplification loop is broken inside a single Lyapunov time, which is why Hybrid sits at ~1e-9 (accumulated noise over the last ~1 DGR step) instead of ~1e-2 (accumulated noise over all reinit cycles).

## 6. Recommendation

1. **Do not attempt a structural fix on `SplitReinitizer` alone.** No probe found a structural source; any "fix" would be fighting FP rounding at the float64 IEEE floor. The CHK-122 61.6 s end-to-end exp11_21 wall-clock stays untouched as required.
2. **Document the L₂-vs-pointwise distinction as a PR-5 carve-out for `SplitReinitizer` GPU.** `L2_psi` matches to 4 sig figs, `mass_err` and `slot_psi` are unchanged — the physical conclusion is preserved. Pointwise drift of O(1e-2) at the Zalesak slot edge is a carve-out from strict PR-5 bit-exactness on the GPU path of `method=split`, not a PR-5 violation.
3. **If a structural fix is ever demanded, the only architecturally sound option is to apply a Lyapunov contraction at the same cadence as the reinit cycle** — in effect, replace `method=split` with `method=hybrid` as the default. `SplitReinitizer` alone lacks a contractive projection and will always be chaos-amplified on long Zalesak-class problems, regardless of whether the noise seed is CuPy matmul or NumPy pairwise sum.
4. **No changes to existing tests, no test-level tolerance relaxation, no `xfail` marker.** `test_levelset.py` and `test_gpu_smoke.py` do not currently exercise the 800-step Zalesak regime; they stay out of scope. The probe script is the authoritative reproducer for this assumption.

## 7. Artifacts

- `scripts/asm_122a_probe.py` — 5-probe harness; local `python3 scripts/asm_122a_probe.py --probe baseline --N 64 --n-steps 100 --pass-b cpu` runs in <1 s with zero drift (determinism check). Remote GPU run: see `make push` + `ssh python` block in the ledger trail.
- `scripts/data/asm_122a/{probe}_gpu.csv` — 5 files, 20 checkpoints each, full drift curves (旧パス `experiment/ch11/results/asm_122a/` は CHK-235 で削除).
- `scripts/data/asm_122a/{probe}_cpu.csv` — 5 files, CPU-CPU determinism references (all zero).

## 8. Out of scope

- `DissipativeCCDAdvection` internals (pre-reinit noise path) — probe 4 already neutralized its CCD wall-BC matmul; the remaining advection-side noise is in the same chaos basin as the reinit-side noise and cannot be separated in this framework.
- `xp.sum` reduction tree order in `heaviside.apply_mass_correction` — mass is preserved to float64 floor across all probes, so the reduction is not a dominant noise source regardless.
- `HybridReinitizer` detailed Lyapunov analysis — qualitative argument above is sufficient for this classification.
- Extending the probe to `method=unified_dccd` or the WENO5 reinit path — not requested by user scope.
- Any fix that touches `src/twophase/` — explicitly excluded by Phase D of the investigation plan.
