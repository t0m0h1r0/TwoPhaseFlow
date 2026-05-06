# CHK-RA-CAPILLARY-RANGE-PAPER-001 — capillary range projection theory in paper

## Scope

User request: document the newly derived theory and formulation rigorously in the paper.

This is a paper-only synchronization of the recent static-droplet KE root-cause work,
Ridge--Eikonal/interface-transport separation, and the production capillary
range-projected pressure-jump closure.

## Paper updates

- `paper/sections/05_reinitialization.tex`
  - Added the interface-transport/Ridge--Eikonal projection split.
  - Defines physical CLS transport as the only physical-time interface update.
  - Defines Ridge--Eikonal as a constrained geometry projection with volume,
    zero-level displacement, and surface-energy proxy gates.
  - Explicitly rejects adding Eikonal pseudo-time RHS terms to the physical
    interface transport equation.

- `paper/sections/09b_split_ppe.tex`
  - Added the core formulation:
    `c_f=A_f B_f(j_gl)`, `a_f=A_f G_f p-c_f`,
    `R_h=range(A_f G_f)`, Hodge split
    `c_f=Pi_R c_f+h_f`, and the auxiliary solve
    `D_f A_f G_f pi_h=D_f c_f`.
  - Shows why PPE residual/divergence can be small while a divergence-free
    non-gradient capillary cochain still injects kinetic energy.
  - Defines the production correction
    `a_f^range=A_f G_f p-Pi_R c_f` and diagnostics
    `eta_H`, `eta_a`.
  - States explicitly that this is not damping, CFL reduction, curvature capping,
    smoothing, or a low-order fallback.

- `paper/sections/11_full_algorithm.tex`
  - Integrated the range-projected capillary cochain into the 7-step algorithm.
  - Stage 6 now passes `widehat c_f=Pi_R c_f` to the PPE/corrector path.
  - Stage 7 defines `B^range` as the representative whose weighted face cochain
    is the projected cochain.

- `paper/sections/13_verification.tex` and `paper/sections/13b_twophase_static.tex`
  - Added the pressure-jump static-droplet face-balance gate.
  - Recorded the `N=32,T=0.2` range-projected static droplet result:
    final KE `7.783e-38`, volume drift `1.777e-15`,
    corrected face acceleration `3.816e-17`, raw Hodge residual `1.139e-3`.

- `paper/sections/15_conclusion.tex`
  - Updated the paper headline PPE design to include capillary cochain range
    projection.

## Validation

- `git diff --check` PASS.
- `make -C paper` PASS; generated `paper/main.pdf` (245 pages).
- Error scan of `paper/main.log` found no LaTeX fatal/error/undefined-control
  entries.
- Existing overfull hbox in `paper/sections/09f_pressure_summary.tex` line 71
  remains pre-existing and outside this change.

## Notes

- [SOLID-X] Paper/docs only; no production source code changed.
- No FD/WENO/PPE fallback or alternate calculation scheme was introduced.
- Main merge was not performed.
