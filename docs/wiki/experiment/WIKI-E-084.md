# WIKI-E-084 - Ch13 Closed-Interface Volume Admission Gate

## Claim

Chapter 13 now includes V12 as a closed-interface volume admission gate for
the Section 14.2 oscillating droplet.  V12 is not an accepted physical
benchmark; it prevents stale `sharp_phase_volume` / Ridge--Eikonal language
from being read as the current production route.

## Evidence

Artifact:

```text
artifacts/A/review_CHK-RA-CH12-13-EXPAUD-001.md
```

Command:

```text
make cycle EXP=experiment/ch13/exp_V12_closed_interface_volume_gate.py
```

Result:

```text
current_active_geometry: ok
sharp_volume_on_compatibility_projection: ValueError
ridge_eikonal_on_active_geometry: ValueError
relative_overcount = +0.000000e+00
prefix step 1 mass_rel = -1.080216e-01
prefix step 1 sharp_area_rel = -5.993794e-03
prefix step 2 = projection-native face-history grid-rebuild blocker
one_period_production_admissible = 0
```

## Paper Boundary

V12 updates Chapter 13 and Section 14.2 as an admission gate.  It does not
rerun or invalidate V1--V11, because the PhaseRegion graph/closed-chart route
remains reduced-chart evidence with `force_admissible=0`.

## Use This Card When

- deciding whether Chapters 12--13 need reruns after reading Section 14.2;
- citing the current oscillating-droplet YAML state-space boundary;
- reviewing claims that `sharp_phase_volume` / Ridge--Eikonal is still the
  production setting for the Section 14.2 closed-interface runtime.
