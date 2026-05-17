# CHK-RA-CH14-ORIGIN-RESET-001 — Ch14 capillary origin-reset handoff

## Claim

The next productive Ch14 capillary session should start from capillary state
ownership and a minimal oracle, not from further screened q/phi runtime
projection tuning.

## Provenance

- Extracted from branch `codex/ra-ch14-osc-droplet-eighth-20260516`, especially
  commit `b0d36536` (`Probe capillary screened graph q runtime`).
- This handoff intentionally does not merge that branch's runtime code into
  `main`; it extracts the durable theory and negative evidence.
- Main-side wiki consumers are `docs/wiki/theory/WIKI-T-174.md` and
  `docs/wiki/cross-domain/WIKI-X-056.md`.
- Reusable next-session prompt:
  `docs/memo/ch14_origin_reset_next_session_prompt.md`.

## Extracted Facts

The previous branch established a useful control and a useful failure:

- The default GPU AO-Fast capillary-wave diagnostic completed a short remote
  two-step probe and generated a visualization PDF.
- Sampled capillary mode values in that branch were nonzero and changed sign
  over the two sampled steps, while the admitted graph route reported
  `compat_linf=0`.
- The screened graph-q rebuild failed closed under the strict contract:
  `GPU active q/phi compatibility projection did not converge; final residual
  1.630e-08 exceeds tolerance 1.000e-11`.
- Exploratory probes beyond that point indicated topology movement, redundant
  periodic quotient constraints, and a later nonlinear line-search failure.
- Loose predictor tolerance was not accepted as a fix.

## Interpretation

The failure should not be read as "screened Sobolev needs a looser residual."
It should be read as evidence that the hybrid state split may be wrong:

```text
conserve q
  -> rebuild smooth phi/graph
  -> compute capillary geometry from phi/graph
  -> demand exact q compatibility
```

If transported `q` is not on the chosen smooth-interface chart manifold, then
exact q preservation and smooth geometry can conflict.  Graph rebuild can hide
this by redefining `q` from the graph; exact q projection can expose it by
creating jagged geometry or topology-moving updates.

## Recommended Next Path

Use the following sequence:

1. Decide whether the owned state is interface configuration `Gamma_h` or cell
   volume `q`.
2. If `Gamma_h` is owned, build a graph capillary-wave oracle:
   `eta(x) -> Q_h(eta), E[eta], delta E/delta eta`.
3. Add a closed-droplet chart plan:
   `Gamma(theta)` or `r(theta) -> Q_h(Gamma), E[Gamma], volume`.
4. Verify force sign, symmetry, energy trend, and phase/mode behavior visually.
5. Only after the oracle passes, wire the route into Ch14 runtime and T/8
   experiments.

## Forbidden Carryovers

- Do not treat screened q/phi projection as the default continuation route.
- Do not weaken tolerances, skip rebuilds, smooth curvature, add damping, or
  retune CFL as the primary remedy.
- Do not insert special closed-droplet conditions that are not chart choices
  under a common variational principle.
- Do not accept visual smoothness without pre/post q, energy, and symmetry
  residuals.

## Validation Performed for This Handoff

This is a docs-only extraction.  It changes wiki, artifact, memo prompt, lock,
and ledger/index bookkeeping only; no solver code, experiment YAML, cached
result data, numerical algorithm, tolerance, CFL, smoothing, damping, or
fallback route is changed.
