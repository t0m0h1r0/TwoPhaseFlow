# CHK-RA-CH5-001 — Chapter 5 strict narrative review

Date: 2026-05-06
Branch: `ra-ch5-narrative-review-20260506`
Worktree: `.claude/worktrees/ra-ch5-narrative-review-20260506`
Scope: `paper/sections/05_reinitialization.tex`, `paper/sections/05b_cls_stages.tex`, with adjacent consistency checks against §§3, 6, 10, 11, 12.

## Route

ResearchArchitect classified this as FULL-PIPELINE / A-domain PaperWorkflowCoordinator: PaperReviewer strict review, PaperWriter remediation, PaperCompiler validation.

## Round 1 Verdict: FAIL

MAJOR+ findings: 3. Minor findings: 2.

### Findings

1. **MAJOR-1 — `\psi\leftrightarrow\phi` sign convention is internally inconsistent.**
   `05_reinitialization.tex` used the correct convention in DGR and Eikonal setup, but the ξ-SDF algorithm used `\varepsilon\ln(\psi/(1-\psi))`, the opposite of §3 and §5.2. The wide ξ-SDF reconstruction also wrote `H_{f\varepsilon_\xi}(\phi_\xi)` without the required minus sign. This reverses liquid/gas sign semantics and breaks the claimed zero-set-preserving reconstruction.

2. **MAJOR-2 — The standard Chapter 5 path is obscured by DGR, split reinitialization, and `f>1` width broadening.**
   DGR was introduced as an operational postprocess, then prohibited for capillary vibration, while the later ξ-SDF section prescribed `f>1` broadening or split reinitialization for `\sigma>0`. This made the chapter read as a sequence of compensating fixes rather than one canonical algorithm, and it risked presenting hidden regularization as part of the scheme.

3. **MAJOR-3 — §5.2 contradicts §3 and §11 on curvature evaluation.**
   §5.2 listed “computing curvature from `\psi` before reinitialization” as a failure mode, while §3 proves the `\psi` direct curvature formula and §11 maps the integrated algorithm to `\psi` direct curvature with interface-band filtering. The actual failure is using a distorted, unmonitored `\psi` profile, not `\psi` curvature itself.

4. **MINOR-1 — The adaptive trigger notation used `M(\tau)` for a physical-step quality monitor.**
   `M(\tau)=\int\psi(1-\psi)dV` mixed virtual-time notation with a physical-step trigger and overloaded mass notation. This weakened the narrative separation between physical transport and auxiliary redistancing.

5. **MINOR-2 — Several phrases retained implementation-log vocabulary.**
   Terms such as “production”, “Strategy B”, fixed/no-clamp verification phrasing, and calibration-style `f` language made Chapter 5 sound like a work log rather than a final algorithm statement.

## Remediation

- Repaired ξ-SDF sign convention to `\phi_{\mathrm{raw}}=\varepsilon\ln((1-\psi)/\psi)` and restored the minus sign in `H_{f\varepsilon_\xi}(-\phi_\xi)`.
- Reframed DGR as a diagnostic/comparison thickness correction, not a hidden standard postprocess.
- Made the canonical Stage D/F path explicit: Ridge--Eikonal/FMM/ξ-SDF zero-set distance reconstruction plus Stage F `\phi`-space volume closure.
- Demoted `f>1` width broadening and split reinitialization to explicit comparison/sensitivity conditions, with `f=1` as the standard width-preserving path.
- Replaced `M(\tau)` with `Q_\Gamma` as an interface-band quality measure.
- Rewrote §5.2’s curvature failure mode to distinguish valid `\psi` direct curvature from invalid curvature evaluation on distorted, unmonitored profiles.
- Removed implementation-log wording in the touched Chapter 5 paragraphs.

## Round 2 Verdict: PASS

MAJOR+ findings: 0. FATAL findings: 0.

Checks:

- Targeted sign/terminology scan: PASS.
- `git diff --check`: PASS.
- `make -C paper`: PASS, produced `paper/main.pdf` with 245 pages.
- Build log fatal/error/undefined scan: PASS.
- Existing overfull hbox remains only at `paper/sections/09f_pressure_summary.tex:71`.

## Transparency Record

AI-assisted: true.
Source materials: `paper/sections/05_reinitialization.tex`, `paper/sections/05b_cls_stages.tex`, targeted references in `paper/sections/03b_cls_transport.tex`, `paper/sections/03c_levelset_mapping.tex`, `paper/sections/03d_ridge_eikonal.tex`, `paper/sections/06b_advection.tex`, `paper/sections/10d_ridge_eikonal_nonuniform.tex`, `paper/sections/11_full_algorithm.tex`, `paper/sections/12u4_ridge_eikonal_reinit.tex`.
Verification actions: targeted line review, adjacent consistency scan, terminology scan, LaTeX build, log scan, whitespace check.
