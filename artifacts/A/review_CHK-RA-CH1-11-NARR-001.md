# Review CHK-RA-CH1-11-NARR-001

Session: `CHK-RA-CH1-11-NARR-001`
Agent: ResearchArchitect
Branch: `ra-ch1-11-narrative-review-20260503`
Base: `main` at `42150984`
Scope: `paper/sections/01*.tex`--`paper/sections/11*.tex`

## Verdict

PASS AFTER FIX. A strict Chapter 1--11 rereview found no need to reorder the
main exposition, but it did find reviewer-visible contract drift left by older
algorithm generations. The paper now carries one consistent story: CLS uses
the global $\psi=H_\varepsilon(-\phi)$ sign convention, Ridge--Eikonal returns
to the FCCD conservative CLS path, the adopted NS time integration is
EXT2--AB2/IMEX--BDF2 + IPC with implicit-BDF2/DC viscosity, and Chapter 11's
verification links match the current U/V numbering.

## Findings And Fixes

### RA-CH1-11-NARR-001-01: CLS sign convention split across Chapters 3 and 5

Finding: Chapters 3 and 5 define the global liquid indicator as
$\psi=H_\varepsilon(-\phi)$, but the Stage A--F summary and Ridge--Eikonal
handoff still used the opposite tanh/artanh pair and regenerated
$H_{\varepsilon_\text{local}}(\phi)$. The Stage F mass correction also shifted
$\phi$ in the wrong sign convention. This was not a cosmetic issue: it made the
reader unable to determine which side of the interface is liquid.

Fix: Updated the tanh/artanh pair, Ridge--Eikonal handoff, and Stage F Newton
shift to consistently use $H_\varepsilon(-\phi)$ and to move $\phi$ in the
mass-increasing direction implied by that convention.

### RA-CH1-11-NARR-001-02: Adopted time-integration story still had CN-era scars

Finding: The Chapter 1 roadmap, Chapter 4 operator handoff, Chapter 6 variable
scheme policy, Chapter 6 viscous layer text, and Chapter 11 step table mixed
old CN/AB2 wording with the current Chapter 7 and Chapter 12 contracts. A
reviewer would see both "CN viscosity" and "implicit-BDF2 + DC" presented as
the adopted path.

Fix: Reframed the adopted path as TVD--RK3 for CLS, EXT2--AB2/IMEX--BDF2 + IPC
for NS coupling, and implicit-BDF2 + DC for viscosity. The UCCD6
Crank--Nicolson stability theorem remains only as a periodic-grid property, not
as the production time integrator.

### RA-CH1-11-NARR-001-03: Verification bridge references lagged Chapter 12--14

Finding: Chapter 11 still referred to HFE as `U6-c` after the Chapter 12
renumbering to `U6-b`, and Chapter 1 still described Chapter 14 benchmarks as
future "results to be added". Both made the front half look older than the
verified back half.

Fix: Updated the pure-FCCD DNS verification bridge to `U6-b` and aligned the
Chapter 1 roadmap with the current Chapter 14 YAML set: capillary wave, rising
bubble, and Rayleigh--Taylor smoke, with longer quantitative extensions left to
future work.

### RA-CH1-11-NARR-001-04: Velocity and normal notation were not visually stable

Finding: Chapters 1--11 mixed `\bm{u}` with the project macro `\bu`, and mixed
`\hat{\bm{n}}` with `\hat{\bm n}`. The meaning was usually recoverable, but
the inconsistency undercut the requested reviewer-grade notation discipline.

Fix: Normalized continuous velocity and normal notation across Chapters 1--11
to `\bu` and `\hat{\bm n}`. Discrete algebra vectors such as `\mathbf{u}` in
matrix definitions were left intact.

## Validation

- `git diff --check` PASS.
- Targeted stale-contract scan PASS: no `U6-c`, `CN 半陰的`, `AB2+IPC`,
  `仮想時間ステッピング`, `TVD-RK3 + DCCD`, positive-sign local Heaviside
  regeneration, `\bm{u}`, or `\hat{\bm{n}}` remains in Chapter 1--11 targets.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS in
  `paper/`; output `main.pdf`, 243 pages.
- Remaining log notes observed: pre-existing underfull hbox in
  `sections/09f_pressure_summary.tex:57` and a float-only page warning around
  Chapter 12. Neither was introduced by this Chapter 1--11 pass.

## SOLID-X

Paper/audit-only change. No production code boundary changed, no tested code
deleted, no FD/WENO/PPE fallback introduced, and no experiment data or figures
were modified.
