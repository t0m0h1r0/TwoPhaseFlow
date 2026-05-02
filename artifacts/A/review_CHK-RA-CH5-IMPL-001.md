# CHK-RA-CH5-IMPL-001 — Chapter 5 implementation fidelity audit

Date: 2026-05-02  
Branch: `ra-ch5-implementation-audit-20260502`  
Verdict: **PASS AFTER FIX**

## Scope

- Paper: `paper/sections/05_reinitialization.tex`, `paper/sections/05b_cls_stages.tex`, and the non-uniform D3/D4 reference in `paper/sections/10d_ridge_eikonal_nonuniform.tex`.
- Library: `src/twophase/levelset/heaviside.py`, `reinit_dgr.py`, `reinit_eikonal.py`, `reinitialize.py`, `ridge_eikonal_*`, and the simulation reinitialization wiring.
- Tests: `src/twophase/tests/test_ridge_eikonal.py`, plus existing `test_levelset.py` and Ridge--Eikonal GPU checks.

## Paper → Code Chain

- DGR (§5, `sec:dgr_thickness`) requires: band median `ε_eff = median[ψ(1−ψ)/|∇ψ|]`, logit inversion, `ε_eff/ε` rescale, `H_ε` reconstruction, then φ-space mass correction. The default implementation now performs exactly this chain; optional φ-Laplacian smoothing is explicit opt-in only.
- ξ-SDF (§5, `eq:xi_sdf`) is a uniform-grid basis in index space. The library now rejects `eikonal_xi` and legacy `eikonal_fmm` on non-uniform grids instead of silently applying index-space geometry there.
- Non-uniform Ridge--Eikonal follows §10 D3/D4: physical FMM seeding and quadratic update use physical `h_x,h_y`; reconstruction uses `ε_local(x)=ε_scale(ε/h_min)sqrt(h_x h_y)` with volume-weighted φ-space mass correction.
- Stage F mass closure uses φ-space Newton linearization weights `H'_ε V`; Stage B retains the ψ-space interface-local correction for post-advection closure only.

## Findings And Fixes

- **F1 — DGR default was not paper-exact.** `phi_smooth_C=1e-4` inserted an undocumented CCD Laplacian smoothing step into the default DGR map. Fixed defaults to `0.0` through the facade and simulation wiring while preserving the explicit opt-in code path.
- **F2 — Ridge--Eikonal silently overwrote explicit width.** `method="ridge_eikonal"` used `max(eps_scale, 1.4)`, preventing the paper-required explicit `f=1`/`f>1` comparisons. Removed the lower bound; configs that need `1.4` must state it.
- **F3 — Uniform-basis Eikonal paths were allowed on non-uniform grids.** `eikonal_xi`/legacy `eikonal_fmm` are now rejected on non-uniform grids; users must select `ridge_eikonal` for D3/D4 compliance.
- **F4 — Legacy CPU FMM was reachable from GPU.** `eikonal_fmm` now rejects GPU use instead of converting through the host; GPU-resident FMM remains the `ridge_eikonal` path.
- **F5 — Paper wording implied fallback.** Chapter 5 now describes those routes as explicit comparison paths or auxiliary reconstruction, not fallback behavior.

## GPU Check

- Remote CuPy smoke: `Backend(use_gpu=True)`, non-uniform `ridge_eikonal`, output stayed CuPy, `ε_local` stayed device-resident, explicit `eps_scale=1.0` was preserved, and relative volume drift was `8.067390e-06`.
- Existing GPU parity tests passed for fused Ridge kernels and GPU FMM accepted-set parity with ridge seeds.

## Validation

- `git diff --check` PASS.
- Remote targeted pytest PASS: new sentinels `3 passed in 0.15s`.
- Remote targeted pytest PASS: Ch5/Eikonal/Ridge regressions `10 passed in 0.37s`.
- Remote GPU pytest PASS: Ridge/FMM GPU tests `2 passed in 0.51s`.

## SOLID

- [SOLID-X] No tested implementation was deleted. Legacy/optional paths remain explicit, but paper-inexact automatic behavior was removed or rejected.
- [SOLID-X] Strategy boundaries remain intact: facade dispatch, DGR, uniform Eikonal helpers, and non-uniform Ridge--Eikonal FMM stay separated.
