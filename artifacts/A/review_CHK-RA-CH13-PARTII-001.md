# CHK-RA-CH13-PARTII-001 — Chapter 13 Part II integration audit

Date: 2026-05-07

Scope: audit Chapter 13 against Part II (§4--§11), rerun the static-droplet related verification set, and move static-droplet material out of Chapter 14 into Chapter 13.

User policy:
- Work in a separate worktree.
- Commit at sensible checkpoints.
- Do not merge to main without explicit instruction.
- If main merge is later requested, use no-ff and keep working in the same worktree afterward.
- Put Chapter 13 material in Chapter 13; Chapter 12 remains unit/component tests.
- Chapter 14 will not run or host static-droplet experiments.

## Experiments refreshed

Remote-first execution used `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle ...`.

| Experiment | Result |
|---|---|
| V3 `experiment/ch13/exp_V3_static_droplet_longterm.py` | PASS. `N=64/96/128` pressure relative errors `1.23%/1.15%/0.97%`; peak speeds `1.686e-03/7.043e-03/6.271e-03`. |
| V4 `experiment/ch13/exp_V4_galilean.py` | PASS. `diff_final=2.068e-01`, `diff_max=2.632e-01`. |
| V5 `experiment/ch13/exp_V5_spurious_current_multistep.py` | PASS. CCD stays below matching FD in the table; worst CCD final speed `1.93e-02`. |
| V6 `experiment/ch13/exp_V6_density_ratio_convergence.py` | PASS. All 8 cases stable; max final speed `3.290e-10`, max volume drift `2.365e-16`, pressure-correction diagnostic `0.737--1.003`. |
| V8 `experiment/ch13/exp_V8_nonuniform_ns_static.py` | PASS. Final pressure errors and speed values match the paper-scale claims; `N=96, alpha=2` pressure error remains `2.86%`. |
| V9 `experiment/ch13/exp_V9_local_eps_nonuniform.py` | PASS. B/C identical at `N=32`; max speed `4.269e-10`; max volume drift refreshed to `3.81e-16`. |

Follow-up graph sync: after the text/table patch, `make cycle EXP=experiment/ch13/exp_V6_density_ratio_convergence.py ARGS=--plot-only` and `make cycle EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py ARGS=--plot-only` were run on the remote environment. The regenerated result PDFs were copied into `paper/figures/ch13_v6_density_ratio*.pdf` and `paper/figures/ch13_v9_*.pdf` so the checked-in paper figures match the refreshed V6/V9 values.

Production static-droplet data formerly associated with the Chapter 14 static route was incorporated into Chapter 13 as a V3 production-stack static gate:

| Run | Final KE | Max KE | Max volume drift | Deformation | Final speed Linf |
|---|---:|---:|---:|---:|---:|
| `N=32,T=1` | `2.353e-07` | `2.625e-07` | `1.396e-15` | `0` | `1.575e-04` |
| `N=32,T=10` | `3.871e-07` | `1.718e-06` | `2.919e-15` | `0` | `1.686e-04` |

These runs support bounded static behavior, not an exact roundoff-static theorem: a sampled analytic circle is not automatically a constrained critical point of the discrete surface functional.

## Round 1 findings

F1. Chapter 13 still described an old `range projection face-balance` short gate as if it proved roundoff static equilibrium.

Resolution: replaced it with a production-stack static gate in §13b, explicitly stating that Chapter 14 does not duplicate static droplets and that the acceptance target is geometry/volume preservation plus bounded kinetic leakage.

F2. V6/V9 numerical values were stale after reruns.

Resolution: updated V6 max speed/volume drift (`3.3e-10`, `2.4e-16`) and V9 max volume drift (`3.81e-16`) across §13d, §13e, §13f, and §15.

F3. Chapter 14 placement was ambiguous because a static-droplet YAML lineage existed there.

Resolution: §14 now states that static circular droplets, including the production-stack static gate, belong to §13; §14 keeps only finite-interface-motion physical benchmarks.

## Round 2 check

No remaining Chapter 13/14 placement issue found under the clarified scope. Chapter 12 remains a unit/component-test chapter, Chapter 13 carries integration and static-droplet gates, and Chapter 14 carries moving-interface benchmarks only.

[SOLID-X] Paper/artifact/bookkeeping only in this checkpoint; no solver source or checked-in experiment configuration behavior changed, no tested implementation deleted, and no FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing, benchmark-name branch, blanket projection, or QP-as-physics path was introduced.
