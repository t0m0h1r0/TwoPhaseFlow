# CHK-RA-PAPER-REVIEW-CH01-13-001 Review Record

Date: 2026-05-12
Branch: `codex/ra-paper-review-ch01-13-20260512`
Scope: paper Chapters 1--13, plus local abstract/front references needed for consistency.

## Reviewer Summary

The review found no need to reorder whole chapters in this pass. The major issues were cross-chapter narrative drift:

- The abstract still described the verification program as U1--U11 / V1--V10, while Chapters 12--13 now contain U12 / V11.
- Several passages still described implementation/performance details such as CPU/GPU batching, memory, performance ratios, or "implementation" rather than paper-level operator structure.
- U10/U12/V11 boundary language sometimes sounded like a physical benchmark result rather than a gate that protects the standard physical path.
- Figure 2 and Figure 7 needed to stay aligned with the current narrative: active geometry starts from transported `q_C`, reconstructs a compatible interface `Gamma_h`, derives `phi, psi`, and only then becomes a candidate capillary closure.

All MAJOR findings identified in this pass were fixed and then re-reviewed. No unit reached the 20-round limit.

## Review Units and Rounds

| Unit | Scope | Rounds | MAJOR+ Residual |
|---|---|---:|---|
| Ch.1 | Introduction and method positioning | 2 | None |
| Ch.2 | Governing equations and capillary theory | 2 | None |
| Ch.3 | CLS, mapping, Ridge--Eikonal connection | 2 | None |
| Ch.4 | CCD/FCCD operator foundations | 2 | None |
| Ch.5 | CLS reinitialization stages | 1 | None |
| Ch.6 | Term-wise discretization and FCCD advection | 2 | None |
| Ch.7 | Time integration | 1 | None |
| Ch.8 | Pressure--velocity coupling / BF theory | 1 | None |
| Ch.9 | PPE, HFE, capillary closure, pressure summary | 2 | None |
| Ch.10 | Interface-fitted nonuniform grid | 1 | None |
| Ch.11 | Integrated update and active geometry bridge | 2 | None |
| Ch.12 | Component verification U1--U12 | 2 | None |
| Ch.13 | Integration verification V1--V11 | 2 | None |
| Part-level pass | Ch.1--3, Ch.4--6, Ch.7--10, Ch.11--13 | 2 | None |
| Whole-scope pass | Ch.1--13 plus abstract consistency | 2 | None |

## Main Fixes

- Updated the abstract to U1--U12 / V1--V11 and explicitly framed V11 as an active-geometry admission gate, not a physical benchmark success.
- Removed or demoted implementation-facing detail from the paper narrative:
  - CPU/GPU batching and performance statements in the CCD boundary-cost discussion.
  - The `q`-sharing "optimization" and performance multiplier in the FCCD advection section.
  - "implementation" phrasing where a mathematical formulation or discrete condition was meant.
- Reworded AO-related passages to use the paper-facing name `アクティブ幾何毛管分解` and to clarify the sequence `q_C -> Gamma_h -> phi, psi -> r_sigma/R_p`.
- Aligned Figure 2 and Figure 7 text/box wording with the current flow. Figure 7 now shows the active route as a developmental capillary closure through `Gamma_h`, rather than a direct `q_C -> phi/psi` shortcut.
- Redrew Figure 2 as a two-lane layout with equal-size boxes. The standard path and the developmental active-geometry path now avoid crossing arrows; the old time-loop arrow that cut through the boxes was removed.
- Rephrased U10/U12/V11 exits so they are not mistaken for new physical benchmarks. They are gates or single-component conditions that protect the standard physical benchmark path.
- Reduced English-mixed wording in key tables and captions, especially for `face value/grad`, `metric`, `pressure-jump`, `component-Hodge`, `uniform-offset`, and related visible terms.

## Re-Review Notes

- Ch.1--3 now introduce the narrative as: physical difficulty -> one-fluid and capillary theory -> CLS state and distance reconstruction. No MAJOR narrative gap remains.
- Ch.4--6 now state operator reuse and block structure as mathematical properties, not hardware optimization claims. No MAJOR implementation-detail leakage remains.
- Ch.7--10 already matched the current standard path; only terminology-level and pressure/capillary interpretation checks were needed.
- Ch.11 now keeps the standard pressure-jump path and the active-geometry developmental path separated in both Figure 7 and the surrounding prose.
- Ch.12--13 now consistently present U12 and V11 as gate tests, while U10/U11 remain conditions feeding later physical paths rather than additional Chapter 13 physical benchmarks.

## Verification Plan

- `git diff --check`
- `make -B -C paper`
- `paper/main.log` scan for LaTeX errors, undefined references, and over/underfull warnings.
- Targeted scans for stale U/V counts and implementation/GPU vocabulary in Chapters 1--13.

## Verification Results

- `git diff --check`: PASS
- `make -B -C paper`: PASS, generated `paper/main.pdf` with 273 pages.
- `paper/main.log` scan for LaTeX errors, undefined references, and over/underfull warnings: PASS.
- Targeted scan for `U1--U11`, `V1--V10`, `AO-Fast`, `projection-native`, `face-space`, `GPU`, `CPU`, `YAML`, `D2H`, `CUDA`, `CuPy`, and `最適化` in Chapters 1--13: PASS.
- Rendered Figure 2 page with `pdftoppm -f 16 -l 16 -png -r 180 paper/main.pdf ...` and visually checked that boxes, labels, and arrows no longer collide.
