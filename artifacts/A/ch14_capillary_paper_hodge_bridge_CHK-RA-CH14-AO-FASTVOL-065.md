# CHK-RA-CH14-AO-FASTVOL-065 - Paper update for AO face Hodge bridge

## Question

User asked to update the paper after the Chapter 14 capillary-wave visual
breakage RCA and the AO face-bridge unit fix.

## Paper Changes

- `paper/sections/11e_ao_fast_state_space.tex`
  - Added the q-owned graph-gauge ordering equation:
    `q^- -> phi_G^- = G_col(q^-) -> Q_h^{S(phi_G^-)}(phi^+) = q^-`.
  - Added the face-Hodge contract:
    `a_{\sigma,G}=M_G^{-1} r_{\sigma,bal}` and
    `f_P^* <- f_P^* + I_{G->P} dt a_{\sigma,G}`.
  - Clarified that the geometric-to-projection bridge interpolates
    already-Hodge-divided acceleration/increment samples and must not divide by
    physical face length a second time.
  - Updated the standard-route admission boundary from six to seven conditions.
- `paper/sections/07_time_integration.tex`
  - Connected the time-integration capillary closure to the one-time face Hodge
    application and same-dimension projection-face interpolation.
- `paper/sections/12*`, `paper/sections/13*`, `paper/sections/14_benchmarks.tex`,
  `paper/sections/15_conclusion.tex`, and the Figure 2 note in
  `paper/sections/01b_classification_roadmap.tex`
  - Propagated the new Hodge-divided face-bridge condition through U12, V11,
    the benchmark stack, error-budget summary, and conclusion.

## Validation

```text
git diff --check
make -C paper
rg -n "LaTeX Error|Undefined control sequence|undefined references|Reference .* undefined|Label\\(s\\) may have changed|Overfull|Underfull|Missing character" paper/main.log
```

Results:

- `git diff --check` passed.
- `make -C paper` passed and regenerated `paper/main.pdf` as a 274-page PDF.
- The targeted log scan found no LaTeX errors, unresolved references,
  over/underfull boxes, or missing glyph warnings.

## SOLID/A3

- [SOLID-X] Paper/docs/artifact update only; no solver source, experiment YAML,
  result data, physical parameter, CFL, damping, smoothing, tolerance, fallback,
  main merge, branch deletion, or worktree removal changed.
