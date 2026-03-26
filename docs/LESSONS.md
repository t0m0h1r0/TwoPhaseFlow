# LESSONS

## §A — Known Error Classes (Mathematical / Code)

| LES-ID | Failure | Cause | Fix Pattern | Reuse Condition |
|---|---|---|---|---|
| KL-01 | Block matrix (2,1) sign flip after RHS transposition | Reading LHS sign directly instead of reading RHS sign first, then negating | Read RHS coeff → negate → write to LHS. Verify with `ccd_solver.py`: A_L(2,1) = b₂/h < 0, A_R(2,1) = −b₂/h > 0 | Any block-matrix entry derived by RHS transposition |
| KL-02 | Wrong block size (3×3 vs 2×2) in documentation | Copy-paste from old 3-variable formulation | Verify block dimensions against actual code arrays | Any block matrix documentation update |
| KL-03 | Pseudocode comment names wrong algorithm (台形則 vs Riemann sum) | Stale comment not updated after algorithm change | Cross-check algorithm name in comment vs. actual accumulation pattern in code | Any pseudocode with named numerical schemes |
| KL-04 | D(κf) ≠ κD(f) for spatially varying κ | Forgetting Leibniz rule when κ varies in space | Expand D(κf) = κD(f) + f·∇κ — never factor out variable coefficients | Surface tension, variable-density Navier-Stokes, any PDE with spatially varying coefficients |
| KL-05 | Nyquist modified wavenumber ≠ finite-grid spectral radius | Confusing continuous Fourier analysis with finite-grid eigenvalue analysis | Compute spectral radius of actual discrete matrix for finite-N stability bounds | CFL derivation, stability analysis for CCD or compact schemes |
| KL-06 | Pre-asymptotic O(h⁴) convergence mistaken for asymptotic rate | Testing on insufficiently refined grids where leading-order term not dominant | Confirm asymptotic regime: slope must stabilize across at least 3 grid doublings | Any convergence order claim from log-log regression |
| KL-07 | "Conservative" CFL rounding in wrong direction | Ceiling instead of floor (or vice versa) when converting float dt to integer steps | Conservative means SMALLER dt — use floor for dt, ceiling for Nsteps | Any adaptive time-stepping or CFL-limited dt calculation |
| KL-08 | Kronecker product index convention: C-order vs. Fortran-order | NumPy (C-order) Kronecker product gives different index mapping than mathematical convention | State index convention explicitly; verify with N=2 example; match paper's stated convention | Any 2D CCD or Kronecker-product assembly |
| KL-09 | PPE solver design intent: LGMRES-primary / LU-fallback confused with LU-primary | Misreading architecture doc or old code with reversed fallback order | LGMRES is primary (iterative, handles large sparse systems); spsolve is automatic fallback only on LGMRES non-convergence | Any PPE solver configuration or documentation |

## §B — Hallucination Patterns (LaTeX / Paper)

| LES-ID | Failure | Cause | Fix Pattern | Reuse Condition |
|---|---|---|---|---|
| KL-04 | (see §A) — also appears as reviewer claim | Reviewer misapplies product rule | Derive D(κf) from first principles; never accept reviewer claim at face value | Reviewer processing (PaperWriter Skepticism Protocol) |
| KL-05 | (see §A) — also appears as stability section error | Confusion between Fourier and finite-grid analysis | Independent derivation of spectral radius for N=2 or N=4 | Stability section review |
| KL-06 | (see §A) — also claimed by reviewers as "wrong order" | Pre-asymptotic behavior on coarse grids | Demonstrate asymptotic regime with 4+ grid levels | Convergence claims in paper |
| KL-07 | (see §A) | | | |
| KL-08 | (see §A) | | | |
| KL-10 | Collocated-grid corrector claims exact CCD-divergence-free (`D_CCD·u=0`) after projection | RC divergence used in PPE RHS leaves residual `∇_RC·u* − D_CCD·u* = O(h²)` uncancelled | State `∇_h^RC·u^{n+1}=0` (RC sense); add O(h²) note for CCD sense | Any collocated-grid projection with Rhie-Chow PPE |
| KL-11 | Pin-node exclusion in residual diagnostic still targets old corner (0,0) after pin moved to center (N/2,N/2) | `compute_residual()` hardcoded `ravel()[0]` while `solve()` used dynamic center pin | Replace all hardcoded pin-index references with `pin_dof = ravel_multi_index(tuple(n//2 for n in grid.N), grid.shape)` | Any PPE solver change that moves the gauge pin location |
| KL-12 | `\texorpdfstring` missing in numbered heading with math → xelatex hangs at 100% CPU with no log output | `\section{$O(h^4)$ scheme}` without wrapping | Wrap: `\texorpdfstring{$O(h^4)$}{O(h\textasciicircum 4)}` in ALL numbered headings containing math; scan before every compile | Every xelatex compile attempt; any numbered heading with `$...$` |

## Format reference

`LES-ID | failure description | root cause | fix pattern | when to apply this lesson`
