# CHK-RA-CH14-AO-FASTVOL-033 - Wiki accumulation of AO-Fast findings

## Purpose

User request:

> 得られた重要な知見は全てwikiに蓄積して

Recent AO-Fast capillary findings were distributed across artifacts, paper
sections, experiments, and YAML changes.  This checkpoint promotes the reusable
knowledge into `docs/wiki` so later work starts from the current theory instead
of stale branch artifacts.

## Wiki Updates

Updated:

```text
docs/wiki/theory/WIKI-T-169.md
docs/wiki/cross-domain/WIKI-X-041.md
docs/wiki/INDEX.md
```

Added:

```text
docs/wiki/experiment/WIKI-E-063.md
docs/wiki/cross-domain/WIKI-X-049.md
```

## Captured Findings

- Full pressure-image AO capillary splitting can cancel non-static face drive
  exactly; it is a counterexample, not a physical success certificate.
- Nonzero nodal Young--Laplace residual is insufficient; the accepted object is
  `r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma` after defining the pressure-reaction
  subspace.
- Component-Hodge output is retained as a non-staticity probe only.
- GPU AO-Fast packets with non-static zero balanced drive must fail close; no
  hidden PCG/DC/dense-CPU/host fallback is accepted.
- Flat/static zero-drive controls remain admissible and must not be rejected by
  the non-static fail-close rule.
- U12/V11 remote GPU gates record the executable evidence and replace the stale
  V11 common-flux admissibility reading.
- Chapter 14 production YAMLs are explicit `diffuse_cls` configs.  Standard
  capillary-wave/Rayleigh--Taylor use `curvature_jump`; closed-interface
  droplet/bubble cases use `closed_interface_riesz` with
  `pressure_component_hodge`; AO-Fast requires a separate
  `geometric_cell_fraction` YAML contract.
- The successful mainline Chapter 14 capillary-wave rerun validates the
  standard FCCD/UCCD6/pressure-jump/component-Hodge route, not AO-Fast
  admission.

## Validation

```text
git diff --check
rg -n "WIKI-X-049|WIKI-E-063|CHK-RA-CH14-AO-FASTVOL-033" docs/wiki docs/02_ACTIVE_LEDGER.md artifacts/A
```

[SOLID-X] Wiki, artifact, and ledger only; no production solver source, YAML
physical parameter, experiment result, CFL reduction, damping, smoothing,
curvature cap, FD/WENO/PPE fallback, hidden PCG/DC fallback, AO-Fast production
admission, or main merge was introduced.
