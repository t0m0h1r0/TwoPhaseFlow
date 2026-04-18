---
ref_id: WIKI-X-015
title: "Numerical Simulation Debugging: Theory-First Root-Cause Methodology"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch13/config/exp13_01_a1.0_dgr_noreinit.yaml
    description: "Set A1 isolation exp — no reinit → blowup (proof: fold forms without reinit)"
  - path: experiment/ch13/config/exp13_01_a1.0_dgr_hybrid.yaml
    description: "Set A2 isolation exp — hybrid → stable but wrong D(t) (2nd failure mode)"
  - path: experiment/ch13/config/exp13_01_a1.0_d4.yaml
    description: "Set D4 — every-500 hybrid → blowup (rules out reinit-frequency hypothesis)"
  - path: experiment/ch13/config/exp13_01_a1.2_f1.yaml
    description: "Set F1 — no reinit α=1.2 → blowup (confirms reinit necessary)"
  - path: docs/wiki/theory/WIKI-T-030.md
    description: "DGR theory — written before fix was implemented"
  - path: docs/wiki/experiment/WIKI-E-027.md
    description: "DGR blowup full investigation (CHK-133)"
depends_on:
  - "[[WIKI-T-030]]: DGR theory including Limitations section"
  - "[[WIKI-E-027]]: DGR blowup root-cause investigation"
  - "[[WIKI-X-014]]: Non-uniform grid stability map"
consumers: []
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

# Numerical Simulation Debugging: Theory-First Root-Cause Methodology

Lessons compiled from a two-stage investigation of ch13 capillary wave failures:
Stage 1 (CHK-133): DGR blowup (KE > 1e6) → hybrid fix.
Stage 2 (CHK-135): hybrid gives wrong 2D physics → root cause analysis and fix.
The two-stage structure exemplifies how "fixing the crash" ≠ "fixing the physics".

---

## 1. Distinguish Failure Modes Before Debugging

Two fundamentally different failure classes require different debugging strategies:

| Class | Symptom | Debugging approach |
|---|---|---|
| **Hard failure** | Blowup, NaN, KE > 1e6 | Find the WHEN (step number); instrument the amplifier |
| **Silent failure** | Wrong D(t), wrong VolCons, wrong shape | Compare to analytical solution; check all physical invariants |

**Lesson:** After fixing a hard failure, always verify the physics is correct — not just that the simulation "completes". The ch13 hybrid fix prevented hard blowup but produced D(t) saturating at 0.226 (should decay to ~0); this was only discovered by comparing to the Prosperetti (1981) analytical solution.

Checklist of physical invariants to verify after any code change:
1. Volume conservation: `|VolCons_final - 1| < 5%`
2. Energy dissipation: `KE_final << KE_max`
3. Mode comparison: `D(t)` vs analytical `D₀ e^{-βt} cos(ω₀t)`
4. 2D snapshot: interface shape qualitatively correct (not inflated/deformed)

---

## 2. Establish a Working Baseline First

Before debugging, identify a configuration that gives correct results:
```
split-only, α=1.0, uniform grid → D_final=0.0036 ✓  (correct baseline)
```
Every diagnostic experiment is then a comparison to this baseline. Without a baseline:
- You cannot distinguish "broken by my change" from "was always broken"
- You cannot quantify improvement/regression

**Pattern:** Create a minimal reference config that:
1. Uses the simplest possible setup (uniform grid, single method)
2. Has a known analytical solution to compare against
3. Runs quickly (short T_final or coarse grid)

---

## 3. Theory-First: Derive Invariants Before Running Experiments

Before changing code or running experiments, derive what the code MUST preserve:

**Example from DGR investigation:**

*Wrong approach:* "DGR gives wrong D(t), let me try changing the scale parameter."

*Correct approach:*
1. Derive: κ(c·φ) = κ(φ) for uniform scale c → DGR scale does NOT change curvature
2. Derive: ∫δ_ε(c·φ)|∇(c·φ)|dA = const → DGR scale does NOT change net CSF force
3. Identify the remaining degree of freedom: mass correction via w=4q(1-q)
4. Derive: mass correction shift is ∝ 1/|∇psi| at interface → non-uniform for curved interfaces
5. Conclude: the mass correction IS the energy injection mechanism

This theoretical analysis ruled out two mechanisms in 5 minutes of algebra, avoiding 2 unnecessary experiments. Only then run experiments to confirm the third mechanism.

**Invariant checklist for level-set reinitialization:**
- Interface position preserved: zero-crossing of φ unchanged
- Volume conservation: ∫psi dV = const (before mass correction)
- Curvature preserved: κ_before = κ_after (for thickness-only correction)
- Mass correction: non-uniform shift for curved interfaces → shape error

---

## 4. Isolation Experiments: One Variable at a Time

Each experiment changes exactly ONE variable from a known-good configuration.

**Template:**

| Exp | Base config | Change | Expected if hypothesis H correct | Expected if H wrong |
|---|---|---|---|---|
| A1 | hybrid baseline | reinit_every=0 | blowup | stable |
| A2 | hybrid baseline | σ=0 | stable | blowup |
| A3 | hybrid baseline | reinit_every=500 | worse blowup | stable |
| G1 | α=1.2 hybrid | grid_rebuild_freq=10 | VolCons < 5% | VolCons >> 5% |

Each exp CONFIRMS or REFUTES exactly one hypothesis. Four exps → complete mechanism.

**Rule:** If you cannot predict the expected outcome for BOTH "hypothesis correct" and "hypothesis wrong" before running the experiment, the experiment is not well-designed.

---

## 5. Instrumented Diagnostics for Hard Failures

For blowup (step number known), add per-step scalar printouts to find the ONSET:

```python
# In DGRReinitializer.reinitialize():
if step_count % 20 == 0:
    print(f"[DGR#{step_count:04d}] eps_eff={eps_eff:.5f} scale={scale:.4f} "
          f"band_n={int(xp.sum(band))}  |∇ψ|_band: min={grad_min:.3f} max={grad_max:.2f}")
```

Print only SCALARS (not arrays) — this gives:
- WHEN the fold forms (|∇ψ|_min → 0)
- WHAT the amplifier does (scale stays ≈ 1 → DGR is no-op)
- HOW FAST blowup occurs (KE jump magnitude)

From Set B instrumented run: `|∇ψ|_band min = 0.0000 at step=62 [DGR#31]` → fold onset confirmed.

Binary-search approach for finding onset step:
1. Print every N steps; find the interval [t_last_ok, t_first_bad]
2. Halve N; repeat until N=1
3. Total experiments: O(log(N_total_steps)) instead of O(N_total_steps)

---

## 6. Frequency Sensitivity: Discriminating Experiments

For any periodic process (reinit, grid rebuild), test the extreme cases first:
- Disabled (every=0): "Is this process needed at all?"
- Very infrequent (every=500): "What happens without it for many steps?"
- Very frequent (every=1): "What is the minimum pathology per call?"

The answers immediately bracket the problem:
- If disabled → blowup: process IS needed; blowup rate tells you how fast the problem develops
- If very infrequent → blowup at t < T_period: first call must happen before this onset time
- If very frequent → correct: any frequency between is candidates

From ch13 Set D: D4 (every-500) blew up at step=76 (< first reinit at step=500). This immediately ruled out the "reduce frequency" hypothesis — the interface folds at step ~62 regardless of frequency, so reinit MUST happen before step ~62.

---

## 7. Short Cycle: Analyze Between Experiments

Do not batch all experiments; analyze after each pair:

```
Hypothesis → Experiment → Analyze → Refine hypothesis → Next experiment
```

From ch13 investigation:
1. Run D4 (every-500): BLOWUP at step=76 → rules out frequency hypothesis A1
2. Analysis: fold develops at step ~62; any frequency > every-62 would prevent blowup
3. Revised hypothesis: the problem is in each DGR CALL, not the frequency
4. Next: G1 (grid_rebuild_freq=10) tests whether the non-uniform grid is misapplied

Batching all experiments upfront wastes time running experiments that later analysis would have skipped.

---

## 8. Negative Results Are Findings — Document Them

Document what DIDN'T work and why:

| Null fix | What was tested | Why it failed | Knowledge gain |
|---|---|---|---|
| Set C (CHK-133) | Pointwise |∇φ| normalization | g_min floor creates bulk amplification → CCD Laplacian contamination | Do NOT use pointwise normalization for logit-inverted fields |
| Set D4 (CHK-135) | Reduce reinit frequency (every-500) | Fold develops before first reinit → identical to no-reinit | Reinit must happen at least every ~60 steps for capillary waves at CFL=0.10 |

Negative results prevent future repeated exploration of dead ends. Without them, a future investigator would try the same null fixes.

**Pattern for documenting null results:**
1. State the hypothesis being tested
2. State the expected outcome if hypothesis was correct
3. State the actual outcome
4. Derive WHY it fails (not just THAT it fails)
5. State what this rules out for future investigators

---

## 9. Update Theory Documentation Before Implementing the Fix

"Write what you know before you change the code."

For CHK-133: WIKI-T-030 §Limitations was written (fold cascade mechanism documented) before the hybrid fix was confirmed to be correct. This prevents the theory from being left in an incorrect state after a partial fix.

For CHK-135: theory section in this wiki was written before the correction experiments completed. This allows parallel work: theory documentation and experiments run simultaneously.

**Template:**
1. Write the theory doc (WIKI-T or WIKI-X) first, explaining the failure mechanism
2. Mark as "PROVISIONAL" with a note: "Hypothesis — experimental confirmation pending"
3. Run the discriminating experiment
4. Update the wiki to remove "PROVISIONAL" when confirmed

---

## 10. Two-Stage Fix Pattern

Complex failures often require two-stage investigation:

**Stage 1: Stop the hard failure** (blowup, NaN)
→ Find the amplifier (CSF force over folded interface)
→ Fix the amplifier (hybrid reinit)
→ Verify: no blowup at T_final ✓

**Stage 2: Verify the physics** (compare to analytical solution)
→ Find the soft failure (wrong D(t), wrong VolCons)
→ Root cause: different mechanism from Stage 1 (DGR mass correction curvature bias)
→ Fix the soft failure
→ Verify: D(t) matches Prosperetti ✓, VolCons < 5% ✓

Without Stage 2, the simulation "works" (no crash) but produces wrong results. The distinction:
- Stage 1 failure: simulation cannot complete
- Stage 2 failure: simulation completes with wrong physics

Both must be fixed for a correct result.

---

## Summary: Debugging Decision Tree

```
Simulation fails
    ├── Hard failure (blowup, NaN, crash)
    │   ├── Find WHEN: binary-search step number
    │   ├── Find WHAT: instrument the amplifier
    │   ├── Theory: derive which invariant breaks
    │   ├── Isolation: one-variable-at-a-time
    │   └── Fix → re-run → check Stage 2 (physics correctness)
    │
    └── Soft failure (wrong output)
        ├── Compare to analytical solution
        ├── Theory-first: derive invariants; rule out mechanisms algebraically
        ├── Isolation: discriminating experiments (extreme cases first)
        ├── Document negative results
        └── Fix → verify all physical invariants
```

For both failure types: commit and document at each milestone, not just at the end.
```
Commit-1: diagnostic configs
Commit-2: experiment results + analysis
Commit-3: theory update (wiki)
Commit-4: code fix
Commit-5: verification results + merge
```
