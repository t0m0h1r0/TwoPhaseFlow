# CHK-RA-CODE-GPU-008 — ch14 capillary paper refresh from rerun

Date: 2026-05-16
Branch: `codex/ra-code-paper-gpu-review-20260516`
Worktree: `.claude/worktrees/codex-ra-code-paper-gpu-review-20260516`

## Request

User requested that the latest one-period capillary-wave experiment result also
be reflected in the paper.

## Source Result

Source artifact/result:

- `artifacts/A/ch14_capillary_regression_check_CHK-RA-CODE-GPU-007.md`
- `experiment/ch14/results/ch14_capillary/data.npz`
- `experiment/ch14/results/ch14_capillary/*.pdf`

The source experiment was the remote-first rerun:

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary --no-checkpoint-final"
```

Result: PASS.

## Metrics Reflected

| Metric | Value |
|---|---:|
| samples | `2585` |
| final time | `0.046742983863` |
| initial signed amplitude | `2.002821033748e-04` |
| quarter-period signed amplitude | `1.574613338802e-05` |
| half-period signed amplitude | `-1.833865831437e-04` |
| three-quarter signed amplitude | `-4.067365721147e-05` |
| final signed amplitude | `1.590460892479e-04` |
| final amplitude ratio | `0.794110340205` |
| max kinetic energy | `8.292391914738e-06` |
| final kinetic energy | `1.143411766571e-06` |
| final volume drift | `1.477225460012e-14` |
| max volume drift | `5.719166459861e-14` |
| final `dy_min` | `3.919802248741e-04` |

Phase samples used in Table `tab:ch14_capillary_phase_samples`:

| Phase | t [s] | signed amplitude | ratio | kinetic energy |
|---|---:|---:|---:|---:|
| `0` | `1.843598857897e-05` | `2.002821033748e-04` | `1.000000000000e+00` | `4.698388716451e-11` |
| `1/4` | `1.169170430384e-02` | `1.574613338802e-05` | `7.861977242447e-02` | `8.044166068568e-06` |
| `1/2` | `2.336764788197e-02` | `-1.833865831437e-04` | `-9.156413880900e-01` | `8.180088875338e-07` |
| `3/4` | `3.505476398473e-02` | `-4.067365721147e-05` | `-2.030818357013e-01` | `6.942475885615e-06` |
| `T` | `4.674298386300e-02` | `1.590460892479e-04` | `7.941103402050e-01` | `1.143411766571e-06` |

## Paper Updates

Updated textual/table values in:

- `paper/sections/14_benchmarks.tex`
- `paper/sections/13e2_ao_capillary_split_gate.tex`

Synced the paper's Ch14 capillary figure PDFs from the latest result directory:

- histories: signed interface amplitude, kinetic energy, volume drift
- snapshots: five `psi`, five velocity, and five pressure phase snapshots

## Validation

`git diff --check`: PASS.

Stale-value scan over the edited sections: PASS, no previous CHK-RA-CODE-GPU-004
values remain in the targeted Ch14/V11 text.

```bash
rg -n "1\.587038|1\.563467|8\.3385|1\.1483|9\.6223|9\.9611|8\.34\\times10\^-6|0\.792" \
  paper/sections/14_benchmarks.tex paper/sections/13e2_ao_capillary_split_gate.tex
```

`make -C paper`: PASS.

Output:

- `paper/main.pdf`
- 276 pages

`paper/main.log` diagnostic scan: PASS.  No LaTeX/package warnings, overfull or
underfull boxes, undefined refs/citations, missing glyphs, emergency stops,
fatal errors, or undefined control sequences were found.

## Scope

[SOLID-X] Paper text, paper figures, artifact, and ledger only.  No
`src/twophase/`, experiment YAML, physical parameter, CFL, damping, smoothing,
tolerance, production algorithm, hidden fallback, main merge, branch deletion,
or worktree removal was changed.
