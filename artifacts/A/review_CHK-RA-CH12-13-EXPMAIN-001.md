# CHK-RA-CH12-13-EXPMAIN-001 - Chapter 12--13 experiment audit on latest main

Date: 2026-05-09

Base: latest `origin/main` = `69d87435` (`merge: RA ch14 common flux rising bubble`).

Parallel work explicitly ignored: `codex/ra-paper-review-ch1-11-20260509`.

## Verdict

Additional/update/rerun work is required.

The reason is not the parallel Chapter 1--11 review.  On latest main, Chapter
1--11 and `src/twophase/` now contain the conservative common-flux route:
`q`, mass, and momentum share one transport ledger; q-only reinitialization and
dynamic remap are fail-close until conservative `(q,m,p)` remap exists; restart
closure stores pre-step conservative state.

Chapter 12--13 currently verify the older decomposition:

- Chapter 12 U1--U9: unit/component primitives, all CPU-oriented.
- Chapter 13 V1--V10: single-phase, reduced BF, pressure-jump/HFE/DC, local
  epsilon, and CLS advection gates.
- V6/V7/V9 use `uccd6` momentum convection through `experiment/ch13/ch14_stack_common.py`.
- No `experiment/ch12` or `experiment/ch13` script selects
  `momentum_form: conservative_common_flux`.

Therefore the existing V1--V10 results are not invalidated wholesale, but they
do not constitute Chapter 12--13 evidence for the newly merged common-flux
algorithmic contract.

## Evidence Checked

1. `git diff 69d87435^1..69d87435` changes shared solver/runner paths used by
   experiments, including `src/twophase/levelset/fccd_advection.py`,
   `src/twophase/simulation/conservative_transport.py`,
   `src/twophase/simulation/ns_pipeline.py`, `runner.py`, config models, and
   checkpoint support.
2. `paper/sections/01*`--`11*` on latest main now teach common-flux transport,
   q-only reinit fail-close, same pressure/transport divergence complex, and
   conservative restart closure.
3. `paper/sections/12*.tex` and `paper/sections/13*.tex` contain no
   common-flux U/V experiment.  The bridge table still routes face/CLS effects
   to V1/V2/V6/V7/V10, but not to a `(q,m,p)` common-flux gate.
4. `experiment/ch13/ch14_stack_common.py` asserts the current V6/V7/V9 stack as
   `interface transport = fccd_flux`, `momentum convection = uccd6`, and
   `reinitialization = ridge_eikonal`; it is not the conservative route.
5. Source tests protect the new route (`test_common_flux_transport.py`,
   `test_ns_pipeline_fccd.py`, `test_simulation_checkpoint.py`), but source
   tests are not Chapter 12--13 experiment evidence.
6. Existing ch14 artifacts already contain useful theorem and gate data, but
   they are Chapter 14/rising-bubble artifacts and should not silently stand in
   for Chapter 12--13 verification.

## Required Work

### R1 - Latest-main regression reruns for affected existing V tests

Rerun only the V tests whose executed path touches the changed shared
transport/solver stack or whose paper claims are directly adjacent to the new
common-flux contract:

| ID | Command | Reason |
|---|---|---|
| V3 | `make cycle EXP=experiment/ch13/exp_V3_static_droplet_longterm.py` | Refresh the pressure-jump/Riesz static auxiliary gate after common-flux/static criticality changes. |
| V6 | `make cycle EXP=experiment/ch13/exp_V6_density_ratio_convergence.py` | Uses ch13/ch14 stack common code and shared pressure-jump solver path. |
| V7 | `make cycle EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py` | Uses the coupled pressure-jump stack and reinit cadence; rerun after solver/transport edits. |
| V9 | `make cycle EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py` | Uses ch13/ch14 stack common code plus local-epsilon/nonuniform pressure-jump path. |
| V10 | `make cycle EXP=experiment/ch13/exp_V10_cls_advection_nonuniform.py` | Uses `FCCDLevelSetAdvection`, which now carries the common-flux ledger path. |

Do not rerun V1/V2/V4/V5/V8 unless the above reruns reveal a shared regression.
Their primary kernels and evidence contracts are not the newly changed
common-flux path.

### R2 - Add a Chapter 12 common-flux component experiment

Add a new U-series component gate, tentatively `U10`, by promoting the useful
parts of `artifacts/A/ch14_common_flux_gate.py` into
`experiment/ch12/exp_U10_common_flux_ledger.py` using `twophase.experiment`.

Acceptance metrics:

- common phase/mass/momentum flux keeps mass and momentum conservative;
- kinetic energy is non-increasing for closed common-flux candidates up to
  tolerance;
- mismatched density/velocity/momentum candidates are recorded as negative
  controls, not alternate routes;
- density remains the affine image of phase;
- endpoint clipping/q-only projection is rejected unless accompanied by a
  certified `(q,m,p)` remap.

Paper updates:

- add `paper/sections/12u10_common_flux_ledger.tex`;
- update `12_component_verification.tex`, `12h_summary.tex`, and the U-to-V
  bridge from U1--U9 to U1--U10.

### R3 - Add a Chapter 13 common-flux integration gate

Add a small V-series gate, tentatively `V11`, for conservative common-flux
admissibility.  This should be a verification gate, not a physical benchmark
that duplicates Chapter 14.

Recommended file:

```text
experiment/ch13/exp_V11_common_flux_admissibility.py
```

Required subchecks:

- build the latest `conservative_common_flux` runtime from the canonical ch14
  rising-bubble YAML with a reduced grid override, verifying reinit/grid rebuild
  are disabled and conservative state fields are present;
- run a short transport/projection gate on remote GPU, not beyond the already
  validated small-time window;
- verify affine density error, mass/momentum ledger consistency, kinetic-energy
  certificate, checkpoint roundtrip of conservative state, and absence of
  q-only reinit/remap;
- include a negative fail-close check: enabling q-only reinit or dynamic grid
  remap in conservative mode must be rejected or explicitly marked uncertified.

Paper updates:

- add V11 to `13_verification.tex` and `13f_error_budget.tex`;
- state that V1--V10 remain the velocity-primary / pressure-jump / CLS evidence
  set, while V11 is the conservative-common-flux admissibility gate;
- keep full rising-bubble physics in Chapter 14.

### R4 - Sync paper figures and validation

For any rerun that changes numerical values or PDFs:

```text
git diff --check
make -B -C paper
rg -n "^(LaTeX Warning|Package .*Warning|Class .*Warning|Overfull|Underfull|! |.*Error|Fatal|Undefined control sequence|LaTeX Error)" paper/main.log
```

For code/script additions:

```text
make test
```

Remote-first execution remains mandatory.  Use local fallback only if remote is
unavailable.

## Work Not Required

- No blanket rerun of all Chapter 12 U1--U9 is justified by the latest-main
  diff.  Those tests cover stable primitives whose implementation files were
  not the common-flux merge target.
- No retrofit of V6/V7/V9 into `conservative_common_flux` is allowed until the
  conservative reinit/remap certificate exists.  Those runs currently rely on
  q-only Ridge--Eikonal reinitialization, which the common-flux theory marks as
  fail-close in conservative mode.
- No Chapter 13 moving-interface physical benchmark should replace Chapter 14.
  Chapter 13 should add theorem/admissibility evidence; Chapter 14 keeps the
  rising-bubble/capillary/oscillating-droplet physical benchmark narrative.

## SOLID-X

Audit/plan artifact only.  No solver source, experiment config/result, paper
prose, tested implementation, FD/WENO/PPE fallback, damping/CFL workaround,
smoothing, curvature cap, benchmark branch, blanket projection, or
QP-as-physics path changed in this checkpoint.
