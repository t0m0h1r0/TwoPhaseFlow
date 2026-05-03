# CHK-RA-OSC-N64-015 — Paper Reflection of Projection-Native ψ Transport

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Decision

The CHK-014 finding is paper-worthy because it is not an implementation detail
or tuning knob.  It changes the mathematical contract of the coupled
projection/interface update: once the PPE/projection has produced a canonical
face velocity, conservative CLS transport must consume that same face velocity.

## Paper Changes

- `paper/sections/09b_split_ppe.tex` now states the projection-native
  conservative update
  `psi^{n+1}=RK3[psi^n; -D_f((P_f psi) u_f^{n+1})]` and records that nodal
  reconstruction is not a valid flux source for interface transport.
- `paper/sections/13f_error_budget.tex` now lists velocity-representation
  mismatch as a distinct error source under interface representation error.
- `paper/sections/14_benchmarks.tex` now ties the benchmark stack to the new
  equation and reports the N64 static-droplet diagnostic: old reconstructed-node
  transport final cut-face `kappa` std `1.07e1`, projection-native transport
  `1.86`, frozen-interface control `1.66e-2`.

## Validation

```bash
git diff --check
```

PASS.

```bash
make -C paper
```

PASS.  `latexmk` completed and produced `paper/main.pdf`.

## SOLID-X

No SOLID issue: paper-only update.  No tested implementation was deleted, and
the text explicitly rejects smoothing/CFL/velocity-source toggles as a root fix
for this failure mode.
