# CHK-RA-CH14-AO-FASTVOL-034 — AO Short-Paper Reflection In Paper

## User Request

AO のショートペーパーに記載されている内容を基本的に論文へ反映しつつ，
Part I の第2章は理論章なので，数値誤差抑制・高速化・GPU 契約の記述を
第2章へ置かないよう整理する。

## Paper Changes

- Added `paper/sections/11e_ao_fast_state_space.tex` and included it from
  `paper/main.tex` after the existing Chapter 11 algorithm material.
- Kept Chapter 2 focused on the continuous/theoretical boundary:
  surface-energy virtual work, pressure-reaction subspace, and the
  full-pressure-image cancellation theorem.
- Moved the AO-Fast approximation/error-budget equations
  `eq:ao_fast_error_budget` and `eq:ao_fast_acceleration_error_bound`
  into the new Chapter 11 AO-Fast algorithm section.
- Reflected the SP-AO state-space contract in the paper:
  `q_C=|C| theta_C` ownership, `Q_h(phi)=q` compatibility,
  active support `A_q`, projection Schur system, projection-work ledger,
  pressure-reaction split, active/dirty complexity model, fixed-stratum
  approximation accuracy, PCG/DC policy, GPU no-inner-D2H contract, and
  YAML/fail-close UX boundary.
- Updated roadmap, Chapter 12 mapping, and conclusion so U12/V11 point to the
  dedicated AO-Fast state-space section rather than relying on Chapter 2.
- Fixed one pre-existing paper-domain scan issue by wrapping the appendix
  title math `omega` with `\texorpdfstring`.

## Validation

- `git diff --check`: PASS
- Section/subsection/caption math scan:
  `grep -nE "\\(section|subsection|caption)" paper/sections/*.tex | grep -F "$" | grep -v "texorpdfstring"`: PASS (no matches)
- `make -B -C paper`: PASS, `main.pdf` rebuilt
- `rg -n "Undefined references|LaTeX Warning: Reference|Overfull|Fatal error|Emergency stop|LaTeX Error" paper/main.log`: PASS (no matches)

## Boundary

[SOLID-X] Paper, appendix title hygiene, artifact, and ledger only.  No solver
source, production YAML, physical parameter, experiment result, CFL reduction,
damping, smoothing, curvature cap, FD/WENO/PPE fallback, hidden PCG/DC
fallback, AO-Fast production admission, main merge, branch deletion, or
worktree removal introduced.
