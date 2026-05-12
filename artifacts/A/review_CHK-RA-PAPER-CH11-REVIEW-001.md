# CHK-RA-PAPER-CH11-REVIEW-001 — Chapter 11 Strict Paper Review

Date: 2026-05-12
Branch: `codex/ra-paper-review-ch11-20260512`
Scope: Chapter 11 paper text and directly required cross-reference wording in Chapters 1, 2, 9, 12--15.

## Review Units

| Unit | Files | Rounds | Result |
|---|---|---:|---|
| Chapter 11 overview and 7-stage algorithm | `paper/sections/11_full_algorithm.tex` | 2 | No MAJOR+ remains |
| Bootstrap / timestep bridge | `paper/sections/11c_dccd_bootstrap.tex` | 1 | No MAJOR+ remains |
| Pure FCCD DNS advanced closure | `paper/sections/11d_pure_fccd_dns.tex` | 1 | No MAJOR+ remains |
| Active-geometry capillary decomposition | `paper/sections/11e_ao_fast_state_space.tex` | 4 | No MAJOR+ remains |
| Adjacent terminology and adoption-boundary pass | `paper/sections/01*.tex`, `paper/sections/02*.tex`, `paper/sections/09*.tex`, `paper/sections/12*.tex`, `paper/sections/13*.tex`, `paper/sections/14_benchmarks.tex`, `paper/sections/15_conclusion.tex`, `paper/main.tex` | 3 | No MAJOR+ remains |
| Whole target pass | Chapter 11 plus affected cross-references | 3 | No MAJOR+ remains |

No unit reached the 20-round cap.

## Round Findings And Fixes

### Round 1: Chapter 11 Narrative

- MAJOR: The old term `AO-Fast` was not a paper-facing method name; `AO` only identified a short paper and did not tell the reader what the method does.
  - Fix: Named the method `アクティブ幾何毛管分解`, defined it as a geometric cell-fraction capillary closure that updates only the active interface support, and removed the old name from rendered target text.
- MAJOR: The Chapter 11 overview interrupted the standard 7-stage algorithm with detailed execution-policy conditions.
  - Fix: Reduced the overview to the method's role and moved the paper-level adoption boundary to the dedicated state-space section.
- MAJOR: The state-space section mixed mathematical claims with implementation-history vocabulary (`packet`, `production admission`, dense direct implementation, configuration/fallback keys).
  - Fix: Reframed it around state owner, compatibility projection, capillary work, approximation error, and adoption conditions for the standard physics path.
- MINOR: Restart-state closure described implementation artifacts (`manifest`, file request time) rather than the paper-level restart equivalence condition.
  - Fix: Rephrased as requested time versus actual pre-step state time.

### Round 2: Cross-Reference Consistency

- MAJOR: U12, V11, and the conclusion still reintroduced the old `AO-Fast` name and packet/failure wording.
  - Fix: Replaced those references with `アクティブ幾何毛管分解`, `採用境界`, `未受理分解`, and `標準物理経路`.
- MINOR: English status labels such as `gate`, `full pressure image`, `CPU exact`, and `drive` obscured the Japanese narrative.
  - Fix: Normalized visible prose to `ゲート`, `全圧力像`, `厳密分解`, and `駆動` where not part of a code path or label.

### Round 3: Active-Geometry Section Polish

- MAJOR: The new method section still contained implementation-oriented English in explanatory prose (`solver family`, `state-changing support stream`, `device-resident`, etc.).
  - Fix: Reworded prose into Japanese descriptions while preserving mathematical labels and established method names.

### Round 4: Implementation Detail Removal

- MAJOR: GPU optimization, hardware/backend language, fallback/fail-close wording, and solver-internal details were not appropriate for the paper narrative.
  - Fix: Removed GPU/backend/PCG/Krylov/YAML/fallback/packet language from the target and affected cross-references. Recast U12/V11 as mathematical adoption-boundary gates: exact full-pressure overprojection is a counterexample, component-volume Hodge is a nonstatic diagnostic, and unresolved active-geometry decomposition stays outside the standard physics path.
- MAJOR: `projection-native` and `face-space contract` remained in the benchmark narrative.
  - Fix: Replaced them with Japanese paper-facing terms: `射影と同じ面フラックス`, `面速度空間`, and `面速度空間の契約`.

## Final Review Result

Chapter 11 now presents a coherent progression:

1. Standard 7-stage Navier--Stokes update and its operator contracts.
2. Bootstrap and timestep constraints.
3. Pure FCCD DNS as an advanced sharp-interface closure, not the verified standard path.
4. Active-geometry capillary decomposition as a named future capillary route with explicit mathematical adoption gates.

MAJOR or BLOCKER findings remaining: none.

## Verification Executed

- `git diff --check` — PASS.
- Targeted terminology scan for old method name and internal/implementation vocabulary — PASS; no hits for `AO-Fast`, GPU/backend/PCG/Krylov/YAML/fallback/packet language, `projection-native`, or `face-space` in the target and affected cross-references.
- `make -B -C paper` — PASS; `paper/main.pdf` rebuilt.
- `paper/main.log` warning/error/undefined-reference scan — PASS; no matches in the checked warning/error pattern.
