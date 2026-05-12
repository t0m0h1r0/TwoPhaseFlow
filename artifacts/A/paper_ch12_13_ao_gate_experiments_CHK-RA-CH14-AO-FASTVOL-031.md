# CHK-RA-CH14-AO-FASTVOL-031 - Ch12--13 AO gate experiments

## Purpose

User requests:

> 12-13章で行うべき追加実験を実施し、論文へ反映してください。

> 陳腐化した実験は削除して構いません

The Chapter 12--13 support experiments must match the corrected AO-Fast
capillary theory.  The relevant pre-benchmark question is not whether the
current AO-Fast packet is a successful production capillary solver; it is
whether the paper now exposes the algebraic gate that prevents an unresolved
pressure-reaction split from entering Chapter 14 results.

## Experiment changes

Added:

```text
experiment/ch12/exp_U12_ao_capillary_split_gate.py
experiment/ch13/exp_V11_ao_capillary_split_gate.py
```

Removed as stale:

```text
experiment/ch13/exp_V11_common_flux_admissibility.py
paper/figures/ch13_v11_common_flux_admissibility.pdf
```

The old V11 common-flux admissibility script belonged to the earlier
common-flux transport audit.  It no longer answers the current AO-Fast
capillary pressure-reaction question and would make the paper appear to have a
successful integration gate where the current theory requires fail-close.

## Remote commands

```text
make cycle EXP=experiment/ch12/exp_U12_ao_capillary_split_gate.py ARGS='--require-gpu'
make cycle EXP=experiment/ch13/exp_V11_ao_capillary_split_gate.py ARGS='--require-gpu'
```

Both runs executed on the remote GPU host and pulled their result directories
back into the worktree.

## Results

U12:

| case | CPU exact balanced drive | component probe balanced drive | GPU gate |
|---|---:|---:|---|
| flat N32 | `0.000000e+00` | `0.000000e+00` | `ok`, no fail-close |
| wave N32 | `0.000000e+00` | `2.117576e+00` | `ok`, fail-close |
| wave N64 | `0.000000e+00` | `2.305484e+00` | `ok`, fail-close |

V11:

| case | component probe balanced drive | GPU gate |
|---|---:|---|
| flat N32 pressure-coordinate | `0.000000e+00` | `ok`, no fail-close |
| wave N32 pressure-coordinate | `2.117576e+00` | `ok`, fail-close |
| wave N32 face-acceleration | `2.117576e+00` | `ok`, fail-close |
| wave N64 pressure-coordinate | `2.305484e+00` | `ok`, fail-close |

Interpretation:

- The flat interface remains an exact zero-drive control.
- The full pressure-image CPU exact split cancels the capillary-wave balanced
  drive exactly, so it is a counterexample rather than a physical success
  certificate.
- The component-volume Hodge probe detects the non-static wave residual and is
  retained only as a diagnostic probe, not as the final pressure-reaction
  subspace.
- The current GPU AO-Fast packet correctly fail-closes on non-static waves
  instead of falling back to an implicit PCG/DC/CPU path.

## Paper changes

Updated:

```text
paper/sections/12u12_ao_capillary_split_gate.tex
paper/sections/13e2_ao_capillary_split_gate.tex
paper/figures/ch12_u12_ao_capillary_split_gate.pdf
paper/figures/ch13_v11_ao_capillary_split_gate.pdf
```

The Chapter 12 U12 text now records the executable remote GPU gate and its
figure.  The Chapter 13 V11 text now promotes the same result into an
integration-before-production gate and removes the stale common-flux reading.

## Validation

```text
python -m py_compile experiment/ch12/exp_U12_ao_capillary_split_gate.py \
    experiment/ch13/exp_V11_ao_capillary_split_gate.py \
    experiment/ch14/diagnose_ao_algebraic_split.py
python experiment/ch12/exp_U12_ao_capillary_split_gate.py --plot-only --require-gpu
python experiment/ch13/exp_V11_ao_capillary_split_gate.py --plot-only --require-gpu
git diff --check
make -B -C paper
```

[SOLID-X] Experiment scripts, paper-facing figures, paper prose, artifact, and
ledger only; no production solver source, YAML physical parameter, CFL
reduction, damping, smoothing, curvature cap, FD/WENO/PPE fallback, hidden
PCG/DC fallback, main merge, or AO-Fast workaround was introduced.
