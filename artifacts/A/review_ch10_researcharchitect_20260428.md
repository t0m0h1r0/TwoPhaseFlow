# §10 ResearchArchitect Review — 2026-04-28

Initial verdict: FAIL (1 FATAL, 3 MAJOR, 2 MINOR).

## Scope
- Reviewed `paper/sections/10_grid.tex`.
- Reviewed `paper/sections/10b_ccd_extensions.tex`.
- Reviewed `paper/sections/10c_fccd_nonuniform.tex`.
- Reviewed `paper/sections/10d_ridge_eikonal_nonuniform.tex`.
- Cross-checked Ridge definition in `paper/sections/03d_ridge_eikonal.tex` and FCCD base form in `paper/sections/04e_fccd.tex`.

## Findings
- R10-1 FATAL: `paper/sections/10d_ridge_eikonal_nonuniform.tex:176` computes `[\bnabla_x^2 \xiridge]_{i,j}` as `D2x + D2y`, and `paper/sections/10d_ridge_eikonal_nonuniform.tex:190` says mixed terms are unnecessary. This contradicts `paper/sections/03d_ridge_eikonal.tex:98`, where the ridge is defined by the minimum eigenvalue of the full Hessian. A scalar Laplacian or diagonal-only Hessian can flip the ridge sign/orientation for oblique interfaces.
- R10-2 MAJOR: `paper/sections/10_grid.tex:58`, `paper/sections/10_grid.tex:70`, `paper/sections/10_grid.tex:179`, and `paper/sections/10b_ccd_extensions.tex:67` cite `sec:verification`, whose label is in `paper/sections/13_verification.tex`. §10 therefore still depends on the concrete verification chapter instead of keeping the theory/discretization text implementation-neutral.
- R10-3 MAJOR: `paper/sections/10_grid.tex:330` cites `sec:local_eps_validation`, also in the later nonuniform-grid validation section. The warning is valid, but the chapter-local theory should state the incompatibility without depending on a concrete validation chapter.
- R10-4 MAJOR: `paper/sections/10b_ccd_extensions.tex:74` says "次章では ... CLS 界面追跡の移流・再初期化スキームを設計する", but `paper/main.tex:90` moves directly to the verification part and §11 has been removed. This is a stale chapter-order promise.
- R10-5 MINOR: `paper/sections/10d_ridge_eikonal_nonuniform.tex:33` uses visible stale notation `J_x^{\S6}` even though the metric definition now lives in §10, not §6.
- R10-6 MINOR: Source comments still expose old file/section history: `paper/sections/10_grid.tex:1`, `paper/sections/10b_ccd_extensions.tex:1`, and `paper/sections/10c_fccd_nonuniform.tex:1`.

## Required Fixes
- Replace the Ridge nonuniform D2 implementation with a full physical Hessian construction, including `H_{xy}`, and evaluate the same eigenvalue/normal-curvature object required by §3.4.
- Remove direct §13 validation references from §10 prose; keep validation as a downstream check, not as a dependency of the derivation.
- Replace the stale "next chapter" transition with a §10-local closure.
- Rename stale visible metric notation and clean old source-only comments.

## Residual Risk
- No source code was changed in this review checkpoint; SOLID audit is not applicable.
