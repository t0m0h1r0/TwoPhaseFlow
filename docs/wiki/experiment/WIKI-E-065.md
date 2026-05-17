---
ref_id: WIKI-E-065
title: "Ch14 Variational Capillary Graph Oracle PASS"
domain: experiment
status: ACTIVE
tags: [ch14, capillary_wave, variational_oracle, interface_configuration, q_derived, graph_chart, visualization]
sources:
  - path: artifacts/A/ch14_variational_state_oracle_CHK-RA-CH14-VAR-002.md
    description: "Theory artifact, hypothesis matrix, oracle plan, and PASS metrics"
  - path: experiment/ch14/diagnose_variational_capillary_oracle.py
    description: "Minimal graph-chart capillary oracle implementation"
  - path: docs/wiki/theory/WIKI-T-174.md
    description: "State-ownership theory selecting Gamma_h versus q"
  - path: docs/wiki/experiment/WIKI-E-064.md
    description: "Baseline PASS and screened graph-q FAIL evidence that motivated the oracle-first route"
depends_on:
  - "[[WIKI-T-174]]"
  - "[[WIKI-E-064]]"
consumers:
  - domain: theory
    usage: "Use as the first validated graph-chart evidence for interface-configuration primary capillarity"
  - domain: experiment
    usage: "Use before designing the closed-curve chart or any Ch14 T/8 runtime connection"
  - domain: code
    usage: "Use to keep q derived from Gamma_h in oracle work instead of repairing screened q/phi projection by default"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Variational Capillary Graph Oracle PASS

## Knowledge Card

The first origin-reset oracle for Ch14 capillarity passed with
interface-configuration primary state ownership:

```text
Gamma_h = {(x, eta(x))}
q = Q_h(Gamma_h)
E[eta] = sigma integral sqrt(1 + eta_x^2) dx
force = - delta E / delta eta
```

This is a small graph-chart oracle, not a T/8 runtime admission and not a
screened q/phi projection repair.  It preserves [[WIKI-E-064]] as negative
knowledge and tests the alternative route selected in [[WIKI-T-174]].

## Validation

Command:

```text
make cycle EXP=experiment/ch14/diagnose_variational_capillary_oracle.py
```

Result: PASS.  The remote run saved and pulled:

```text
experiment/ch14/results/diagnose_variational_capillary_oracle/data.npz
experiment/ch14/results/diagnose_variational_capillary_oracle/variational_capillary_oracle.pdf
```

Key metrics:

| Metric | Value | Gate |
|---|---:|---|
| `eta_mode` | `4.000000000000e-02` | owned graph amplitude |
| `force_mode` | `-5.780870211894e+00` | restoring sign opposes height |
| `force_sign_product` | `-2.312348084758e-01` | force sign PASS |
| `fd_rel_error` | `1.295792449794e-11` | energy variation PASS |
| `q_height_error_linf` | `2.220446049250e-15` | derived `Q_h(eta)` column volume PASS |
| `q_mode_error` | `1.387778780781e-17` | q mode PASS |
| `surface_error` | `0` | P1 surface length equals graph segment length |
| `variation_sine` | `-5.273559366969e-16` | cosine symmetry PASS |
| `volume_error` | `2.220446049250e-16` | derived volume PASS |

## Practice

- Start future Ch14 capillary work from the owned interface configuration and
  derive `q` for measurement until a genuine q-space energy `E_h[q]` is
  designed.
- A regular-sign P1 gauge is an oracle precondition.  Do not interpret exact
  node-level graph placement as a physics failure.
- The next admissible step is a closed-curve chart using the same
  `E=sigma |Gamma_h|` variation, followed only then by a short runtime probe.
- Do not use this oracle to justify tolerance weakening, smoothing, damping,
  CFL retuning, rebuild skipping, FD/WENO/PPE family fallback, or hidden CPU
  fallback in production runtime.
