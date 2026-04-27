# CHK-248 — §6 方程式項別空間離散化 再査読レビュー

**Date**: 2026-04-28  
**Branch**: `worktree-ra-ch6-review-fixes`  
**Worktree**: `/Users/tomohiro/Downloads/TwoPhaseFlow-ch6-review-fixes`  
**Reviewer stance**: ResearchArchitect / 査読官スタンス  
**Scope**: current `main` at `c235ee7`, §6 files only unless A3 evidence required
**Closure**: CHK-249 fixes applied in the same worktree; all findings below are closed.

## A. Verdict

**判定**: **Major Revision, near-Reject for §6.3 viscous formulation**

§6 は CHK-240 後に表層の priority mismatch は解消されているが、現行版にはより深い数式・A3 chain の不整合が残る。特に §6.3 Layer C は「応力発散」を一度定義した後でさらに face-to-cell 差分を取っており、次元上は二重発散になっている。これは粘性項の中心定式化を壊すため、査読なら最初に止める。

| Severity | Count | Summary |
|---|---:|---|
| FATAL | 1 | 粘性 Layer C が二重発散になっている |
| MAJOR | 5 | FCCD 精度矛盾、圧力符号、BF 定理の論証不足、粘性 μ placement の A3 断絶、質量保存過剰主張 |
| MINOR | 4 | stale comments / legacy label / misleading ref / unsupported constants |

## B. FATAL Findings

### F-1: §6.3 Layer C is dimensionally inconsistent and contradicts the code path

- **Location**: `paper/sections/06d_viscous_3layer.tex:82`
- **Evidence**:
  - `paper/sections/06d_viscous_3layer.tex:88` defines `(F_mu)_x|_{i+1/2,j}` as a derivative of stresses, i.e. already a viscous force component.
  - `paper/sections/06d_viscous_3layer.tex:99` then computes the cell force by differencing those force components again.
  - The implementation evaluates exactly one stress divergence: `src/twophase/ns_terms/viscous_spatial.py:136` builds stress, then `src/twophase/ns_terms/viscous_spatial.py:140` takes one derivative of stress.
- **Why fatal**: the paper formula implements `div(div(tau))` for the cell RHS, while the governing equation needs `div(tau)`. This changes dimensions and the physics of the viscous operator.
- **Required fix**: define either stress fluxes on faces and take one divergence to cell centers, or define face-centered force components and interpolate/average them to cell centers. Do not take a second divergence of an already-diverged force.

## C. MAJOR Findings

### M-1: FCCD face value accuracy is claimed as `O(h^6)` in §6.1 but defined as `O(H^4)` in §4/§6.2

- **Location**: `paper/sections/06b_advection.tex:121`, `paper/sections/06b_advection.tex:213`
- **Counter-evidence**:
  - §6.2 defines the same `P_f` face interpolation as 4th order: `paper/sections/06c_fccd_advection.tex:43` and `paper/sections/06c_fccd_advection.tex:51`.
  - §4 defines FCCD face jets as `O(H^4)`: `paper/sections/04e_fccd.tex:15`.
  - §6.2 gives the leading truncation term: `paper/sections/06c_fccd_advection.tex:65`.
- **Impact**: the role table advertises CLS advection as face-value `O(h^6)`, but the single-source FCCD definition is `O(H^4)`. A reviewer will read this as inflated order of accuracy.
- **Required fix**: change the §6.1 equation/table to `O(H^4)` for face values and separate it from bulk CCD/UCCD6 `O(h^6)` claims.

### M-2: Momentum closure has the pressure-gradient sign opposite to the governing equation

- **Location**: `paper/sections/06c_fccd_advection.tex:230`
- **Counter-evidence**:
  - One-fluid NS uses `-\nabla p`: `paper/sections/02_governing.tex:155`.
  - The time-integration chapter also uses `-\bnabla p`: `paper/sections/07_time_integration.tex:161`.
- **Impact**: §6.2 closes the momentum update with `+ \nabla p + \sigma\kappa\nabla\psi + g`. Unless `\nabla p` is explicitly defined as the negative pressure force, this violates the equation chain.
- **Required fix**: write `-\nabla p + \sigma\kappa\nabla\psi + g` or define a signed pressure-force operator and use that notation consistently.

### M-3: The FCCD Option B BF theorem does not prove the advertised Option-B effect

- **Location**: `paper/sections/06c_fccd_advection.tex:171`
- **Evidence**:
  - The theorem includes advection as one of the three shared-face terms at `paper/sections/06c_fccd_advection.tex:172`.
  - The proof then sets `u == 0`, making all advection forms identically zero at `paper/sections/06c_fccd_advection.tex:195`.
  - The corollary claims Option B alone removes the `O(H^2)` floor at `paper/sections/06c_fccd_advection.tex:218`.
- **Impact**: the proof supports only pressure/CSF operator matching in a static state. It does not logically establish that Option B is necessary for the static BF residual, because the advection term vanishes under the stated hypothesis.
- **Required fix**: either narrow the theorem to pressure/CSF BF consistency and move Option B to a dynamic/advection consistency proposition, or add a nonzero-flow residual theorem where the convective flux actually enters.

### M-4: Face/corner μ prescriptions in §6.4 are not implemented in the current A3 code chain

- **Location**: `paper/sections/06d_viscous_3layer.tex:245`, `paper/sections/06d_viscous_3layer.tex:277`
- **Evidence**:
  - Paper states face μ is required for Layer C / CN construction and harmonic mean is the default at `paper/sections/06d_viscous_3layer.tex:249` and `paper/sections/06d_viscous_3layer.tex:273`.
  - Paper states corner μ is used for `tau_xy` at `paper/sections/06d_viscous_3layer.tex:281`.
  - Code uses a cell-centered `mu` array directly in stress assembly at `src/twophase/ns_terms/viscous_spatial.py:139` and `src/twophase/ns_terms/viscous_spatial.py:154`.
- **Impact**: the paper promises a face/corner placement strategy, but the code path has no corresponding face μ / corner μ buffers in the viscous evaluator. This is an A3 and PR-5 fidelity gap.
- **Required fix**: either implement face/corner μ placement or downgrade §6.4 to a design requirement not yet implemented, with the actual current code path stated explicitly.

### M-5: CLS advection is advertised as strictly mass-conservative after a nonconservative clamp

- **Location**: `paper/sections/06b_advection.tex:145`, `paper/sections/06b_advection.tex:213`
- **Evidence**:
  - §6.1 states the FCCD flux telescopes and is strictly conservative under periodic boundaries at `paper/sections/06b_advection.tex:148`.
  - The same section then applies a value clamp and admits it is generally not mass-conservative at `paper/sections/06b_advection.tex:168`.
  - The role table still states strict mass conservation for nonperiodic and nonuniform cases at `paper/sections/06b_advection.tex:213`.
- **Impact**: conservation is true for the raw flux divergence under boundary-compatible quadrature, but not for the full advertised CLS step after clamp unless the mass correction is included and proven.
- **Required fix**: qualify the table: raw FCCD flux is conservative; the operational CLS step is conservative only after the §5 mass correction, and only to the tolerance/proof stated there.

## D. MINOR Findings

### m-1: Source comments expose stale file names and old chapter routing

- **Location**: `paper/sections/06_scheme_per_variable.tex:1`
- **Issue**: comments still name `07_0_scheme_per_variable.tex`, `07_advection`, `07c`, and `07e` even though the active files are `06*.tex`.
- **Risk**: not visible in PDF, but it misleads future maintainers and weakens the paper-source hygiene after the §6 relocation.

### m-2: Legacy DCCD labels remain on FCCD equations

- **Location**: `paper/sections/06b_advection.tex:107`, `paper/sections/06b_advection.tex:122`, `paper/sections/06b_advection.tex:125`
- **Issue**: `sec:advection_dccd_design`, `eq:dccd_adv_ccd`, and `eq:dccd_adv_filter` now denote FCCD constructs.
- **Risk**: backward compatibility may justify the labels, but source-level A3 search becomes misleading. Add alias comments in a label registry or migrate active labels with phantomsection aliases.

### m-3: §6.0 table sends UCCD6 readers to the FCCD advection section

- **Location**: `paper/sections/06_scheme_per_variable.tex:45`
- **Issue**: the row says `UCCD6` but references `sec:fccd_advection`. The surrounding text later uses `sec:uccd6_def`.
- **Risk**: minor cross-reference friction; point the table to `sec:uccd6_def` and add a secondary §6.2 reference if needed.

### m-4: CFL constant for FCCD+TVD-RK3 is still citation/derivation-light

- **Location**: `paper/sections/06b_advection.tex:174`
- **Issue**: the box labels the bound as unverified, which is good, but `max |k*_FCCD| approx 2.0` is not tied to a figure/table or DFT lemma.
- **Risk**: a reviewer may ask for the spectrum plot or derivation if the numerical CFL policy depends on the value.

## E. A3 / SOLID Audit

- **A3 chain**: broken for §6.3/§6.4 viscous placement. Paper specifies face/corner μ and Layer C geometry; code currently implements node-shaped stress divergence with direct cell-centered `mu`.
- **PR-5**: violated where paper-exact behavior cannot be traced to implementation (`F-1`, `M-4`).
- **SOLID audit**: no source code was changed in this review. No new `[SOLID-X]` fix is required before the review memo can stand, but any later viscous implementation patch should isolate face/corner μ placement rather than expanding `ViscousSpatialEvaluator` into a larger monolith.

## F. Recommended Repair Order

1. **Fix §6.3 Layer C first**: rewrite the discrete viscous force so it is exactly one stress divergence and matches the code or planned code.
2. **Resolve viscous A3**: decide whether face/corner μ is implemented now or marked as future design.
3. **Normalize FCCD accuracy**: use `O(H^4)` for FCCD face values everywhere in §6.
4. **Correct momentum signs**: align §6.2 closure with §2 and §7.
5. **Split BF theorem claims**: static pressure/CSF theorem vs dynamic advection-locus proposition.
6. **Clean source hygiene**: stale comments, legacy labels, and table cross-references.

## G. Verification Performed

- Loaded `docs/02_ACTIVE_LEDGER.md` first 60 lines per session rule.
- Confirmed new worktree: `worktree-ra-ch6-review-fixes`.
- Reviewed §6 files: `06_scheme_per_variable.tex`, `06b_advection.tex`, `06c_fccd_advection.tex`, `06d_viscous_3layer.tex`.
- Cross-checked §4 FCCD definition, §2 governing signs, §7 time-integration signs, and `src/twophase/ns_terms/viscous_spatial.py`.
- No paper/src fixes were applied in this CHK; this is a reviewer memo only.

## H. Closure Addendum — CHK-249

**Status**: all FATAL/MAJOR/MINOR findings closed by paper edits.

| Finding | Closure |
|---|---|
| F-1 | Rewrote §6.3 Layer C as exactly one cell-centered stress divergence `D^C tau`, matching `ViscousSpatialEvaluator` rather than a second face-to-cell divergence. |
| M-1 | Normalized FCCD face-value accuracy in §6.1 and the scheme-role table to `O(H^4)`, with cross-ref to the §6.2 primitive. |
| M-2 | Corrected the §6.2 closed momentum update to use `-\nabla p`, consistent with §2 and §7. |
| M-3 | Narrowed the static BF theorem to pressure/CSF matching and moved Option B to a dynamic advection-locus proposition. |
| M-4 | Reframed face/corner μ as optional staggered/face-flux extension rules; current A3 path uses cell-centered μ in the collocated stress divergence. |
| M-5 | Qualified mass conservation: raw FCCD flux telescopes before clamp; the operational step requires the §5 mass correction. |
| m-1 | Updated stale `07_*` source comments in §6 files. |
| m-2 | Added active FCCD labels while preserving old DCCD labels as explicit backward-compatible aliases. |
| m-3 | Changed the UCCD6 table cross-ref to `sec:uccd6_def`, with §6.2 retained only as FCCD Option B/C context. |
| m-4 | Tied the FCCD+TVD-RK3 CFL constant to the §4 FCCD Fourier symbol. |

**SOLID/A3 closure**: no source code was changed. [SOLID-X] none. A3 is restored by aligning the paper’s viscous Layer C and μ-placement claims to the current `src/twophase/ns_terms/viscous_spatial.py` code path.

## I. Rereview Closure Addendum — CHK-250

**Status**: the 3 Major findings from the post-CHK-249 rereview are closed by paper edits.

| Finding | Closure |
|---|---|
| RR-M1 | Unified the μ averaging policy with §2: CLS diffuse-interface viscous μ uses arithmetic averaging as the baseline; harmonic averaging is retained only as a sharp-interface/sensitivity option, not as the high-viscosity default. |
| RR-M2 | Added the missing clamp-after mass-correction step to the full algorithm and corrected the stale DCCD wording to FCCD. |
| RR-M3 | Downgraded the viscous energy identity to an idealized energy estimate and explicitly excluded nonuniform grids, one-sided boundaries, and normal/tangent fallback from the strict-identity claim. |

**Verification**: `latexmk -xelatex -interaction=nonstopmode main.tex` completed successfully; targeted grep found no stale `調和平均推奨`, `DCCD は TVD`, or strict energy-identity residue in the patched loci.

## J. Second Rereview Closure Addendum — CHK-251

**Status**: the 3 Major findings from the second post-CHK-250 rereview are closed by paper edits.

| Finding | Closure |
|---|---|
| RR2-M1 | Aligned Layer C wording with the implementation: CCD-derived differences are allowed only in Layer A bulk and smooth tangential directions; interface-normal CCD forcing is the anti-pattern. |
| RR2-M2 | Made Stage B mass correction mandatory for the standard clamp-enabled operation, while preserving no-clamp bounded verification as the only optional case. |
| RR2-M3 | Replaced the over-strong shear-continuity guarantee with an A3 consistency claim: the One-Fluid diffuse-interface stress evaluation avoids discrete asymmetry but does not explicitly enforce the interface jump condition. |

**Verification**: `latexmk -xelatex -interaction=nonstopmode main.tex` completed successfully; targeted grep found no stale `自然に保証`, `Layer C で CCD 使用`, or old optional Stage B wording.

## K. Third Rereview Closure Addendum — CHK-252

**Status**: the remaining Major 1 + Minor 1 from the third rereview are closed by paper edits.

| Finding | Closure |
|---|---|
| RR3-M1 | Disambiguated invalid direct mass correction on non-SDF $\phi$ from the valid DGR/SDF-shift $\phi$-space correction in §5. |
| RR3-m1 | Softened §6.1 clamp-after correction wording from “restore total mass” to “return total-mass error to the prescribed tolerance,” consistent with $\lambda_\psi\in[0.5,1.0]$. |

**Verification**: `latexmk -xelatex -interaction=nonstopmode main.tex` completed successfully; targeted grep found no stale direct `質量補正を $\phi$ に適用` failure wording or `総量を戻す` residue in the patched loci.
