# CHK-RA-CH14-N32T1-001 — §9.3 Capillary-Wave Runtime Verification

Date: 2026-04-30
Branch: `ra-ch14-n32t1-ch93-20260430`
Config: `experiment/ch14/config/ch14_capillary_n32_t1_ch93.yaml`
Result: `experiment/ch14/results/ch14_capillary_n32_t1_ch93/data.npz`

## Request

Run the existing ch14 capillary-wave stack at `N=32`, `T=1` from a fresh
`main` worktree and verify whether it behaves as described in paper §9.3.

## Run

```text
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary_n32_t1_ch93"
```

The first run used the same YAML under `config/probes/`, but that location makes
the runner write results under `config/probes/results/`, outside `remote.sh pull`.
The verification config was therefore moved to `experiment/ch14/config/` and run
again so the canonical result lands under `experiment/ch14/results/`.

## Numerical Outcome

| Quantity | Value |
|---|---:|
| final time | `1.000000` |
| steps | `180` |
| `h_min` | `1.779146e-02` |
| `dt_capillary` | `5.582024e-03` |
| limiter code | `3` (`capillary`) |
| kinetic energy start → end | `1.382675e-09 → 3.329482e-05` |
| kinetic energy max | `3.329482e-05` |
| volume drift final | `1.602486e-05` |
| amplitude start → end | `1.196977e-02 → 1.132959e-02` |
| `kappa_max` max | `4.885598e+00` |
| `div_u_max` max | `4.828822e-02` |
| `ppe_rhs_max` max | `1.307128e+01` |

No NaN, no guard-triggered blow-up, and no runaway kinetic-energy growth was
observed for the requested `N=32`, `T=1` run.

## §9.3 Stack Check

| §9.3 item | Runtime evidence | Judgment |
|---|---|---|
| pressure-jump surface tension | YAML uses `surface_tension.formulation: pressure_jump` | PASS |
| oriented affine Young--Laplace route | diagnostics: `ppe_interface_coupling_affine_jump=1`, `ppe_interface_coupling_jump=0` | PASS |
| legacy regular jump disabled | diagnostics: legacy `jump_decomposition` flag remains `0` | PASS |
| DC `k=3` outer correction | YAML uses `solver.kind: defect_correction`, `corrections.max_iterations: 3` | PASS |
| capillary CFL control | diagnostics: `dt_limiter_code=3` for all steps | PASS |
| literal phase-mean gauge paragraph | diagnostics: `ppe_phase_count=1`, `ppe_pin_count=1`, `ppe_mean_gauge=0` | NOT LITERAL §9.3 |

## Interpretation

The run verifies the current affine interface-stress implementation: the sharp
Young--Laplace jump is injected through the affine face-gradient law, the legacy
regular-pressure decomposition is inactive, and the short capillary-wave case
reaches `T=1` without numerical blow-up.

However, the runtime does **not** literally execute the older independent
liquid/gas Neumann-block interpretation in §9.3.  In the current code path,
`affine_jump` deliberately uses a globally connected affine solve with a global
pin gauge, matching the affine-jump research note (`WIKI-X-039`: global gauge,
no zero mask removing cut-face jump flux).  Therefore the requested result is:

- §9.3 affine pressure-jump mechanism: verified active.
- §9.3 text if read as “two disconnected phase blocks with per-phase mean
  gauge”: not what the current affine route runs.

This is a theory/design distinction, not a CFL knob issue.  Making the affine
route both phase-block separated and jump-driven would require a separate
operator design in which the regular pressure coefficient and the known jump
flux coefficient are not the same cut-face mask.

## SOLID Audit

[SOLID-X] No production code was changed in this CHK.  No new SOLID violation
was introduced.
