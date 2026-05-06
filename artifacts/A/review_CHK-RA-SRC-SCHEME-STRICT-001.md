# CHK-RA-SRC-SCHEME-STRICT-001 — src Scheme Fidelity/GPU/SOLID Review

Date: 2026-05-06
Branch: `codex/src-scheme-strict-review-20260506`
Worktree: `.claude/worktrees/codex-src-scheme-strict-review-20260506`

## Scope

Strict targeted review of `src/twophase/` computational schemes against:

- paper-exact numerical contracts (CCD/FCCD/UCCD6, split PPE, HFE/range projection);
- GPU-first implementation discipline through `backend.xp`;
- SOLID/C1 and public construction-route hygiene.

## Rounds

### Round 1 — MAJOR fixed

`weno5` was still selectable through public CLS advection config/registry even
though PR-1 and §11 classify WENO as reference/comparison, not a solver-core
production route.  Fix: retain `LevelSetAdvection` as a C2 direct-import
reference, but remove it from the active `ILevelSetAdvection` registry and
public config choices.  Tests now assert the public route rejects `weno5`.

### Round 2 — MAJOR fixed

`UCCD6ConvectionTerm` claimed skew-symmetric NS advection but implemented the
plain non-conservative CCD form `u_k D_k u_j`.  §11 limits that form to smooth
single-phase manufactured/comparison notation.  Fix: UCCD6 bulk advection now
uses the CCD skew form
`0.5[(u·∇)u_j + ∇·(u_j u)]`, with the existing selective hyperviscosity kept
on `backend.xp`.

### Round 3 — MAJOR fixed

Capillary range projection was only opt-in in the modern NS option defaults,
despite §9/§11/§13 identifying the affine pressure-jump stack as the current
standard.  Fix: direct construction now uses `capillary_range_projection="auto"`:
it resolves to `range_projected` for pressure-jump + affine-jump coupling and
to `none` for legacy/non-capillary routes.  Explicit invalid combinations still
fail closed.

### Round 4 — PASS

PPE defect correction and capillary range projection were checked against
§9 Hodge closure.  The implementation solves the auxiliary problem with the
same face-flux/divergence operator and restores solver context afterward.  No
MAJOR+ issue found.

### Round 5 — PASS

GPU-first hot-path scan found remaining host conversions only in diagnostics,
explicit direct sparse solvers, host-only C2 references, metadata assembly, or
non-hot setup paths.  No MAJOR+ issue found.

## Validation

- `make test PYTEST_ARGS="..."` attempted first; remote was unavailable and
  Make's local fallback failed because `python` is not on PATH in this
  worktree.
- Local targeted fallback via workspace venv:
  `src/twophase/tests/test_config.py`,
  `src/twophase/tests/test_config_io_fccd.py`,
  selected `test_ns_pipeline_fccd.py`: `19 passed, 3 skipped`.
- Broader local fallback:
  `src/twophase/tests/test_config_io_fccd.py`: `70 passed`.
- Scheme-local fallback:
  `src/twophase/tests/test_ns_terms.py`,
  `src/twophase/tests/test_uccd6.py`,
  `src/twophase/tests/test_ns_pipeline_fccd.py`: `84 passed`.
- Full local CPU suite via workspace venv:
  `src/twophase/tests`: `587 passed, 32 skipped`.
- `git diff --check`: PASS.

## SOLID

[SOLID-X] No C1 violation found in the final audited construction routes.
The fixes narrow public scheme selection, restore the existing UCCD6 contract,
and avoid adding alternate numerical fallbacks.  No tested implementation was
deleted; WENO5 remains a direct-import C2 reference.
