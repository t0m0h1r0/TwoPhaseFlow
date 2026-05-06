# CHK-RA-CH9-002 — Chapter 9 Strict Narrative Review

Date: 2026-05-06
Scope: `paper/sections/09_ccd_poisson.tex`, `09b_split_ppe.tex`, `09c_hfe.tex`, `09d_defect_correction.tex`, `09e_ppe_bc.tex`, `09f_pressure_summary.tex`
Verdict: PASS after 2 rounds. FATAL 0 / MAJOR 0.

## Round 1 Verdict: FAIL

### MAJOR-1 — Latest pressure-jump stack was not the chapter-level closure

The chapter body had introduced capillary range projection and Hodge/face-cochain pressure representation, but the chapter entrance and exit still defined the §9 closure as only phase-separated PPE + jump gradient + HFE + DC + gauge/reprojection. This made the latest research stack in Ch. 11 and Ch. 13 appear optional rather than part of the canonical pressure-jump closure.

Evidence:
- `paper/sections/09_ccd_poisson.tex:41-56`: chapter closure omitted `\Pi_{\mathcal{R}_h}c_f`.
- `paper/sections/09b_split_ppe.tex:22-33`: split-PPE closure list omitted capillary range projection.
- `paper/sections/09f_pressure_summary.tex:9-24,60-77`: final summary omitted capillary range projection.

Fix:
- Added "毛管 cochain 値域射影" as a first-class closure problem in the chapter opening, split-PPE closure list, and final summary.
- Added `\Pi_{\mathcal{R}_h}c_f` / `a_f^{\mathrm{range}}` to the closure equations.
- Reconnected the final narrative to the latest range-projected pressure-jump stack.

### MAJOR-2 — DC was split between a fixed `k=3` contract and a residual contract

The chapter's front matter and split-PPE discussion treated `DC k=3` as a closure condition, while §9d correctly stated that the numerical contract is the high-order residual criterion. This is a logical inconsistency: `k=3` can be an observed practical cap in component tests, but it cannot be the proof obligation for a coupled pressure-jump PPE.

Evidence:
- `paper/sections/09_ccd_poisson.tex:48-56`: closure used `DC k=3`.
- `paper/sections/09b_split_ppe.tex:30-31,148-154`: split-PPE box made `k=3` the headline claim.
- `paper/sections/09d_defect_correction.tex:17-25,129-155`: residual criterion already stated the correct contract.

Fix:
- Replaced closure-level `DC k=3` with `DC{\eta_{\mathrm{DC}}\le\varepsilon_{\mathrm{PPE}}}`.
- Reframed `k=3` as a component-test observation/practical upper bound, not the physical or numerical closure condition.
- Updated the DC comparison table heading and split-PPE accuracy box accordingly.

### MAJOR-3 — HFE heading overclaimed the guaranteed order

The HFE title and opening made `O(h^6)` sound like a blanket interface-extension guarantee. Later text correctly limited the order to the Hermite interpolation data contract, with full tensor mixed derivatives and sufficiently accurate closest-point geometry. The heading therefore overstated the result and weakened the chapter's credibility.

Evidence:
- `paper/sections/09c_hfe.tex:10,17-23`: title and opening implied unconditional `O(h^6)` interface extension.
- `paper/sections/09c_hfe.tex:187-202`: later paragraph gave the actual data-condition caveat.

Fix:
- Retitled HFE as a "高次片側データ契約".
- Moved the `O(h^6)` claim to the conditional interpolation setting.
- Changed the conceptual figure wording from pressure-increment smoothing to one-sided pressure representatives, aligning it with affine-jump face cochains.

### MAJOR-4 — §9e still read like an obsolete strategy menu

The condition-number section described smoothed-Heaviside stabilization and high-density "switching" language after the chapter had already selected pressure-jump split PPE as the canonical closure. This blurred the narrative distinction between retained latest content and historical/model-comparison material.

Evidence:
- `paper/sections/09e_ppe_bc.tex:23-44`: "安定化戦略" and "切替条件" framing made the final path look conditional rather than selected.

Fix:
- Reframed §9e as model boundaries plus the adopted pressure-jump closure.
- Kept low-density smoothed-Heaviside material as a contrast/model-limit analysis only.

## Round 2 Verdict: PASS

Rescan found no remaining MAJOR+ issue in Ch. 9 narrative, notation consistency, chapter structure, or latest-stack consistency.

Targeted checks:
- No obsolete process-history terms in Ch. 9 (`masked`, plot-failure wording, old-results wording, version/change-log framing, `fallback`).
- Closure equations now include capillary range projection and DC residual contract at entrance, body, and exit.
- HFE order claim is conditional and no longer a chapter-title guarantee.
- `git diff --check` PASS.
- `make -C paper` PASS: `paper/main.pdf`, 245 pages.
- `paper/main.log` fatal/error/undefined-control/overfull scan PASS.

[SOLID-X] Paper/review/bookkeeping only; no `src/twophase/`, experiment script, config, or result change; no tested implementation deleted; no FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing, masked-output fallback, or alternate pressure scheme introduced.
