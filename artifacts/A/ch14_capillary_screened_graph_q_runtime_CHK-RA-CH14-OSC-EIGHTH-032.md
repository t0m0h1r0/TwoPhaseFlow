# CHK-RA-CH14-OSC-EIGHTH-032 — Capillary screened graph-q runtime probe

## Claim

The Ch14 capillary-wave GPU baseline is still admitted for a short runtime
probe, but the screened graph-q rebuild is not yet an admissible production
route.

## Evidence

- Baseline remote command:
  `make cycle EXP=experiment/ch14/diagnose_capillary_direction.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 2 --print-every 1 --plot-pdf experiment/ch14/results/capillary_direction_baseline.pdf'`
- Baseline result: PASS.  Remote output reached step 2 and pulled
  `experiment/ch14/results/capillary_direction_baseline.pdf`.
- Baseline sampled values:
  step 1 `t=3.651782879273e-05`, `raw_accel_cos=2.753533350606e+01`,
  `balanced_accel_cos=-2.753533350606e+01`, `compat_linf=0`.
  step 2 `t=5.575430939397e-05`, `raw_accel_cos=-2.808607486070e+01`,
  `balanced_accel_cos=2.808607486070e+01`, `compat_linf=0`.
- Screened graph-q command:
  `make cycle EXP=experiment/ch14/diagnose_capillary_direction.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 2 --screened-q-phi-rebuild --print-every 1 --plot-pdf experiment/ch14/results/capillary_direction_screened_q_phi.pdf'`
- Screened result: FAIL before step 1 admission under the strict tolerance
  contract.  The admitted implementation stops while forming the topology
  carrier:
  `GPU active q/phi compatibility projection did not converge; final residual 1.630e-08 exceeds tolerance 1.000e-11`.
- Exploratory loose-predictor probes beyond that fail-close exposed a later
  `compatibility projection line search failed`; that probe was not promoted
  because tolerance weakening is not an admissible fix.

## Interpretation

The failure rejects the simple residual-projection runtime wiring.  The
screened graph-q rebuild needs a direct nonlinear constrained optimization
formulation with a topology-aware merit function; it must not be replaced by
tolerance weakening, rebuild skipping, smoothing, or a different capillary
physics path.

## Preservation Note

This artifact is copied into `main` as negative knowledge before discarding the
unmerged source branch `codex/ra-ch14-osc-droplet-eighth-20260516`.  The source
branch's runtime implementation is intentionally not merged by this artifact.
