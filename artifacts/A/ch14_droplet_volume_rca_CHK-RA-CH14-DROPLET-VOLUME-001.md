# CHK-RA-CH14-DROPLET-VOLUME-001 — ch14 oscillating-droplet visible volume-loss RCA

Date: 2026-05-10
Branch: `codex/ra-ch14-droplet-volume-theory-20260510`

## Problem

The ch14 oscillating-droplet run visibly loses droplet volume.  In the current
YAML the reported `volume_conservation` is the diffuse CLS integral

```text
M_psi = sum_i psi_i dV_i,
```

but the physical incompressible liquid volume in the visible plot is the sharp
closed-interface area

```text
V_Gamma = |{x : psi(x) >= 0.5}|.
```

For a Rayleigh--Lamb oscillating droplet with no phase change, no gravity, and
periodic exterior boundary, surface tension may exchange kinetic and surface
energy, but it must not create a monotone phase-volume sink.

## Diagnostic Probe

Added `experiment/ch14/diagnose_droplet_volume_rca.py`.

The probe measures:

- direct ridge-eikonal reinitialization on the initial fitted grid;
- a short prefix of the actual common-flux Navier--Stokes stack;
- the metric area implied by `Grid.cell_volumes()`.

It does not modify physics, tune parameters, damp, smooth, cap curvature, or
change CFL.

Primary local command:

```text
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 \
  experiment/ch14/diagnose_droplet_volume_rca.py --steps 20 --include-static-steps
```

Remote GPU confirmation:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
  make cycle EXP=experiment/ch14/diagnose_droplet_volume_rca.py ARGS="--steps 20"
```

## Hypotheses and Verdicts

| ID | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | Real physics shrinks the droplet. | Rejected | Incompressible two-phase Rayleigh--Lamb motion preserves liquid area; there is no phase change or compressibility term. |
| H2 | The loss is only a visualization/snapshot artifact. | Rejected | Saved snapshot fields give sharp P1 area drift from `7.7360e-05` to about `6.39e-05`, i.e. roughly `-17%`. |
| H3 | Surface tension/pressure jump physically changes volume. | Rejected as primary | Direct reinitialization alone, before pressure and capillary stages, already produces the large area drop in diffuse mode. |
| H4 | CFL/time integration causes the immediate loss. | Rejected as primary | Direct reinitialization has no physical timestep and reproduces the same collapse; two steps are enough. |
| H5 | Dynamic nonuniform grid rebuild is the primary cause. | Rejected as primary | Static fitted grid plus diffuse reinit still gives about `-22%` sharp-area loss. |
| H6 | `diffuse_mass` reinit conserves the wrong closed-phase quantity. | Supported, primary | Direct reinit on the current fitted IC: diffuse mode `sharp_area_rel=-2.235799e-01`; sharp mode `sharp_area_rel=+1.723668e-04` on remote GPU. |
| H7 | Periodic/nonuniform control volumes are inconsistent with the physical domain. | Supported, secondary | `Grid.cell_volumes()` summed over the periodic N+1 node array gives `4.423000451181e-04` while the physical domain is `4.000000000000e-04`, a `+10.575%` overcount. |
| H8 | `sharp_phase_volume` is unusable because it fail-closes around step 400. | Not reproduced in this diagnostic | Current GPU short/500-step probes did not fail-close; this was checked only to address previous ledger evidence and is not needed for the primary conclusion. |
| H9 | Common-flux transport conserves `M_psi` but not necessarily `V_Gamma`. | Supported as a secondary issue | With sharp reinit, short prefixes are stable, but longer prefixes still drift in sharp area; static and dynamic fitted grids behave similarly, so this is not specifically a rebuild-only defect. |
| H10 | Boundary leakage causes loss. | Rejected | The case is periodic, and the immediate loss appears in a local representation projection.  The boundary issue found is duplicate-node quadrature, not physical leakage. |
| H11 | Density/momentum projection causes the visible collapse. | Rejected as primary | The collapse is present before momentum prediction, PPE, and velocity correction. |
| H12 | Initial ellipse geometry is invalid. | Rejected as primary | Sharp reinit preserves the same initial ellipse area to `O(1e-4)` relative on GPU. |

## Key Measurements

Remote GPU direct reinitialization:

```text
DIRECT_REINIT dynamic_diffuse mass_rel=+1.069251e-02 sharp_area_rel=-2.235799e-01 psi_max=9.452615e-01
DIRECT_REINIT dynamic_sharp   mass_rel=+3.383435e-07 sharp_area_rel=+1.723668e-04 psi_max=9.971234e-01
DIRECT_REINIT static_diffuse  mass_rel=+1.069251e-02 sharp_area_rel=-2.235799e-01 psi_max=9.452615e-01
DIRECT_REINIT uniform_diffuse mass_rel=+1.202181e-03 sharp_area_rel=-7.373827e-02 psi_max=9.618608e-01
DIRECT_REINIT uniform_sharp   mass_rel=+2.020052e-07 sharp_area_rel=+8.054234e-05 psi_max=9.876631e-01
```

Remote GPU short prefix:

```text
SHORT_STEP dynamic_diffuse step=2 sharp_area_rel=-2.215456e-01
SHORT_STEP dynamic_sharp   step=2 sharp_area_rel=+5.578536e-04
```

Current saved production droplet snapshots:

```text
t=2.652412244614e-05 sharp_area=7.736035396561e-05 rel=+0.000000e+00
t=2.637626679239e-02 sharp_area=6.352724763798e-05 rel=-1.788139e-01
t=5.274892000245e-02 sharp_area=6.431595923957e-05 rel=-1.686186e-01
t=7.910352205292e-02 sharp_area=6.362162974016e-05 rel=-1.775939e-01
t=1.054606630820e-01 sharp_area=6.387314436392e-05 rel=-1.743427e-01
```

## Cause

Primary cause:

```text
experiment/ch14/config/ch14_oscillating_droplet.yaml
  interface.reinitialization.profile.volume_constraint: diffuse_mass
```

This is mathematically the wrong invariant for a closed incompressible droplet
when the plotted object is the zero level / P1 liquid area.  The projection
restores diffuse mass by moving the level-set profile, and that move shifts the
zero level enough to shrink the visible phase area.

Secondary cause:

`Grid.cell_volumes()` is being used as a nodewise quadrature over the full
periodic image array.  For periodic topology, the duplicated endpoint nodes
should not be counted as independent physical measure.  On the fitted N32
droplet grid this overcounts the domain by `+10.575%`.  That makes
`volume_conservation` and diffuse-mass reinit targets less physically
meaningful on periodic fitted grids.

Tertiary issue:

Even when sharp-volume reinitialization is used, the current conservative
transport state conserves the transported diffuse scalar, not a geometric
closed-interface area functional.  This is a real mathematical distinction, not
a parameter-tuning problem, and should be handled by a proper conservative
representation/projection contract rather than damping or CFL changes.

## Required Theoretical Direction

The correct repair should restore the A3 chain:

```text
incompressible closed phase volume V_Gamma
  -> sharp P1 / fixed-stratum liquid-area functional
  -> periodic-topology-aware metric quadrature
  -> reinit/remap/transport projection preserving the intended invariant
  -> ch14 experiment gate reporting V_Gamma, not only |Delta M_psi|/M_psi
```

Allowed directions:

- make oscillating-droplet production preserve `sharp_phase_volume` again;
- correct periodic node quadrature so `sum dV` equals the physical domain;
- add a sharp-area diagnostic/gate for ch14 closed droplets;
- audit common-flux transport/reprojection against `V_Gamma`.

Forbidden directions:

- lowering CFL to hide the symptom;
- damping, smoothing, or curvature capping;
- changing the physical droplet size to make the plot look acceptable;
- using `volume_conservation` of diffuse mass as evidence that the visible
  droplet volume is conserved.
