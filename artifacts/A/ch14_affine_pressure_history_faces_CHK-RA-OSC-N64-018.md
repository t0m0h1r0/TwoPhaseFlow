# CHK-RA-OSC-N64-018 — affine pressure-history face contract

## Question

Does the remaining static Young--Laplace failure come from treating the IPC
history pressure as a nodal scalar gradient instead of the same affine face
pressure acceleration used by PPE/projection?

## Theory

For an affine pressure-jump closure, pressure is discontinuous across the
interface.  Therefore the predictor history term must not evaluate
`grad(p^n)` by a nodal scalar gradient at cut faces.  The discrete object that
has a physical static-equilibrium limit is the face acceleration

`a^n_{p,f} = A_f (G_f p^n - B_f(j^n))`.

In an exact static droplet, `G_f p^n` contains the Young--Laplace jump and
`B_f(j^n)` removes the singular cut-face contribution.  The remaining
acceleration vanishes up to smooth-phase error.  A nodal gradient of the
stored discontinuous pressure cannot satisfy this cancellation.

## Change

- `NSStepState` now carries previous/current pressure acceleration face
  components.
- `solve_ns_pressure_stage` stores current physical pressure as affine
  face-space pressure acceleration using the same pressure-flux kwargs as the
  corrector.
- `compute_ns_predictor_stage` consumes the stored face acceleration in
  face-native predictor mode, reconstructing nodes only as a derived input for
  the viscous predictor and correcting predictor faces back to the canonical
  face source.
- `TwoPhaseNSSolver` persists the face history across steps and clears it when
  the grid is rebuilt.
- Paper §9b, §13f, and §14 now state the pressure-history face contract and
  record the N64 static-droplet improvement.

## Validation

- `py_compile` PASS for changed solver/test modules.
- Targeted `make test` PASS:
  `3 passed, 547 deselected` for pressure-history face storage/consumption
  and affine corrector context forwarding.
- `make -C paper` PASS; `paper/main.pdf` rebuilt.
- `git diff --check` PASS.

Remote was unavailable from the sandboxed command path, so validation ran via
the documented local fallback with the repository `.venv` on `PATH`.

## Static droplet result

Production route:

`make cycle EXP=experiment/run.py ARGS='--config ch14_static_droplet_n64_alpha2_like_oscillating'`

with local fallback completed `T=1.5`.

| metric | CHK-016 post transport fix | CHK-018 affine history faces |
|---|---:|---:|
| steps | 2320 | 2317 |
| final KE | `1.686513e-02` | `6.994038e-05` |
| max KE | `1.686513e-02` | `6.994038e-05` |
| `KE >= 1e-3` | `t=0.551775` | never |
| `KE >= 1e-2` | `t=1.199616` | never |
| final volume drift | `8.741532e-04` | `1.045073e-05` |
| final speed `L_inf` | `2.393391e-01` | `3.445336e-03` |
| final pressure contrast | `2.681811e+01` | `5.033101e-01` |

Short curvature-contract diagnostic also improved at `T=0.4`:
final KE `6.548e-06`, final cut-face `kappa` std `1.039808e-01`
instead of the CHK-014/017 `O(1)` remainder.

## Verdict

Supported.  The remaining dominant static-droplet failure was the IPC
pressure-history representation mismatch, not CFL, smoothing, damping,
curvature clipping, or a pressure deletion workaround.  The fix is a
projection-native affine face-space history contract.

[SOLID-X] no violation found.  The pressure-face kwargs are centralized in the
step service; solver state only persists the canonical face quantity; no
tested implementation was deleted.
