# CHK-RA-CH6-IMPL-001 — Chapter 6 implementation fidelity audit

Date: 2026-05-02  
Branch: `ra-ch6-implementation-audit-20260502`  
Verdict: **PASS AFTER FIX**

## Scope

- Paper: `paper/sections/06_scheme_per_variable.tex`, `06b_advection.tex`, `06c_fccd_advection.tex`, `06d_viscous_3layer.tex`.
- Library: FCCD level-set/momentum advection, UCCD6 convection defaults, viscous 3-layer spatial evaluator, non-uniform grid metrics, and simulation/config wiring.
- Tests: focused CPU and GPU parity/smoke coverage for FCCD, UCCD6, ψ direct transport mass closure, non-uniform metrics, and viscous interface switching.

## Paper → Code Chain

- CLS ψ advection: Chapter 6 requires FCCD conservative face-value flux, TVD-RK3 stage clamp, then ψ-space mass correction. The runtime now defaults to `fccd_flux`, applies direct-ψ transport mass correction with `grid.cell_volumes()`, and keeps phi-primary correction outside the φ advection operator to avoid the known double-correction bug.
- Momentum advection: Chapter 6 scheme assignment sets UCCD6 as the bulk velocity default, with FCCD Option B/C as explicit alternatives. Library defaults now use `uccd6`; FCCD docs now state the implemented conservative `P_f(u_k u_j)` path rather than claiming a skew-symmetric substitution.
- Viscous 3-layer: `ccd_bulk` keeps the paper split: bulk `μΔ_CCD u` only outside the ψ interface band, full stress-divergence in the interface band, low-order physical-coordinate derivatives along interface-normal directions, and CCD tangential derivatives where smooth.
- ρ/μ update: runtime property update already implements `rho_g + (rho_l-rho_g)ψ` and `mu_g + (mu_l-mu_g)ψ`; the audit found no Chapter 6 code divergence there.
- Non-uniform grids: FCCD face values/divergence use physical face/control-volume widths, CCD derivatives use metric transforms, viscous low-order derivatives use non-uniform 3-point formulas, and non-uniform metric rebuilds now reject low-order substitution unless a `CCDSolver` is supplied.

## Findings And Fixes

- **F1 — Legacy defaults contradicted Chapter 6.** `NumericsConfig`, `RunCfg`, solver options, direct solver constructor defaults, and builder fallbacks still selected `dissipative_ccd`/`ccd`. Fixed to `fccd_flux`/`uccd6`.
- **F2 — direct ψ transport missed post-clamp mass closure.** `PsiDirectTransport` now snapshots mass and applies ψ-space interface-weighted mass correction after advection/reinit. `PhiPrimaryTransport` remains the only owner of phi-primary mass closure.
- **F3 — non-uniform metrics allowed a low-order substitute.** `compute_metrics()` now fails closed for non-uniform coordinates without a CCD metric solver, preserving the paper-required high-order metric path.
- **F4 — FCCD Option B docs overstated skew-symmetric behavior.** Documentation now matches the implemented conservative single-face-value flux; no hidden logic switch was added.
- **F5 — fallback wording in viscous helpers obscured the paper switch.** Renamed the interface derivative selector and rephrased the explicit viscous branch as an explicit branch, not a fallback.

## GPU Check

- FCCD and UCCD6 GPU parity smoke passed on remote CuPy/CUDA.
- New ψ direct transport mass correction keeps the corrected field as a CuPy array and restores mass to `<1e-12` in the GPU smoke.
- The touched hot paths use `backend.xp` and device reductions; no new host-side scalar control branch was introduced in the GPU path.

## Validation

- Remote CPU targeted pytest PASS: `25 passed in 11.48s`.
- Remote GPU targeted pytest PASS: `10 passed in 0.86s`.
- Remote default-construction smoke PASS: default solver reports `fccd_flux uccd6 FCCDLevelSetAdvection UCCD6ConvectionTerm`.
- Additional existing integration probes were not used as acceptance because they fail on unrelated current constraints: CSF/local-epsilon validation and missing remote `experiment/ch13` YAML.

## SOLID

- [SOLID-X] No tested implementation was deleted; legacy schemes remain explicit alternatives.
- [SOLID-X] The correction is localized to configuration defaults, transport mass closure, metric contract enforcement, and documentation/tests; solver strategy boundaries remain intact.
