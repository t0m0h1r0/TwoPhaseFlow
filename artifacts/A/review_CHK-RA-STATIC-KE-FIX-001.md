# CHK-RA-STATIC-KE-FIX-001 — Static-Droplet KE Mitigation

Date: 2026-05-06

## Verdict

The original KE rise is not physically valid.  The implemented production
change is deliberately conservative:

- `transport_variational_p2_ale_discrete_gradient` is rejected for
  `pressure_jump` production configs because the previous RCA showed a
  nonzero divergence-free capillary face cochain on a static Young-Laplace
  droplet.
- ch14 production YAMLs now use the scalar face-native Young-Laplace geometry
  `face_implicit`.
- `ch14_static_droplet.yaml` disables Ridge-Eikonal reinitialization
  (`every_steps: 0`) because static-equilibrium validation must not apply a
  pseudo-time profile-restoration step that changes surface energy without
  physical work accounting.

This is not a fallback: the invalid P2 ALE face-cochain route now fails closed
when paired with production `pressure_jump`.

## Remote GPU Validation

All runs used `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock` and remote
`make run`.

| case | N | T | final/max KE | max volume drift | max deformation | final face accel Linf |
|---|---:|---:|---:|---:|---:|---:|
| face_implicit + reinit eps=1.4 | 32 | 0.2 | `2.581e-05` | `6.345e-16` | `0` | `1.869e-02` |
| face_implicit + reinit eps=1.5 | 32 | 0.2 | `1.630e-05` | `1.903e-15` | `0` | `1.112e-02` |
| face_implicit + no reinit | 32 | 0.2 | `2.19e-07` at `t≈0.198` | `1.015e-15` | `0` | `1.154e-03` |
| face_implicit + no reinit | 32 | 5.0 | `9.490e-05` | `3.426e-15` | `0` | `2.403e-03` |

Reference from the previous P2 ALE route:

- N=32, T≈0.2: KE `7.307e-06`.
- N=32, T=5.0: KE `1.031e-03`.

Thus the accepted static-droplet route reduces T=5 KE by about one order of
magnitude versus the rejected P2 ALE route, while preserving volume to roundoff.
The remaining nonzero face acceleration shows that pressure-jump/projection is
not mathematically perfect yet; it is now exposed as residual work rather than
hidden behind reinitialization.

## Rejected During This CHK

A cut-face-only FCCD pressure-gradient patch was tried and rejected.  It raised
N=32,T=0.2 KE from `2.58e-05` to `3.05e-05`, so it was removed before commit.

## Remaining Theory Work

The next root fix is not damping, CFL reduction, curvature clipping, or a
silent alternate scheme.  The remaining work is to implement the P2 ALE
pressure-jump range projection required by the face-work theorem:

```text
B_h(j_h) ~= F_cap
```

in the same face-work metric consumed by the PPE and corrector, and to gate it
with the static-droplet Hodge residual `|a_f|`, not only `|D_f a_f|`.
