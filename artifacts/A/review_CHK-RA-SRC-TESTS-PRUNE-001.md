# CHK-RA-SRC-TESTS-PRUNE-001 — src/twophase/tests necessity audit

Date: 2026-05-08
Branch: `codex/ra-src-tests-prune-20260508`
Verdict: pruning unit 1

## Retention Rule

Keep tests that protect current paper/PR contracts, active runtime regressions,
GPU/CuPy parity on production paths, public configuration fail-close behavior,
checkpoint/restart/data contracts, visualization fail-close semantics, or prior
fixed bugs on active routes. Remove tests that only exercise retired reference
implementations, obsolete aliases, or weak sanity checks whose behavior is
already protected by stronger current-route tests.

## Removed

| Removed test coverage | Rationale | Replacement / retained guard |
|---|---|---|
| `test_iim.py` | Behavioral tests for retired direct-import IIM/CCD-LU solver internals. They no longer protect active affine-jump/FCCD projection routes. | `test_config.py` rejects retired PPE factory routes; `test_ns_pipeline_fccd.py` keeps IIM reprojector fail-close and runtime bootstrap non-construction guards. |
| `test_iim_ridge_eikonal_chain.py` | End-to-end Ridge-Eikonal -> retired IIM chain. The Ridge-Eikonal and current pressure-jump stacks now have direct tests; the cross-chain target is stale. | `test_ridge_eikonal.py`, `test_ns_pipeline_fccd.py`, and closed-interface Riesz/Hodge tests cover active chain pieces. |
| `test_ppe_ccd_lu_gpu_matches_cpu` | GPU parity for retired CCD-LU PPE reference path. Current GPU smoke should focus on production GPU hot paths. | CPU component/reference CCD-LU checks remain in `test_pressure.py`; GPU production PPE/FVM/FCCD paths remain in GPU smoke files. |
| `test_weno5_zero_bc_order_reduced` | Only asserted nonzero error/no crash for a non-production WENO wall-BC route. | WENO periodic reference order remains; public WENO route rejection remains in config/pipeline tests. |
| legacy config alias tests | Exercised old spelling compatibility only, not current YAML or public fail-close policy. | Current structured config round-trip, canonical ch14 YAML, production default, invalid route, and retired route rejection tests remain. |
| hard-coded rising-bubble grid/domain literals | Duplicated YAML parsing assertions in solver-build coverage and over-specified absolute domain length inside an execution-stack test. | The retained checks cover canonical resolution, stack options, and solver propagation from `cfg.grid`. |

## SOLID-X

[SOLID-X] Test-suite pruning only. No production solver equations, pressure/PPE
routes, capillary force, DCCD/FCCD/UCCD kernels, transport, reinit physics,
boundary conditions, GPU implementation, or experiment configs changed.
