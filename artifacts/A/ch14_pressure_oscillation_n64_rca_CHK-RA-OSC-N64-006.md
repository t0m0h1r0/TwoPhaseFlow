# CHK-RA-OSC-N64-006 — N64 droplet pressure-oscillation RCA

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

The pressure snapshots show unexplained oscillations.  Diagnose the cause from
the physical and mathematical equilibrium conditions, without ad-hoc fixes.

## Theoretical baseline

For a static circular droplet at rest,

- velocity must remain zero except for numerical spurious current,
- pressure is constant in each bulk phase,
- the only physical discontinuity is the Young--Laplace jump,
  `[p]=sigma kappa=sigma/R`,
- for the tested water-air static droplet, `sigma/R = 0.072/0.25 = 0.288`,
- pressure gauge is arbitrary, so global/phase means are not physical evidence;
  residual pressure after subtracting phase means is the relevant diagnostic.

## Added diagnostics

Added `experiment/ch14/diagnose_pressure_oscillations_n64.py`.

The diagnostic loads saved NPZ fields and measures:

- Young--Laplace jump error,
- bulk, liquid, gas, and interface residual pressure after phase-mean removal,
- high-frequency pressure energy and checkerboard projection,
- angular Fourier amplitudes around the droplet,
- curvature proxy `div(grad H/|grad H|)` from the stored phase field,
- correlation between pressure and curvature in the interface band.

Generated outputs are regenerable under
`experiment/ch14/results/ch14_pressure_oscillation_n64_diagnostics/`.

## Additional control

Added and ran
`experiment/ch14/config/ch14_static_droplet_n64_alpha2_staticgrid_pressure_probe.yaml`.
This preserves the alpha-2 static-droplet physics and numerics, but changes the
fitted-grid schedule from every-step rebuild to a fixed initially fitted grid.
It is a diagnostic control, not a proposed fix.

Command:

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_static_droplet_n64_alpha2_staticgrid_pressure_probe"
```

Result:

- `[static non-uniform] h_min=1.2368e-02`
- first `dt_cap=6.471e-04`
- BLOWUP at `step=2064`, `t=1.322804570956273`
- final/max KE `3.326510429974434e+06`
- final/max volume drift `9.1376353366593e-04`
- deformation `0.0 -> 8.595027376632592e-04`
- max absolute deformation `2.9753562133649682e-03`

## Diagnostic table

All pressures below are measured on the stored non-uniform-grid data, not only
on remapped plot images.

| case | snapshot time | status | jump | jump error | liquid residual RMS | gas residual RMS | checker projection | curvature std |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| static alpha2 initial | 0.000647 | OK | 0.288438 | 0.000438 | 2.84e-05 | 1.73e-05 | 5.57e-03 | 0.484 |
| static alpha2 final | 1.500000 | completed | -0.502856 | 0.214856 | 4.644 | 0.176 | 0.170 | 42.754 |
| static alpha2 static-grid final | 1.300500 | near blowup | -0.137206 | 0.150794 | 3.919 | 0.097 | 0.200 | 39.800 |
| static alpha4 final | 1.100002 | near blowup | -1.424425 | 1.136425 | 13.730 | 0.765 | 0.310 | 23.347 |
| oscillating alpha4 final | 0.900258 | near blowup | -0.569852 | 0.281852 | 8.877 | 0.226 | 0.296 | 25.949 |

Threshold timings for liquid-phase residual pressure:

| case | RMS > 0.1 | RMS > 1.0 | RMS > 3.0 |
|---|---:|---:|---:|
| static alpha2 | 0.2001 | 0.8501 | 1.3002 |
| static alpha2 static-grid | 0.2006 | 0.7506 | 1.2003 |
| static alpha4 | 0.1502 | 0.3504 | 0.5002 |
| oscillating alpha4 | 0.1501 | 0.4502 | 0.6503 |

## Hypotheses and verdicts

### H1 — pressure gauge or color scale artifact

Verdict: falsified as primary cause.

The diagnostic subtracts liquid and gas phase means separately.  The residual
inside the liquid still grows from `O(1e-5)` to `O(1)`--`O(10)`.  A gauge mode
cannot produce phase-mean-free liquid oscillations.

### H2 — wrong Young--Laplace initialization

Verdict: falsified.

The first static alpha-2 snapshot gives jump `0.288438` against theoretical
`0.288`, with liquid residual RMS `2.84e-05`.  The initial pressure state is
physically correct to the resolution of this run.

### H3 — physical droplet deformation or volume loss

Verdict: falsified as primary cause.

The static alpha-2 run reaches `T=1.5` with maximum deformation below `4e-03`
and volume drift below `9e-04`, while the liquid pressure residual reaches
`4.644`.  The pressure oscillation is not explained by large shape deformation
or volume loss.

### H4 — Rayleigh--Lamb oscillation itself

Verdict: falsified as sole cause.

A perfectly static circle also develops liquid pressure residuals.  The ellipse
accelerates the failure, but it is not necessary for the pressure pathology.

### H5 — alpha=4 fitted-grid concentration

Verdict: supported as a strong amplifier, not the whole mechanism.

Static alpha-4 reaches liquid residual RMS `13.730` by `t≈1.10` and blows up.
Static alpha-2 delays the same residual growth and completes `T=1.5`, but its
liquid residual RMS still reaches `4.644`.  Therefore alpha=4 is a major
destabilizing geometry choice, while alpha=2 reduces rather than removes the
underlying pressure imbalance.

### H6 — every-step grid rebuild/remap/history reset

Verdict: falsified as primary cause.

The static-grid alpha-2 control also develops liquid pressure residuals and
blows up at `t=1.3228`.  Every-step rebuild is not necessary for the pressure
oscillation; in this particular comparison it is even more stable than fixed
initial fitted grid over `T=1.5`.

### H7 — plotting remap artifact

Verdict: falsified as primary cause, but accepted as a visualization amplifier.

The direct non-uniform-grid data already contains large phase-mean-free liquid
pressure residuals.  The plot remapper can change apparent jump and smooth or
distort local extrema near the discontinuity, but it does not create the
underlying oscillation.

### H8 — checkerboard/high-frequency pressure mode

Verdict: supported as a symptom and partial mechanism.

The checker projection grows from near zero to `0.17`--`0.31`, and the
high-frequency pressure fraction is close to one in late snapshots.  The mode
is not a pure checkerboard, but the pressure field is dominated by grid-scale
components once the run leaves the near-equilibrium regime.

### H9 — curvature/geometry error feeding the pressure jump

Verdict: strongly supported as the source that seeds the instability.

The curvature proxy starts near the correct circular value, with interface-band
standard deviation about `0.48`, then grows to `~40` in static alpha-2 and
static-grid alpha-2.  The initial pressure--curvature correlation is high
because the pressure jump correctly follows Young--Laplace.  Later the pressure
residual migrates into bulk liquid modes and the correlation drops, indicating
a seeded capillary/PPE imbalance that is no longer a clean local curvature jump.

### H10 — phase-separated affine PPE fails to maintain phase-constant pressure
under contaminated capillary RHS

Verdict: supported as the propagation mechanism.

The pathology is strongly phase-asymmetric: final liquid residual RMS is
`4.644` for static alpha-2 and `13.730` for static alpha-4, while the gas
residual RMS is only `0.176` and `0.765`.  A static incompressible liquid phase
should not contain these internal pressure modes.  The jump also changes sign
from the correct `+0.288` to negative values.  This points to an elliptic
pressure solve receiving a contaminated capillary/curvature RHS and propagating
it into high-density liquid pressure modes.

## Root-cause inference

The pressure oscillation is not a cosmetic plotting problem and not a pressure
gauge ambiguity.  It is a physical-equilibrium violation: the method initially
satisfies Young--Laplace, then progressively loses the phasewise constant
pressure state.  The most consistent cause is a coupled geometry/capillary/PPE
imbalance:

1. the stored interface geometry gradually develops high-frequency curvature
   error on the N=64 non-uniform fitted grid,
2. the pressure-jump/affine PPE route receives that curvature-contaminated
   capillary RHS,
3. the phase-separated elliptic projection propagates the contamination mostly
   into the high-density liquid phase,
4. alpha=4 and oscillatory elliptic deformation amplify the same mechanism,
   while alpha=2 delays it.

Thus the problem is now localized to the chain

`interface geometry / curvature proxy -> Young--Laplace pressure jump RHS -> phase-separated affine PPE -> liquid bulk pressure modes`.

No solver change is made here.  Theory-consistent next verification should
instrument this chain directly: store per-step curvature spectra, affine jump
RHS spectra, PPE residual history, pressure increment spectra, and phasewise
bulk pressure residuals.  A numerical change should only follow from that
equation-to-code chain, not from damping, smoothing, or timestep tweaking as a
surface-level patch.

[SOLID-X] Diagnostic script/config/artifact only; no solver/operator/builder
boundary was changed, and no tested implementation was deleted.
